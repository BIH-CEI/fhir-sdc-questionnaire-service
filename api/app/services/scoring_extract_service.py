"""
ScoringExtractService — bridges the HAPI CR / SDC gap.

HAPI CR 8.4 evaluates Library/$evaluate (CQL works) but doesn't
trigger sdc-calculatedExpression evaluation during $populate or
$extract. Score values therefore never end up in QuestionnaireResponse
item.answer fields automatically, and the SDC standard flow of
"$populate → user fills → $extract → Observations" breaks for
computed/derived items like PHQ-9 total score and PROMIS T-Score.

This service implements the bridge as a single FastAPI operation:

  POST /api/questionnaires/{q_id}/$compute-and-extract
  Body: Parameters { name: "subject", valueReference: Patient/X }

  Internal pipeline:
    1. Resolve the Library bound to the Questionnaire via cqf-library
    2. Invoke Library/$evaluate?subject=Patient/X on HAPI
    3. Find the most recent matching QR (for derivedFrom provenance)
    4. Build Observations directly from the $evaluate result with proper
       LOINC codes, valueQuantity, AND interpretation for PHQ-9 severity
    5. Optionally POST them as a transaction Bundle (persist=true default)
    6. Return the Bundle (searchset if persisted, transaction if not)
"""
from datetime import datetime, timezone
from typing import Optional
import logging
import httpx

logger = logging.getLogger(__name__)


# Per-Questionnaire registry: which CQL defines map to which Observations.
# Add a new entry here when a new instrument's CQL Library ships in pro-library
# with new define names + Observation LOINC codes.
#
# Each entry under a Questionnaire id maps a CQL define name → Observation spec.
# Spec fields:
#   loinc_code         — LOINC code that goes into Observation.code.coding
#   loinc_display      — display text for that LOINC code
#   unit_code          — UCUM code for valueQuantity.code (e.g. '{score}')
#   interpretation_from — optional CQL define whose value becomes
#                        Observation.interpretation.text (e.g. severity band)
SCORE_OBSERVATION_REGISTRY = {
    "phq-9": {
        "PHQ9TotalScore": {
            "loinc_code": "44261-6",
            "loinc_display": "Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]",
            "unit_code": "{score}",
            "interpretation_from": "PHQ9Severity",
        },
        "PROMISDepressionTScore": {
            "loinc_code": "77861-3",
            "loinc_display": "PROMIS emotional distress - depression - version 1.0 Tscore",
            "unit_code": "{score}",
            "interpretation_from": None,  # T-scale self-describing
        },
    },
    # When pro-library adds PROMIS Depression SF-4a (mii-qst-pro-promis-
    # depression-sf4a), append its entry here with the appropriate CQL define
    # names and ObservationDefinition codes. The Library itself follows the
    # same SDC-Flow-A pattern (context Patient + retrieve).
    "promis-depression-sf4a": {
        # TODO: fill in once pro-library ships the Library
        # "PROMISDepressionSF4aRawScore": {...},
        # "PROMISDepressionSF4aTScore":   {...},
    },
}


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
        """
        Orchestrate score-compute + observation-build for a given subject.

        Returns a Bundle:
          - if persist=True: a 'searchset' Bundle of the persisted Observations
          - if persist=False: a 'transaction' Bundle of the proposed Observations
            (caller can POST it themselves)
        """
        # 1. Resolve the bound scoring Library from the Questionnaire's cqf-library
        library_id = await self._resolve_scoring_library(questionnaire_id)
        if not library_id:
            raise ValueError(
                f"Questionnaire/{questionnaire_id} has no cqf-library extension; "
                f"cannot compute scores"
            )

        # 2. Run CQL evaluation against HAPI CR with Patient context
        scores_params = await self._invoke_evaluate(library_id, subject_reference)
        define_values = self._unpack_parameters(scores_params)

        # 3. Find the most recent QR for derivedFrom provenance
        qr_reference = await self._find_most_recent_qr(
            questionnaire_id, subject_reference
        )

        # 4. Build Observations from the relevant define values
        observations = self._build_observations(
            define_values, subject_reference, qr_reference, questionnaire_id
        )

        if not observations:
            raise ValueError(
                f"No mappable score defines found for Library/{library_id} — "
                f"either the CQL returned no scoring values or no entry in "
                f"SCORE_OBSERVATION_REGISTRY[{questionnaire_id!r}] matched the "
                f"defines. Available defines: {list(define_values.keys())}"
            )

        # 5. Build the transaction Bundle
        transaction_bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "resource": obs,
                    "request": {"method": "POST", "url": "Observation"},
                }
                for obs in observations
            ],
        }

        if not persist:
            return transaction_bundle

        # 6. POST the transaction → persist Observations
        response = await self._client.post("/", json=transaction_bundle)
        response.raise_for_status()
        result_bundle = response.json()

        # HAPI's transaction-response entries carry only response.location
        # (not the full resource). Pair each location back with the source
        # Observation we constructed, so the caller gets ready-to-use entries.
        return self._merge_locations(observations, result_bundle)

    # ─── Internal helpers ──────────────────────────────────────────────────

    async def _resolve_scoring_library(self, questionnaire_id: str) -> Optional[str]:
        """Walk Questionnaire.extension[cqf-library] → return Library id."""
        resp = await self._client.get(f"/Questionnaire/{questionnaire_id}")
        resp.raise_for_status()
        q = resp.json()
        for ext in q.get("extension", []):
            if ext.get("url") == "http://hl7.org/fhir/StructureDefinition/cqf-library":
                # valueCanonical is a URL ending in /Library/{id} (optionally |version)
                canonical = ext.get("valueCanonical", "")
                slug = canonical.split("|", 1)[0].rstrip("/").rsplit("/", 1)[-1]
                if slug:
                    return slug
        return None

    async def _invoke_evaluate(self, library_id: str, subject: str) -> dict:
        resp = await self._client.get(
            f"/Library/{library_id}/$evaluate", params={"subject": subject}
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _unpack_parameters(parameters: dict) -> dict:
        """Parameters resource → flat dict {define_name: value}."""
        out = {}
        for p in parameters.get("parameter", []):
            name = p.get("name")
            for key, value in p.items():
                if key.startswith("value"):
                    out[name] = value
                    break
        return out

    async def _find_most_recent_qr(
        self, questionnaire_id: str, subject: str
    ) -> Optional[str]:
        """Return 'QuestionnaireResponse/{id}' for derivedFrom; None if not found."""
        resp = await self._client.get(
            "/QuestionnaireResponse",
            params={
                "subject": subject,
                "_sort": "-authored",
                "_count": "1",
            },
        )
        if resp.status_code != 200:
            return None
        bundle = resp.json()
        for entry in bundle.get("entry", []):
            qr = entry.get("resource", {})
            q_ref = qr.get("questionnaire", "")
            # Match by URL containing the Questionnaire id (version-agnostic)
            if questionnaire_id in q_ref:
                return f"QuestionnaireResponse/{qr['id']}"
        return None

    @staticmethod
    def _build_observations(
        define_values: dict,
        subject_reference: str,
        qr_reference: Optional[str],
        questionnaire_id: str,
    ) -> list:
        registry = SCORE_OBSERVATION_REGISTRY.get(questionnaire_id, {})
        if not registry:
            raise ValueError(
                f"No Observation-mapping registry entry for Questionnaire "
                f"{questionnaire_id!r}. Add one in SCORE_OBSERVATION_REGISTRY."
            )

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        observations = []

        for define_name, spec in registry.items():
            if define_name not in define_values:
                continue
            raw_value = define_values[define_name]
            if raw_value is None:
                continue

            # Preserve native numeric type so Integer scores serialise as `14`
            # (not `14.0`). FHIR Quantity.value is `decimal` and accepts either;
            # but consumers reasonably prefer integers for items that are
            # conceptually integers (PHQ-9 sum is 0..27 int). The CQL define
            # already returns the right type via valueInteger / valueDecimal.
            value_quantity = {
                "value": raw_value,
                "system": "http://unitsofmeasure.org",
                "code": spec["unit_code"],
            }

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
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": spec["loinc_code"],
                            "display": spec["loinc_display"],
                        }
                    ]
                },
                "subject": {"reference": subject_reference},
                "effectiveDateTime": now,
                "issued": now,
                "valueQuantity": value_quantity,
            }

            # Interpretation (severity band) for items configured for it.
            # Uses per-Questionnaire CodeSystem URL so each instrument gets
            # its own well-namespaced severity vocabulary.
            interp_define = spec.get("interpretation_from")
            if interp_define and interp_define in define_values:
                band_text = define_values[interp_define]
                if band_text:
                    severity_cs = (
                        f"https://fhir.bih-charite.de/pro-library/"
                        f"CodeSystem/{questionnaire_id}-severity"
                    )
                    obs["interpretation"] = [
                        {
                            "text": str(band_text),
                            "coding": [
                                {
                                    "system": severity_cs,
                                    "code": str(band_text).replace(" ", "-"),
                                    "display": str(band_text),
                                }
                            ],
                        }
                    ]

            if qr_reference:
                obs["derivedFrom"] = [{"reference": qr_reference}]

            observations.append(obs)

        return observations

    @staticmethod
    def _merge_locations(
        source_observations: list, transaction_response: dict
    ) -> dict:
        """
        Pair each constructed Observation with the persisted location HAPI
        returned (entry[i].response.location like 'Observation/405/_history/1').
        Strip _history off so fullUrl is the bare resource reference.
        Backfills Observation.id from the location.
        """
        response_entries = transaction_response.get("entry", [])
        merged_entries = []
        for i, obs in enumerate(source_observations):
            location = (
                response_entries[i].get("response", {}).get("location", "")
                if i < len(response_entries)
                else ""
            )
            # 'Observation/405/_history/1' → ('Observation/405', '405')
            bare_ref = location.split("/_history/")[0] if location else None
            obs_id = bare_ref.rsplit("/", 1)[-1] if bare_ref else None
            if obs_id:
                obs["id"] = obs_id
            merged_entries.append(
                {
                    "fullUrl": bare_ref,
                    "resource": obs,
                }
            )

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": merged_entries,
        }
