#!/usr/bin/env python3
"""Build the minimal Kaggle package for RuleShift.

The output contains two ready-to-publish directories:
  - kernel/: notebook + kernel metadata
  - dataset/: runtime source subset + dataset metadata
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KAGGLE_DIR = REPO_ROOT / "kaggle"
RUNTIME_SRC_DIR = REPO_ROOT / "src"
DEFAULT_OUTPUT_DIR = Path("/tmp/ruleshift-kaggle-build")

NOTEBOOK_PATH = KAGGLE_DIR / "ruleshift_notebook_task.ipynb"
KERNEL_METADATA_PATH = KAGGLE_DIR / "kernel-metadata.json"
DATASET_METADATA_PATH = KAGGLE_DIR / "dataset-metadata.json"

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the minimal Kaggle notebook + runtime package.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the Kaggle package will be assembled.",
    )
    return parser


def _reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Required file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_runtime_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Required runtime source directory not found: {source}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def build_kaggle_package(output_dir: Path) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    kernel_dir = output_dir / "kernel"
    dataset_dir = output_dir / "dataset"

    _reset_output_dir(output_dir)

    _copy_file(NOTEBOOK_PATH, kernel_dir / NOTEBOOK_PATH.name)
    _copy_file(KERNEL_METADATA_PATH, kernel_dir / KERNEL_METADATA_PATH.name)
    _copy_file(DATASET_METADATA_PATH, dataset_dir / DATASET_METADATA_PATH.name)
    _copy_runtime_tree(RUNTIME_SRC_DIR, dataset_dir / "src")

    return kernel_dir, dataset_dir


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    kernel_dir, dataset_dir = build_kaggle_package(args.output_dir)
    print(args.output_dir.resolve())
    print(kernel_dir)
    print(dataset_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
