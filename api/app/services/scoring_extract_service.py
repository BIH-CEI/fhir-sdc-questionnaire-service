"""
ScoringExtractService — bridges the HAPI CR / SDC gap, fully generic.

HAPI CR 8.4 evaluates Library/$evaluate (CQL works) but doesn't trigger
sdc-calculatedExpression evaluation during $populate or $extract. The
SDC flow "$populate → user fills → $extract → Observations" therefore
breaks for computed items.

This service implements the bridge as a single FastAPI operation:

  POST /api/questionnaires/{q_id}/$compute-and-extract
  Body: Parameters { name: "subject", valueReference: Patient/X }

The service is **fully generic** — it carries NO instrument-specific
knowledge in code. All scoring metadata lives in the FHIR content:

  - Questionnaire item.code           → Observation.code (LOINC)
  - Questionnaire sdc-calculatedExpression → which CQL define produces the value
  - Questionnaire sdc-questionnaire-observationExtract → which items are extracted
  - ObservationDefinition.qualifiedInterval → Observation.interpretation (severity band)

Adding a new instrument is purely a pro-library change: ship its
Questionnaire (with the wirings above), its scoring Library, and an
ObservationDefinition for each emitted LOINC code (with qualifiedInterval
severity bands where applicable). The sidecar code does not change.

Internal pipeline:
  1. Read the Questionnaire; resolve scoring Library from cqf-library
  2. Walk Questionnaire.item, find items with observationExtract = true
     and a CQL calculatedExpression
  3. Invoke Library/$evaluate on HAPI (single call returns all defines)
  4. Find the most recent matching QR (for derivedFrom provenance)
  5. For each extract-flagged item:
       a. Get the computed value from $evaluate's parameter named after
          the item's calculatedExpression.expression
       b. Look up an ObservationDefinition with the matching code
          (item.code) on the server
       c. Build the Observation; walk OD.qualifiedInterval to set
          Observation.interpretation if a band matches the value
  6. Optionally POST the resulting Bundle as a transaction
  7. Return the Bundle

R5 migration note: ObservationDefinition.qualifiedInterval → qualifiedValue,
and qualifiedInterval.context → qualifiedValue.interpretation. The
sidecar's _band_for_value helper is the only place that needs to change.
"""
from datetime import datetime, timezone
from typing import Optional
import logging
import httpx

logger = logging.getLogger(__name__)


# FHIR canonical URLs we care about
EXT_CQF_LIBRARY = "http://hl7.org/fhir/StructureDefinition/cqf-library"
EXT_SDC_CALC = "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression"
EXT_SDC_EXTRACT = "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract"
EXT_SDC_EXTRACT_CAT = "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observation-extract-category"
EXT_Q_UNIT = "http://hl7.org/fhir/StructureDefinition/questionnaire-unit"


class ScoringExtractService:
    def __init__(self, fhir_base_url: str):
        self.fhir_base_url = fhir_base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.fhir_base_url, timeout=60.0)

    async def aclose(self):
        await self._client.aclose()

    async def compute_and_extract(
        self,
        questionnaire_id: str,
        subject_reference: str,
        persist: bool = True,
    ) -> dict:
        # 1. Read the Questionnaire (we'll walk its items + read cqf-library)
        q = await self._get_questionnaire(questionnaire_id)

        library_id = self._resolve_scoring_library_id(q)
        if not library_id:
            raise ValueError(
                f"Questionnaire/{questionnaire_id} has no cqf-library extension"
            )

        # 2. Walk items → find extract-flagged ones with a CQL expression
        extract_items = self._extract_flagged_items(q)
        if not extract_items:
            raise ValueError(
                f"Questionnaire/{questionnaire_id} has no items with both "
                f"observationExtract=true and sdc-calculatedExpression"
            )

        # 3. One $evaluate call returns all CQL defines for this Patient
        define_values = self._unpack_parameters(
            await self._invoke_evaluate(library_id, subject_reference)
        )

        # 4. Provenance — find the most recent matching QR
        qr_reference = await self._find_most_recent_qr(
            questionnaire_id, subject_reference
        )

        # 5. Build one Observation per extract-flagged item
        observations = []
        for item in extract_items:
            obs = await self._build_observation(
                item, define_values, subject_reference, qr_reference
            )
            if obs is not None:
                observations.append(obs)

        if not observations:
            raise ValueError(
                f"No Observations could be built — likely no CQL defines "
                f"matched the items' calculatedExpression names. "
                f"Available defines: {list(define_values.keys())}"
            )

        # 6. Transaction Bundle
        transaction_bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {"resource": obs, "request": {"method": "POST", "url": "Observation"}}
                for obs in observations
            ],
        }
        if not persist:
            return transaction_bundle

        response = await self._client.post("/", json=transaction_bundle)
        response.raise_for_status()
        return self._merge_locations(observations, response.json())

    # ─── Internal helpers ──────────────────────────────────────────────────

    async def _get_questionnaire(self, qid: str) -> dict:
        r = await self._client.get(f"/Questionnaire/{qid}")
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _resolve_scoring_library_id(q: dict) -> Optional[str]:
        for ext in q.get("extension", []):
            if ext.get("url") == EXT_CQF_LIBRARY:
                canonical = ext.get("valueCanonical", "")
                return canonical.split("|", 1)[0].rstrip("/").rsplit("/", 1)[-1] or None
        return None

    @staticmethod
    def _extract_flagged_items(q: dict) -> list:
        """Return items with observationExtract=true AND a sdc-calculatedExpression."""
        flagged = []
        for item in q.get("item", []):
            has_extract = False
            calc_expression = None
            for ext in item.get("extension", []):
                if ext.get("url") == EXT_SDC_EXTRACT and ext.get("valueBoolean") is True:
                    has_extract = True
                elif ext.get("url") == EXT_SDC_CALC:
                    ve = ext.get("valueExpression", {})
                    if ve.get("language", "").startswith("text/cql"):
                        calc_expression = ve.get("expression")
            if has_extract and calc_expression and item.get("code"):
                flagged.append({"item": item, "cql_expression": calc_expression})
        return flagged

    async def _invoke_evaluate(self, library_id: str, subject: str) -> dict:
        r = await self._client.get(
            f"/Library/{library_id}/$evaluate", params={"subject": subject}
        )
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _unpack_parameters(parameters: dict) -> dict:
        out = {}
        for p in parameters.get("parameter", []):
            name = p.get("name")
            for key, value in p.items():
                if key.startswith("value"):
                    out[name] = value
                    break
        return out

    async def _find_most_recent_qr(self, qid: str, subject: str) -> Optional[str]:
        r = await self._client.get(
            "/QuestionnaireResponse",
            params={"subject": subject, "_sort": "-authored", "_count": "5"},
        )
        if r.status_code != 200:
            return None
        for entry in r.json().get("entry", []):
            qr = entry.get("resource", {})
            if qid in qr.get("questionnaire", ""):
                return f"QuestionnaireResponse/{qr['id']}"
        return None

    async def _build_observation(
        self,
        flagged: dict,
        define_values: dict,
        subject_reference: str,
        qr_reference: Optional[str],
    ) -> Optional[dict]:
        item = flagged["item"]
        expr_name = flagged["cql_expression"]
        if expr_name not in define_values:
            return None
        value = define_values[expr_name]
        if value is None:
            return None

        item_code = item.get("code", [{}])[0]
        loinc_code = item_code.get("code")
        unit = self._get_unit(item)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "survey",
                            "display": "Survey",
                        }
                    ]
                }
            ],
            "code": {"coding": [item_code]},
            "subject": {"reference": subject_reference},
            "effectiveDateTime": now,
            "issued": now,
            "valueQuantity": {
                "value": value,
                "system": "http://unitsofmeasure.org",
                "code": unit,
            },
        }
        if qr_reference:
            obs["derivedFrom"] = [{"reference": qr_reference}]

        # Look up the ObservationDefinition on the server for this LOINC code
        # and use its qualifiedInterval to set Observation.interpretation.
        if loinc_code:
            interp = await self._interpretation_from_obsdef(loinc_code, value)
            if interp:
                obs["interpretation"] = [interp]

        return obs

    @staticmethod
    def _get_unit(item: dict) -> str:
        for ext in item.get("extension", []):
            if ext.get("url") == EXT_Q_UNIT:
                vc = ext.get("valueCoding", {})
                if vc.get("code"):
                    return vc["code"]
        return "1"  # UCUM "unity" — fallback

    async def _interpretation_from_obsdef(
        self, loinc_code: str, value
    ) -> Optional[dict]:
        """
        Find an ObservationDefinition whose code matches the LOINC, then walk
        its qualifiedInterval[] looking for an *absolute* band whose range
        contains `value`. Return the band's context CodeableConcept as the
        Observation.interpretation entry.
        """
        try:
            r = await self._client.get(
                "/ObservationDefinition", params={"code": loinc_code, "_count": "10"}
            )
            r.raise_for_status()
        except httpx.HTTPError:
            return None

        for entry in r.json().get("entry", []):
            od = entry.get("resource", {})
            band = self._band_for_value(od.get("qualifiedInterval", []), value)
            if band is not None:
                return band
        return None

    @staticmethod
    def _band_for_value(qualified_intervals: list, value) -> Optional[dict]:
        """
        Walk qualifiedInterval[]; return a CodeableConcept suitable for
        Observation.interpretation if any *absolute* band's range contains
        `value`. Falls back to the band's `condition` text if no
        `context.coding` is present.

        R5 note: in R5 this would walk qualifiedValue[] and prefer
        qualifiedValue.interpretation directly (already CodeableConcept).
        """
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None

        for qi in qualified_intervals:
            if qi.get("category") != "absolute":
                continue
            rng = qi.get("range", {})
            low = rng.get("low", {}).get("value")
            high = rng.get("high", {}).get("value")
            if low is not None and v < float(low):
                continue
            if high is not None and v > float(high):
                continue
            context = qi.get("context") or {}
            if context.get("coding") or context.get("text"):
                concept = dict(context)
                if "text" not in concept and qi.get("condition"):
                    concept["text"] = qi["condition"]
                return concept
        return None

    @staticmethod
    def _merge_locations(observations: list, transaction_response: dict) -> dict:
        response_entries = transaction_response.get("entry", [])
        merged = []
        for i, obs in enumerate(observations):
            location = (
                response_entries[i].get("response", {}).get("location", "")
                if i < len(response_entries)
                else ""
            )
            bare = location.split("/_history/")[0] if location else None
            obs_id = bare.rsplit("/", 1)[-1] if bare else None
            if obs_id:
                obs["id"] = obs_id
            merged.append({"fullUrl": bare, "resource": obs})
        return {"resourceType": "Bundle", "type": "collection", "entry": merged}
