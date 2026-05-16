"""
Smoke test: load every Questionnaire, ObservationDefinition, and SearchParameter
from a MII PRO tarball into HAPI and report which ones fail.

HAPI's IG installer skips these "instance" resource types — they need to be
PUT individually as regular FHIR resources. This script does that and reports
a clean pass/fail summary plus per-failure diagnostics.

Usage:
  # Against a local tarball
  python3 scripts/verify-mii-pro-load.py --tarball path/to/package.tgz

  # Against an extracted package directory (e.g. FHIR package cache)
  python3 scripts/verify-mii-pro-load.py --package-dir ~/.fhir/packages/de.medizininformatikinitiative.kerndatensatz.pros#2026.3.0/package

  # Against Simplifier (downloads on the fly)
  python3 scripts/verify-mii-pro-load.py --version 2026.3.0

  # Custom HAPI URL
  HAPI_URL=http://hapi-fhir:8080/fhir python3 scripts/verify-mii-pro-load.py --version 2026.3.0

Exits 0 on full success, 1 if any resource failed validation.
"""
import argparse
import io
import json
import os
import pathlib
import re
import sys
import tarfile
import urllib.error
import urllib.request

PACKAGE_NAME = "de.medizininformatikinitiative.kerndatensatz.pros"
RESOURCE_TYPES = ("Questionnaire", "ObservationDefinition", "SearchParameter")
DEFAULT_HAPI_URL = os.environ.get("HAPI_URL", "http://localhost:8095/fhir")


def fetch_tarball(version: str) -> bytes:
    url = f"https://packages.simplifier.net/{PACKAGE_NAME}/{version}"
    print(f"Downloading {url} …")
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def read_tarball(path_or_bytes) -> dict[str, bytes]:
    """Return {filename: content} for every package/*.json in the tarball."""
    if isinstance(path_or_bytes, bytes):
        fileobj = io.BytesIO(path_or_bytes)
        tar = tarfile.open(fileobj=fileobj, mode="r:gz")
    else:
        tar = tarfile.open(path_or_bytes, mode="r:gz")

    resources = {}
    for member in tar:
        if not member.isfile():
            continue
        if not member.name.startswith("package/") or not member.name.endswith(".json"):
            continue
        # Skip the manifest and any examples/ subdir
        base = member.name[len("package/"):]
        if base in ("package.json", ".index.json") or "/" in base:
            continue
        f = tar.extractfile(member)
        if f:
            resources[base] = f.read()
    tar.close()
    return resources


def read_package_dir(path: str) -> dict[str, bytes]:
    """Return {filename: content} for every *.json directly inside the package dir.

    Accepts either the `package/` dir itself or its parent (e.g. ~/.fhir/packages/<name>#<version>).
    """
    p = pathlib.Path(path).expanduser()
    if (p / "package").is_dir():
        p = p / "package"
    if not p.is_dir():
        raise SystemExit(f"--package-dir: not a directory: {p}")

    resources = {}
    for f in sorted(p.glob("*.json")):
        if f.name in ("package.json", ".index.json"):
            continue
        resources[f.name] = f.read_bytes()
    return resources


def put_resource(hapi_url: str, body: bytes, rt: str, rid: str, strip_version_pin: bool):
    """PUT a resource. If strip_version_pin, drops |version from meta.profile."""
    if strip_version_pin:
        res = json.loads(body)
        profiles = res.get("meta", {}).get("profile", [])
        new_profiles = [re.sub(r"\|[^|]+$", "", p) for p in profiles]
        if profiles != new_profiles:
            res.setdefault("meta", {})["profile"] = new_profiles
            body = json.dumps(res).encode()

    req = urllib.request.Request(
        f"{hapi_url}/{rt}/{rid}",
        data=body,
        method="PUT",
        headers={"Content-Type": "application/fhir+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return ("ok", r.status, None)
    except urllib.error.HTTPError as e:
        try:
            oo = json.loads(e.read())
            errs = [
                i.get("diagnostics", "") for i in oo.get("issue", [])
                if i.get("severity") == "error"
            ]
        except Exception:
            errs = ["(no diagnostics)"]
        return ("fail", e.code, errs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--tarball", help="Path to local .tgz")
    src.add_argument("--package-dir", help="Path to extracted package dir (e.g. ~/.fhir/packages/<name>#<version>)")
    src.add_argument("--version", help="Version to fetch from Simplifier, e.g. 2026.3.0")
    parser.add_argument("--hapi-url", default=DEFAULT_HAPI_URL,
                        help=f"HAPI FHIR base URL (default: {DEFAULT_HAPI_URL})")
    parser.add_argument("--strip-profile-version-pin", action="store_true",
                        help="Drop |version from meta.profile entries before PUT (workaround for version drift)")
    args = parser.parse_args()

    print(f"HAPI: {args.hapi_url}")
    if args.package_dir:
        files = read_package_dir(args.package_dir)
    else:
        tarball_data = (
            open(args.tarball, "rb").read() if args.tarball else fetch_tarball(args.version)
        )
        files = read_tarball(tarball_data)
    targets = {
        name: data for name, data in files.items()
        if any(name.startswith(rt + "-") for rt in RESOURCE_TYPES)
    }

    by_type = {rt: [] for rt in RESOURCE_TYPES}
    for name, data in sorted(targets.items()):
        rt = name.split("-", 1)[0]
        by_type[rt].append((name, data))

    print(f"Found {sum(len(v) for v in by_type.values())} resources to load:")
    for rt, items in by_type.items():
        print(f"  {rt}: {len(items)}")
    print()

    results = {"ok": [], "fail": []}
    for rt, items in by_type.items():
        for name, data in items:
            res = json.loads(data)
            rid = res.get("id") or name.replace(rt + "-", "").replace(".json", "")
            status, code, errs = put_resource(args.hapi_url, data, rt, rid, args.strip_profile_version_pin)
            entry = {"id": f"{rt}/{rid}", "code": code, "errors": errs or []}
            results[status].append(entry)

    print(f"\n{'='*60}")
    print(f"PASS: {len(results['ok']):3d}    FAIL: {len(results['fail']):3d}")
    print("=" * 60)

    if results["fail"]:
        print("\nFailures:")
        for f in results["fail"]:
            print(f"\n  ✗ {f['id']}  (HTTP {f['code']})")
            for e in f["errors"][:3]:
                print(f"      • {e[:240]}")
            if len(f["errors"]) > 3:
                print(f"      … and {len(f['errors']) - 3} more error(s)")

    sys.exit(0 if not results["fail"] else 1)


if __name__ == "__main__":
    main()
