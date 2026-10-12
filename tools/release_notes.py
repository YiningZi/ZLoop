"""Extract the current version's Chinese release notes and validate a release tag."""
import argparse
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_release import addon_version


def extract_notes(changelog, version):
    pattern = rf"^## \[{re.escape(version)}\](?:[^\n]*)\n(.*?)(?=^## \[|\Z)"
    matches = list(re.finditer(pattern, changelog, flags=re.MULTILINE | re.DOTALL))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one CHANGELOG entry for {version}")
    notes = matches[0].group(1).strip()
    if not notes:
        raise ValueError(f"Release notes for {version} are empty")
    return notes + "\n"


def validate_release_version(requested, current):
    if requested.removeprefix("v") != current:
        raise ValueError(f"Release tag {requested} does not match bl_info version {current}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Version or v-prefixed tag; must match bl_info")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    current = addon_version()
    if args.version:
        validate_release_version(args.version, current)
    notes = extract_notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), current)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(notes, encoding="utf-8")
        print(f"Release notes verified: {current} -> {args.output}")
    else:
        print(notes, end="")


if __name__ == "__main__":
    main()
