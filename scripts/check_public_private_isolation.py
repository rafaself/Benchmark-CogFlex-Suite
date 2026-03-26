#!/usr/bin/env python3
"""Fail when private split artifacts appear in public repo or packaging paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
KAGGLE_DIR = REPO_ROOT / "packaging" / "kaggle"
DEPLOY_RUNTIME_DIR = REPO_ROOT / "deploy" / "kaggle-runtime"

FORBIDDEN_PATHS = (
    SRC_DIR / "frozen_splits" / "private_leaderboard.json",
    KAGGLE_DIR / "private" / "private_episodes.json",
    KAGGLE_DIR / "private" / "dataset-metadata.json",
)
FORBIDDEN_FILENAMES = (
    "private_leaderboard.json",
    "private_episodes.json",
)


def _collect_public_location_errors() -> list[str]:
    errors: list[str] = []

    for path in FORBIDDEN_PATHS:
        if path.exists():
            errors.append(f"forbidden private artifact present: {path.relative_to(REPO_ROOT)}")

    private_packaging_dir = KAGGLE_DIR / "private"
    if private_packaging_dir.exists():
        errors.append(f"forbidden public packaging directory present: {private_packaging_dir.relative_to(REPO_ROOT)}")

    for search_root in (SRC_DIR / "frozen_splits", KAGGLE_DIR):
        if not search_root.exists():
            continue
        for filename in FORBIDDEN_FILENAMES:
            for path in search_root.rglob(filename):
                errors.append(f"forbidden filename in public location: {path.relative_to(REPO_ROOT)}")

    manifest_path = KAGGLE_DIR / "frozen_artifacts_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen_split_manifests = manifest.get("frozen_split_manifests", {})
    if "private_leaderboard" in frozen_split_manifests:
        errors.append("packaging/kaggle/frozen_artifacts_manifest.json exposes private_leaderboard")

    notebook_path = KAGGLE_DIR / "ruleshift_notebook_task.ipynb"
    notebook_text = notebook_path.read_text(encoding="utf-8")
    if "packaging/kaggle/private/private_episodes.json" in notebook_text:
        errors.append("official notebook still contains a repo-local private dataset fallback")

    staging_path = KAGGLE_DIR / "staging" / "ruleshift_benchmark_v1_kaggle_staging.ipynb"
    staging_text = staging_path.read_text(encoding="utf-8")
    if "packaging/kaggle/private/private_episodes.json" in staging_text:
        errors.append("staging notebook still contains a repo-local private dataset fallback")

    return errors


def _collect_runtime_errors(runtime_dir: Path) -> list[str]:
    if not runtime_dir.exists():
        return []

    errors: list[str] = []
    for filename in FORBIDDEN_FILENAMES:
        for path in runtime_dir.rglob(filename):
            errors.append(f"deploy runtime contains private artifact: {path.relative_to(REPO_ROOT)}")
    return errors


def main() -> int:
    errors = [
        *_collect_public_location_errors(),
        *_collect_runtime_errors(DEPLOY_RUNTIME_DIR),
    ]
    if errors:
        print("Public/private isolation check FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Public/private isolation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
