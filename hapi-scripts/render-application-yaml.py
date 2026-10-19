#!/usr/bin/env python3
"""Render hapi-config/application.yaml for the image.

Replaces the `# @@MII_PRO_RETAINED@@` marker with one `implementationguides`
entry per retained MII PRO version, so HAPI's PackageInstallerSvc installs
the profiles and terminology of every retained version next to the current
one (keyed by canonical + version). Without retained versions the marker is
simply dropped.

Usage: render-application-yaml.py <in.yaml> <out.yaml> "<v1> <v2> ..."
"""
import sys

MARKER = "# @@MII_PRO_RETAINED@@"
PACKAGE = "de.medizininformatikinitiative.kerndatensatz.pros"


def entry(version: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in version)
    return (
        f"      mii_pros_retained_{slug}:\n"
        f"        name: {PACKAGE}\n"
        f"        version: {version}\n"
        f"        installMode: STORE_AND_INSTALL\n"
        f"        packageUrl: file:///data/hapi/local-packages/{PACKAGE}-{version}.tgz\n"
        f"        reloadExisting: false\n"
        f"        fetchDependencies: false\n"
    )


def render(text: str, versions: list[str]) -> str:
    if MARKER not in text:
        raise SystemExit(f"marker {MARKER!r} not found in application.yaml")
    block = "".join(entry(v) for v in versions)
    header = (
        "      # Retained MII PRO versions (Dockerfile ARG MII_PRO_RETAINED_VERSIONS),\n"
        "      # rendered at image build time by hapi-scripts/render-application-yaml.py.\n"
    ) if versions else ""
    lines = []
    for line in text.splitlines(keepends=True):
        if line.strip() == MARKER:
            lines.append(header + block)
        else:
            lines.append(line)
    return "".join(lines)


if __name__ == "__main__":
    src, dst, raw = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    versions = raw.split()
    with open(src) as fh:
        out = render(fh.read(), versions)
    with open(dst, "w") as fh:
        fh.write(out)
    print(f"application.yaml rendered with retained MII PRO versions: {versions or 'none'}")
