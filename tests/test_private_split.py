from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.private_split import (
    PRIVATE_DATASET_ROOT_ENV_VAR,
    PRIVATE_EPISODES_FILENAME,
    PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION,
    discover_private_dataset_root,
    load_private_split,
    resolve_private_dataset_root,
)
from core.splits import generate_frozen_split, load_frozen_split, load_split_manifest
from tasks.ruleshift_benchmark.protocol import InteractionLabel, Split

_EXPECTED_PRIVATE_EPISODE_COUNT = 270


def test_load_private_split_returns_episodes(mounted_private_dataset_root: Path):
    records = load_private_split(mounted_private_dataset_root)
    assert len(records) == _EXPECTED_PRIVATE_EPISODE_COUNT


def test_load_private_split_uses_mounted_environment_dataset():
    records = load_private_split()
    assert len(records) == _EXPECTED_PRIVATE_EPISODE_COUNT


def test_load_private_split_partition_label(mounted_private_dataset_root: Path):
    records = load_private_split(mounted_private_dataset_root)
    for record in records:
        assert record.partition == "private_leaderboard"


def test_load_private_split_episode_split_label(mounted_private_dataset_root: Path):
    records = load_private_split(mounted_private_dataset_root)
    for record in records:
        assert record.episode.split is Split.PRIVATE


def test_load_private_split_manifest_metadata_matches_manifest_interface():
    manifest = load_split_manifest("private_leaderboard")
    records = load_private_split()

    assert manifest.partition == "private_leaderboard"
    assert manifest.manifest_version == "R14"
    assert manifest.seed_bank_version
    assert manifest.episode_split is Split.PRIVATE
    assert manifest.seeds == tuple(record.seed for record in records)

    for record in records:
        assert record.manifest_version == manifest.manifest_version
        assert record.seed_bank_version == manifest.seed_bank_version


def test_private_split_cannot_be_regenerated_from_manifest():
    manifest = load_split_manifest("private_leaderboard")
    with pytest.raises(ValueError, match="runtime regeneration is disabled"):
        generate_frozen_split(manifest)


def test_load_frozen_split_uses_private_loader_for_private_partition():
    direct = load_private_split()
    via_partition = load_frozen_split("private_leaderboard")
    assert via_partition == direct


def test_private_split_probe_targets_are_valid():
    records = load_private_split()
    for record in records:
        assert len(record.episode.probe_targets) == 4
        for target in record.episode.probe_targets:
            assert isinstance(target, InteractionLabel)


def test_private_fixture_payload_uses_current_schema_version(mounted_private_dataset_root: Path):
    payload = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )

    assert payload["benchmark_version"] == "R14"
    assert payload["schema_version"] == PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION
    assert payload["artifact_checksum"]
    assert payload["episode_split"] == "private"
    assert len(payload["episodes"]) == _EXPECTED_PRIVATE_EPISODE_COUNT


def test_load_private_split_missing_explicit_root_raises():
    with pytest.raises(FileNotFoundError, match="private_episodes.json not found"):
        load_private_split(Path("/nonexistent/path/that/does/not/exist"))


def test_load_private_split_missing_mount_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(PRIVATE_DATASET_ROOT_ENV_VAR, raising=False)
    with pytest.raises(
        FileNotFoundError,
        match="Private evaluation dataset is not attached",
    ):
        load_private_split()


def test_discover_private_dataset_root_returns_none_when_private_dataset_is_absent(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(PRIVATE_DATASET_ROOT_ENV_VAR, raising=False)
    assert discover_private_dataset_root() is None


def test_resolve_private_dataset_root_still_raises_when_private_dataset_is_absent(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(PRIVATE_DATASET_ROOT_ENV_VAR, raising=False)
    with pytest.raises(
        FileNotFoundError,
        match="Private evaluation dataset is not attached",
    ):
        resolve_private_dataset_root()


def test_load_private_split_wrong_partition_raises(mounted_private_dataset_root: Path):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    data["partition"] = "unexpected_partition"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="partition"):
            load_private_split(Path(tmpdir))


def test_load_private_split_wrong_benchmark_version_raises(mounted_private_dataset_root: Path):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    data["benchmark_version"] = "R99"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="benchmark_version"):
            load_private_split(Path(tmpdir))


def test_load_private_split_wrong_schema_version_raises(mounted_private_dataset_root: Path):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    data["schema_version"] = "private_split_artifact.v999"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="schema_version"):
            load_private_split(Path(tmpdir))


def test_load_private_split_empty_episodes_raises(mounted_private_dataset_root: Path):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    data["episodes"] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="episodes"):
            load_private_split(Path(tmpdir))


def test_load_private_split_rejects_checksum_mismatch(mounted_private_dataset_root: Path):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    data["artifact_checksum"] = "bad-checksum"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="artifact_checksum"):
            load_private_split(Path(tmpdir))
