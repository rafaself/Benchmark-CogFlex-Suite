from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.private_builder import (
    build_private_episodes_payload,
    load_private_seed_manifest,
    write_private_dataset_artifact,
)
from core.private_split import PRIVATE_EPISODES_FILENAME, PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION
from core.splits import FrozenSplitManifest
from tasks.ruleshift_benchmark.protocol import Split
from tasks.ruleshift_benchmark.schema import (
    DIFFICULTY_VERSION,
    GENERATOR_VERSION,
    SPEC_VERSION,
    TEMPLATE_SET_VERSION,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "build_private_dataset_artifact.py"


def _manifest_payload(seeds: list[int]) -> dict[str, object]:
    return {
        "partition": "private_leaderboard",
        "episode_split": "private",
        "manifest_version": "R14",
        "seed_bank_version": "R14-private-test",
        "spec_version": SPEC_VERSION,
        "generator_version": GENERATOR_VERSION,
        "template_set_version": TEMPLATE_SET_VERSION,
        "difficulty_version": DIFFICULTY_VERSION,
        "seeds": seeds,
    }


def _write_manifest(tmp_path: Path, seeds: list[int]) -> Path:
    manifest_path = tmp_path / "private_leaderboard.json"
    manifest_path.write_text(json.dumps(_manifest_payload(seeds), indent=2) + "\n", encoding="utf-8")
    return manifest_path


def test_load_private_seed_manifest_parses_canonical_private_manifest(tmp_path: Path):
    manifest_path = _write_manifest(tmp_path, [37800, 37801, 37802])

    manifest = load_private_seed_manifest(manifest_path)

    assert manifest == FrozenSplitManifest(
        partition="private_leaderboard",
        episode_split=Split.PRIVATE,
        manifest_version="R14",
        seed_bank_version="R14-private-test",
        spec_version=SPEC_VERSION,
        generator_version=GENERATOR_VERSION,
        template_set_version=TEMPLATE_SET_VERSION,
        difficulty_version=DIFFICULTY_VERSION,
        seeds=(37800, 37801, 37802),
    )


def test_build_private_episodes_payload_emits_private_attachment_contract():
    manifest = FrozenSplitManifest(
        partition="private_leaderboard",
        episode_split=Split.PRIVATE,
        manifest_version="R14",
        seed_bank_version="R14-private-test",
        spec_version=SPEC_VERSION,
        generator_version=GENERATOR_VERSION,
        template_set_version=TEMPLATE_SET_VERSION,
        difficulty_version=DIFFICULTY_VERSION,
        seeds=(37800, 37801),
    )

    payload = build_private_episodes_payload(manifest)

    assert payload["partition"] == "private_leaderboard"
    assert payload["episode_split"] == "private"
    assert payload["benchmark_version"] == "R14"
    assert payload["schema_version"] == PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION
    assert len(payload["episodes"]) == 2
    assert payload["artifact_checksum"]


def test_write_private_dataset_artifact_materializes_private_episodes_json(tmp_path: Path):
    manifest_path = _write_manifest(tmp_path, [37800, 37801, 37802, 37803])

    episodes_path = write_private_dataset_artifact(tmp_path / "dataset", manifest_path=manifest_path)

    assert episodes_path.name == PRIVATE_EPISODES_FILENAME
    payload = json.loads(episodes_path.read_text(encoding="utf-8"))
    assert payload["partition"] == "private_leaderboard"
    assert payload["episode_split"] == "private"
    assert len(payload["episodes"]) == 4


def test_build_private_dataset_artifact_script_writes_dataset_root(tmp_path: Path):
    manifest_path = _write_manifest(tmp_path, [37800, 37801])
    output_dir = tmp_path / "private-dataset"

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT_PATH),
            "--output-dir",
            str(output_dir),
            "--manifest-path",
            str(manifest_path),
        ],
        cwd=_REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert Path(result.stdout.strip()) == output_dir.resolve()
    assert (output_dir / PRIVATE_EPISODES_FILENAME).is_file()
