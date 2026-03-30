from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import sys

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(_REPO_ROOT / "src"))

from core.private_split import (  # noqa: E402
    PRIVATE_DATASET_ROOT_ENV_VAR,
    PRIVATE_EPISODES_FILENAME,
    PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION,
)
from core.splits import MANIFEST_VERSION  # noqa: E402
from tasks.ruleshift_benchmark.generator import generate_episode  # noqa: E402
from tasks.ruleshift_benchmark.protocol import Split  # noqa: E402

_TEST_PRIVATE_SEEDS = (
    40001,
    40016,
    40017,
    40018,
    40000,
    40004,
    40006,
    40008,
    40003,
    40005,
    40007,
    40012,
    40002,
    40010,
    40011,
    40015,
)


def _to_jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _build_private_artifact_payload(seeds: tuple[int, ...]) -> dict[str, object]:
    episodes = [
        {
            "seed": seed,
            "episode": _to_jsonable(generate_episode(seed, split=Split.PRIVATE)),
        }
        for seed in seeds
    ]
    payload: dict[str, object] = {
        "partition": "private_leaderboard",
        "episode_split": "private",
        "benchmark_version": MANIFEST_VERSION,
        "schema_version": PRIVATE_SPLIT_ARTIFACT_SCHEMA_VERSION,
        "episodes": episodes,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **payload,
        "artifact_checksum": hashlib.sha256(encoded).hexdigest(),
    }


@pytest.fixture(scope="session")
def mounted_private_dataset_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("private-dataset")
    episodes_path = dataset_root / PRIVATE_EPISODES_FILENAME
    episodes_payload = _build_private_artifact_payload(_TEST_PRIVATE_SEEDS)
    episodes_path.write_text(
        json.dumps(episodes_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return dataset_root


@pytest.fixture(autouse=True)
def _mounted_private_dataset_env(
    mounted_private_dataset_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        PRIVATE_DATASET_ROOT_ENV_VAR,
        str(mounted_private_dataset_root),
    )
    yield
    monkeypatch.delenv(PRIVATE_DATASET_ROOT_ENV_VAR, raising=False)
