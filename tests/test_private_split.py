from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from private_split import (
    PRIVATE_DATASET_ROOT_ENV_VAR,
    PRIVATE_EPISODES_FILENAME,
    load_private_split,
    load_private_split_manifest_info,
)
from splits import generate_frozen_split, load_frozen_split, load_split_manifest
from tasks.ruleshift_benchmark.protocol import InteractionLabel, Split
from validate import normalize_episode_payload


def test_load_private_split_returns_episodes(
    mounted_private_dataset_root: Path,
):
    records = load_private_split(mounted_private_dataset_root)
    assert len(records) == 16


def test_load_private_split_uses_mounted_environment_dataset():
    records = load_private_split()
    assert len(records) == 16


def test_load_private_split_partition_label(
    mounted_private_dataset_root: Path,
):
    records = load_private_split(mounted_private_dataset_root)
    for record in records:
        assert record.partition == "private_leaderboard"


def test_load_private_split_episode_split_label(
    mounted_private_dataset_root: Path,
):
    records = load_private_split(mounted_private_dataset_root)
    for record in records:
        assert record.episode.split is Split.PRIVATE


def test_load_private_split_manifest_metadata_matches_manifest_interface():
    manifest = load_split_manifest("private_leaderboard")
    records = load_private_split()

    for record in records:
        assert record.manifest_version == manifest.manifest_version
        assert record.seed_bank_version == manifest.seed_bank_version


def test_load_private_split_matches_generated_episodes():
    manifest = load_split_manifest("private_leaderboard")
    generated = generate_frozen_split(manifest)
    loaded = load_private_split()

    assert len(loaded) == len(generated)
    for generated_record, loaded_record in zip(generated, loaded):
        assert generated_record.seed == loaded_record.seed
        assert generated_record.partition == loaded_record.partition
        assert generated_record.manifest_version == loaded_record.manifest_version
        assert generated_record.seed_bank_version == loaded_record.seed_bank_version
        assert normalize_episode_payload(generated_record.episode) == normalize_episode_payload(
            loaded_record.episode
        )


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


def test_private_manifest_info_comes_from_private_episodes_payload():
    payload = load_private_split_manifest_info()

    assert payload["manifest_version"] == "R14"
    assert payload["seed_bank_version"] == "R14-private-mounted-test"
    assert payload["episode_split"] == "private"
    assert len(payload["seeds"]) == 16


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


def test_load_private_split_wrong_partition_raises(
    mounted_private_dataset_root: Path,
):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    data["partition"] = "dev"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="partition"):
            load_private_split(Path(tmpdir))


def test_load_private_split_wrong_manifest_version_raises(
    mounted_private_dataset_root: Path,
):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    data["manifest_version"] = "R99"
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="manifest_version"):
            load_private_split(Path(tmpdir))


def test_load_private_split_empty_episodes_raises(
    mounted_private_dataset_root: Path,
):
    data = json.loads(
        (mounted_private_dataset_root / PRIVATE_EPISODES_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    data["episodes"] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / PRIVATE_EPISODES_FILENAME
        bad_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="episodes"):
            load_private_split(Path(tmpdir))
