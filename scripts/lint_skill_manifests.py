#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.skill_manifest import iter_manifest_paths, validate_repo_manifests


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill manifests")
    parser.add_argument(
        "--manifest",
        action="append",
        type=Path,
        help="Validate only the given manifest path(s)",
    )
    args = parser.parse_args()

    manifest_paths = args.manifest
    if manifest_paths is None:
        manifest_paths = iter_manifest_paths(ROOT)
    issues = validate_repo_manifests(ROOT, manifest_paths)
    if issues:
        for issue in issues:
            rel_path = issue.manifest_path.relative_to(ROOT)
            print(f"{rel_path}: {issue.message}", file=sys.stderr)
        return 1

    for manifest_path in manifest_paths:
        rel_path = manifest_path.relative_to(ROOT)
        print(f"OK {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
