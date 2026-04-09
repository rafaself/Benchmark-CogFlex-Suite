#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tests_dir = root / "tests"
for candidate in (root, tests_dir):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.append(candidate_str)

from scripts.build_cogflex_dataset import PRIVATE_DATASET_ID, dataset_metadata  # noqa: E402
from cogflex_fixtures import write_private_bundle  # noqa: E402

ROOT = root
PRIVATE_DATASET_DIR = ROOT / "kaggle/dataset/private"
def build_private_bundle(output_dir: Path = PRIVATE_DATASET_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_paths = write_private_bundle(output_dir)
    metadata_path = output_dir / "dataset-metadata.json"
    metadata_path.write_text(
        json.dumps(dataset_metadata(PRIVATE_DATASET_ID, "CogFlex Suite Runtime Private"), indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        **bundle_paths,
        "metadata": metadata_path,
    }


def main() -> None:
    build_private_bundle()


if __name__ == "__main__":
    main()
