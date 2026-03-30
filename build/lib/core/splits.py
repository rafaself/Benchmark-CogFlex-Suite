from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Final

from tasks.ruleshift_benchmark.generator import generate_episode
from tasks.ruleshift_benchmark.protocol import Split, parse_split
from tasks.ruleshift_benchmark.schema import (
    DIFFICULTY_VERSION,
    GENERATOR_VERSION,
    SPEC_VERSION,
    TEMPLATE_SET_VERSION,
    Episode,
)

__all__ = [
    "PARTITIONS",
    "PUBLIC_PARTITIONS",
    "MANIFEST_VERSION",
    "FrozenSplitManifest",
    "FrozenSplitEpisode",
    "load_split_manifest",
    "generate_frozen_split",
    "load_frozen_split",
]

PARTITIONS: Final[tuple[str, ...]] = (
    "dev",
    "public_leaderboard",
    "private_leaderboard",
)
PUBLIC_PARTITIONS: Final[tuple[str, ...]] = (
    "dev",
    "public_leaderboard",
)
MANIFEST_VERSION: Final[str] = "R14"
_MANIFEST_FIELD_ORDER: Final[tuple[str, ...]] = (
    "partition",
    "episode_split",
    "manifest_version",
    "seed_bank_version",
    "spec_version",
    "generator_version",
    "template_set_version",
    "difficulty_version",
    "seeds",
)
_DEFAULT_MANIFEST_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "frozen_splits"
_PARTITION_TO_EPISODE_SPLIT: Final[dict[str, Split]] = {
    "dev": Split.DEV,
    "public_leaderboard": Split.PUBLIC,
    "private_leaderboard": Split.PRIVATE,
}


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _manifest_dir(repo_root: Path | str | None = None) -> Path:
    if repo_root is None:
        return _DEFAULT_MANIFEST_DIR
    return Path(repo_root).resolve() / "src" / "frozen_splits"


@dataclass(frozen=True, slots=True)
class FrozenSplitManifest:
    partition: str
    episode_split: Split
    manifest_version: str
    seed_bank_version: str
    spec_version: str
    generator_version: str
    template_set_version: str
    difficulty_version: str
    seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.partition not in PARTITIONS:
            raise ValueError(f"unknown partition: {self.partition}")

        object.__setattr__(self, "episode_split", parse_split(self.episode_split))
        expected_split = _PARTITION_TO_EPISODE_SPLIT[self.partition]
        if self.episode_split is not expected_split:
            raise ValueError("episode_split does not match the canonical partition mapping")

        if self.manifest_version != MANIFEST_VERSION:
            raise ValueError(f"manifest_version must equal {MANIFEST_VERSION}")
        if not _is_nonempty_string(self.seed_bank_version):
            raise ValueError("seed_bank_version must be a non-empty string")
        if self.spec_version != SPEC_VERSION:
            raise ValueError(f"spec_version must equal {SPEC_VERSION}")
        if self.generator_version != GENERATOR_VERSION:
            raise ValueError(f"generator_version must equal {GENERATOR_VERSION}")
        if self.template_set_version != TEMPLATE_SET_VERSION:
            raise ValueError(f"template_set_version must equal {TEMPLATE_SET_VERSION}")
        if self.difficulty_version != DIFFICULTY_VERSION:
            raise ValueError(f"difficulty_version must equal {DIFFICULTY_VERSION}")

        normalized_seeds = tuple(self.seeds)
        if not normalized_seeds:
            raise ValueError("seeds must not be empty")
        if any(not _is_plain_int(seed) for seed in normalized_seeds):
            raise TypeError("seeds must contain only int values")
        if len(set(normalized_seeds)) != len(normalized_seeds):
            raise ValueError("seeds must contain unique values")
        object.__setattr__(self, "seeds", normalized_seeds)


@dataclass(frozen=True, slots=True)
class FrozenSplitEpisode:
    partition: str
    seed: int
    manifest_version: str
    seed_bank_version: str
    episode: Episode

    def __post_init__(self) -> None:
        if self.partition not in PARTITIONS:
            raise ValueError(f"unknown partition: {self.partition}")
        if not _is_plain_int(self.seed):
            raise TypeError("seed must be an int")
        if self.manifest_version != MANIFEST_VERSION:
            raise ValueError(f"manifest_version must equal {MANIFEST_VERSION}")
        if not _is_nonempty_string(self.seed_bank_version):
            raise ValueError("seed_bank_version must be a non-empty string")
        if not isinstance(self.episode, Episode):
            raise TypeError("episode must be an Episode")
        expected_split = _PARTITION_TO_EPISODE_SPLIT[self.partition]
        if self.episode.split is not expected_split:
            raise ValueError("episode split does not match partition mapping")


def load_split_manifest(
    partition: str,
    repo_root: Path | str | None = None,
) -> FrozenSplitManifest:
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition: {partition}")
    if partition == "private_leaderboard":
        return _load_private_split_manifest()

    manifest_path = _manifest_dir(repo_root) / f"{partition}.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_fields = tuple(payload)
    if actual_fields != _MANIFEST_FIELD_ORDER:
        raise ValueError(
            "manifest fields must exactly match the canonical order: "
            + ", ".join(_MANIFEST_FIELD_ORDER)
        )

    return FrozenSplitManifest(
        partition=payload["partition"],
        episode_split=payload["episode_split"],
        manifest_version=payload["manifest_version"],
        seed_bank_version=payload["seed_bank_version"],
        spec_version=payload["spec_version"],
        generator_version=payload["generator_version"],
        template_set_version=payload["template_set_version"],
        difficulty_version=payload["difficulty_version"],
        seeds=tuple(payload["seeds"]),
    )


def generate_frozen_split(manifest: FrozenSplitManifest) -> tuple[FrozenSplitEpisode, ...]:
    if manifest.partition == "private_leaderboard":
        raise ValueError(
            "private_leaderboard must be loaded from the authorized private artifact; "
            "runtime regeneration is disabled"
        )
    return tuple(
        FrozenSplitEpisode(
            partition=manifest.partition,
            seed=seed,
            manifest_version=manifest.manifest_version,
            seed_bank_version=manifest.seed_bank_version,
            episode=generate_episode(seed, split=manifest.episode_split),
        )
        for seed in manifest.seeds
    )


def load_frozen_split(partition: str) -> tuple[FrozenSplitEpisode, ...]:
    if partition == "private_leaderboard":
        from core.private_split import load_private_split

        return load_private_split()
    return generate_frozen_split(load_split_manifest(partition))


def _load_private_split_manifest() -> FrozenSplitManifest:
    from core.private_split import (
        PRIVATE_EPISODES_FILENAME,
        load_private_split,
        resolve_private_dataset_root,
    )

    private_root = resolve_private_dataset_root()
    payload = json.loads(
        (private_root / PRIVATE_EPISODES_FILENAME).read_text(encoding="utf-8")
    )
    records = load_private_split(private_root)
    return FrozenSplitManifest(
        partition="private_leaderboard",
        episode_split=payload["episode_split"],
        manifest_version=payload["benchmark_version"],
        seed_bank_version=payload["artifact_checksum"],
        spec_version=SPEC_VERSION,
        generator_version=GENERATOR_VERSION,
        template_set_version=TEMPLATE_SET_VERSION,
        difficulty_version=DIFFICULTY_VERSION,
        seeds=tuple(record.seed for record in records),
    )
