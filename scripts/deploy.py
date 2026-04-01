#!/usr/bin/env python3
"""Local deploy entrypoint for the Kaggle runtime dataset and notebook bundle."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from ._package_build import KAGGLE_DIR, REPO_ROOT

DEFAULT_RUNTIME_OUTPUT_DIR = Path("/tmp/ruleshift-runtime-package")
DEFAULT_KERNEL_OUTPUT_DIR = Path("/tmp/ruleshift-kernel-bundle")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, build, and optionally publish the Kaggle runtime dataset and notebook bundle.",
    )
    parser.add_argument(
        "--runtime-output-dir",
        type=Path,
        default=DEFAULT_RUNTIME_OUTPUT_DIR,
        help="Output directory for the built Kaggle runtime dataset package.",
    )
    parser.add_argument(
        "--kernel-output-dir",
        type=Path,
        default=DEFAULT_KERNEL_OUTPUT_DIR,
        help="Output directory for the built Kaggle notebook bundle.",
    )
    parser.add_argument(
        "--release-message",
        default="Local deploy",
        help="Release note used when uploading a new Kaggle dataset version.",
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Run the full local validation and build flow without calling the Kaggle CLI publish commands.",
    )
    return parser


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{existing_pythonpath}:{src_path}"
    env["PYTHON"] = sys.executable
    return env


def _build_script(script_name: str, output_dir: Path, env: dict[str, str]) -> None:
    _run(
        [
            sys.executable,
            f"scripts/{script_name}",
            "--output-dir",
            str(output_dir),
        ],
        env=env,
    )


def _build_runtime_dataset(output_dir: Path, env: dict[str, str]) -> None:
    _build_script("build_runtime_dataset_package.py", output_dir, env)


def _build_kernel_bundle(output_dir: Path, env: dict[str, str]) -> None:
    _build_script("build_kernel_package.py", output_dir, env)


def _ensure_kaggle_credentials() -> None:
    token = os.environ.get("KAGGLE_API_TOKEN")
    if not token:
        return

    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    credentials_path = kaggle_dir / "kaggle.json"
    credentials_path.write_text(token, encoding="utf-8")
    credentials_path.chmod(0o600)


def _load_dataset_id() -> str:
    metadata = json.loads((KAGGLE_DIR / "dataset-metadata.json").read_text(encoding="utf-8"))
    dataset_id = metadata.get("id")
    if not isinstance(dataset_id, str) or not dataset_id:
        raise ValueError("dataset-metadata.json must contain a non-empty id")
    return dataset_id


def _publish_runtime_dataset(output_dir: Path, *, release_message: str, env: dict[str, str]) -> None:
    dataset_id = _load_dataset_id()
    status = subprocess.run(
        ["kaggle", "datasets", "status", dataset_id],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    status_output = (status.stdout or "") + (status.stderr or "")

    if status.returncode == 0:
        _run(
            [
                "kaggle",
                "datasets",
                "version",
                "--path",
                str(output_dir),
                "--message",
                release_message,
                "--dir-mode",
                "tar",
                "--quiet",
            ],
            env=env,
        )
        return

    lowered = status_output.lower()
    if any(token in lowered for token in ("401", "403", "unauth", "forbidden", "auth", "login", "token", "credential", "permission", "access denied")):
        raise RuntimeError(
            "Kaggle authentication/authorization failed while checking dataset status.\n"
            f"{status_output.strip()}"
        )
    if any(token in lowered for token in ("404", "not found", "does not exist", "could not find")):
        _run(
            [
                "kaggle",
                "datasets",
                "create",
                "--path",
                str(output_dir),
                "--dir-mode",
                "tar",
                "--quiet",
            ],
            env=env,
        )
        return

    raise RuntimeError(
        "Unable to determine dataset status from Kaggle CLI output.\n"
        f"{status_output.strip()}"
    )


def _publish_kernel_bundle(output_dir: Path, env: dict[str, str]) -> None:
    _run(
        [
            "kaggle",
            "kernels",
            "push",
            "--path",
            str(output_dir),
        ],
        env=env,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    env = _build_env()

    runtime_output_dir = args.runtime_output_dir.resolve()
    kernel_output_dir = args.kernel_output_dir.resolve()

    print("=== RuleShift local deploy ===")
    print(f"runtime_output_dir={runtime_output_dir}")
    print(f"kernel_output_dir={kernel_output_dir}")
    print(f"skip_publish={args.skip_publish}")

    _build_runtime_dataset(runtime_output_dir, env)
    _build_kernel_bundle(kernel_output_dir, env)

    if args.skip_publish:
        print("Publish step skipped.")
        print("=== Local deploy finished ===")
        return 0

    _ensure_kaggle_credentials()
    _run(["kaggle", "--version"], env=env)
    _publish_runtime_dataset(
        runtime_output_dir,
        release_message=args.release_message,
        env=env,
    )
    _publish_kernel_bundle(kernel_output_dir, env)
    print("=== Local deploy finished ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
