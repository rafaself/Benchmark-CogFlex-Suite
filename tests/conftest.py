import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.private_split import (  # noqa: E402
    PRIVATE_DATASET_ROOT_ENV_VAR,
    PRIVATE_EPISODES_FILENAME,
)
from core.splits import MANIFEST_VERSION  # noqa: E402
from tasks.ruleshift_benchmark.generator import generate_episode  # noqa: E402
from tasks.ruleshift_benchmark.protocol import Split  # noqa: E402
from validate import normalize_episode_payload  # noqa: E402


_TEST_PRIVATE_SEEDS = tuple(range(20000, 20016))
_TEST_PRIVATE_SEED_BANK_VERSION = "R14-private-mounted-test"


@pytest.fixture(scope="session")
def mounted_private_dataset_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("private-dataset")
    episodes_path = dataset_root / PRIVATE_EPISODES_FILENAME
    episodes_payload = {
        "partition": "private_leaderboard",
        "episode_split": "private",
        "manifest_version": MANIFEST_VERSION,
        "seed_bank_version": _TEST_PRIVATE_SEED_BANK_VERSION,
        "episode_count": len(_TEST_PRIVATE_SEEDS),
        "retired_seed_bank_versions": [],
        "episodes": [
            {
                "seed": seed,
                "episode": normalize_episode_payload(
                    generate_episode(seed, split=Split.PRIVATE)
                ),
            }
            for seed in _TEST_PRIVATE_SEEDS
        ],
    }
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
