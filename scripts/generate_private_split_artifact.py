#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.private_split import write_private_split_artifact

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_seeds(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("seed file must contain a non-empty JSON array of integer seeds")
    if any(not isinstance(seed, int) or isinstance(seed, bool) for seed in payload):
        raise ValueError("seed file must contain only integer seeds")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the held-out private split artifact offline.",
    )
    parser.add_argument(
        "--benchmark-version",
        required=True,
        help="Benchmark version for the private artifact, for example R14.",
    )
    parser.add_argument(
        "--seeds-file",
        type=Path,
        required=True,
        help="JSON file containing the ordered private seeds.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for the generated private_episodes.json artifact.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seeds = _load_seeds(args.seeds_file)
    resolved_output = args.output.resolve()
    try:
        resolved_output.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        raise ValueError(
            "output must be outside the public repository tree; "
            "write the private artifact to a separate private dataset location"
        )
    output_path = write_private_split_artifact(
        resolved_output,
        benchmark_version=args.benchmark_version,
        seeds=seeds,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
