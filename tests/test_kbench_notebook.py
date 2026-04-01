from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
_NOTEBOOK_PATH = _REPO_ROOT / "packaging" / "kaggle" / "ruleshift_notebook_task.ipynb"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from core.kaggle import validate_kaggle_payload  # noqa: E402

import tests.kbench_shim as _shim  # noqa: E402

sys.modules["kaggle_benchmarks"] = _shim  # type: ignore[assignment]
import kaggle_benchmarks as kbench  # noqa: E402

_EXPECTED_PUBLIC_EPISODES = 54
_EXPECTED_PRIVATE_EPISODES = 270
_EXPECTED_ATTACHED_EPISODES = _EXPECTED_PUBLIC_EPISODES + _EXPECTED_PRIVATE_EPISODES


def _read_notebook_sources() -> str:
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", ())) for cell in notebook["cells"])


def _read_code_cell(cell_id: str) -> dict:
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return next(cell for cell in notebook["cells"] if cell.get("cell_type") == "code" and cell.get("id") == cell_id)


def _execute_code_cell(ns: dict, cell_id: str) -> None:
    cell = _read_code_cell(cell_id)
    source = "".join(cell.get("source", ()))
    filtered = "\n".join(line for line in source.splitlines() if not line.strip().startswith("%"))
    if filtered.strip():
        exec(compile(filtered, f"<{cell['id']}>", "exec"), ns)  # noqa: S102


def _execute_notebook_cells(*, stop_before_cell_id: str | None = None) -> dict:
    cells = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))["cells"]
    ns: dict = {
        "__builtins__": __import__("builtins"),
    }
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        if stop_before_cell_id is not None and cell.get("id") == stop_before_cell_id:
            break
        _execute_code_cell(ns, cell["id"])
    return ns


def _execute_choose_magic() -> object:
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    choose_cell = next(
        cell
        for cell in reversed(notebook["cells"])
        if cell.get("cell_type") == "code" and "%choose" in "".join(cell.get("source", ()))
    )
    choose_line = next(
        line.strip()
        for line in "".join(choose_cell.get("source", ())).splitlines()
        if line.strip().startswith("%choose ")
    )
    chosen_task = choose_line.split(maxsplit=1)[1]
    return kbench.choose(chosen_task)


@pytest.fixture(autouse=True)
def _patch_kaggle_runtime_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _original_is_dir = Path.is_dir

    def _kaggle_aware_is_dir(self: Path) -> bool:
        if str(self) == "/kaggle/input/datasets/raptorengineer/ruleshift-runtime/src":
            return True
        return _original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", _kaggle_aware_is_dir)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    kbench.reset_registry()
    yield
    kbench.reset_registry()


@pytest.fixture(autouse=True)
def _run_output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RULESHIFT_RUN_OUTPUT_DIR", str(tmp_path / "notebook-run"))
    monkeypatch.setenv("RULESHIFT_RUN_ID", "test-run")
    yield
    monkeypatch.delenv("RULESHIFT_RUN_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("RULESHIFT_RUN_ID", raising=False)


def test_notebook_source_keeps_binary_only_leaderboard_surface():
    source = _read_notebook_sources()

    assert 'name="ruleshift_benchmark_v1_binary_row"' in source
    assert "store_task=False" in source
    assert '@kbench.task(\n    name="ruleshift_benchmark_v1_binary"' in source
    assert "def ruleshift_benchmark_v1_binary(llm) -> tuple[int, int]:" in source
    assert "load_leaderboard_dataframe" in source
    assert "build_audit_catalog" in source
    assert "build_audit_balance" in source
    assert "build_audit_failures" in source
    assert "run_binary_task" in source
    assert 'audit_catalog = build_audit_catalog(frozen_splits["public_leaderboard"])' in source
    assert "audit_balance = build_audit_balance(audit_catalog)" in source
    assert "_ruleshift_benchmark_v1_binary_row.evaluate(" in source
    assert "def _run_ruleshift_benchmark_v1_binary_eval(llm):" in source
    assert "eval_df = leaderboard_df" in source
    assert "_RULESHIFT_BINARY_DF = None" in source
    assert "_RULESHIFT_PAYLOAD = None" in source
    assert "_RULESHIFT_OFFICIAL_RESULT = None" in source
    assert "official_result = (payload[\"numerator\"], payload[\"denominator\"])" in source
    assert "global _RULESHIFT_BINARY_DF, _RULESHIFT_PAYLOAD, _RULESHIFT_OFFICIAL_RESULT" in source
    assert "_RULESHIFT_BINARY_DF = binary_df" in source
    assert "_RULESHIFT_PAYLOAD = payload" in source
    assert "_RULESHIFT_OFFICIAL_RESULT = official_result" in source
    assert "returns only `(numerator, denominator)`" in source
    assert "return official_result" in source
    assert "score = ruleshift_benchmark_v1_binary(kbench.llm)" in source
    assert "payload = _RULESHIFT_PAYLOAD" in source
    assert 'raise RuntimeError("ruleshift_benchmark_v1_binary did not populate _RULESHIFT_PAYLOAD")' in source
    assert "%choose ruleshift_benchmark_v1_binary" in source
    assert "pd.DataFrame(" in source
    assert ".set_index(\"Field\")" in source
    assert "\n_status_df" in source
    assert "\n_result_df" in source
    assert "\n_summary_df" in source
    assert "\naudit_catalog" in source
    assert "\naudit_balance" in source
    assert "audit_failures = build_audit_failures(_RULESHIFT_BINARY_DF, audit_catalog)" in source
    assert ".style" not in source
    assert ".to_string(index=False)" not in source


def test_notebook_executes_end_to_end_with_private_mount():
    ns = _execute_notebook_cells()

    assert set(ns["frozen_splits"]) == {"public_leaderboard", "private_leaderboard"}
    assert set(ns["leaderboard_df"]["split"]) == {"public_leaderboard", "private_leaderboard"}
    assert len(ns["frozen_splits"]["public_leaderboard"]) == _EXPECTED_PUBLIC_EPISODES
    assert len(ns["frozen_splits"]["private_leaderboard"]) == _EXPECTED_PRIVATE_EPISODES
    assert len(ns["leaderboard_df"]) == _EXPECTED_ATTACHED_EPISODES
    assert str(ns["RUNTIME_SRC"]) in sys.path

    registry = kbench.get_registry()
    assert set(registry) == {"ruleshift_benchmark_v1_binary"}
    assert "_ruleshift_benchmark_v1_binary_row" in ns
    assert ns["_ruleshift_benchmark_v1_binary_row"].store_task is False
    assert ns["_ruleshift_benchmark_v1_binary_row"].evaluate_call_count == 1
    assert ns["_ruleshift_benchmark_v1_binary_row"].last_evaluation_data is not None
    assert len(ns["_ruleshift_benchmark_v1_binary_row"].last_evaluation_data) == len(ns["leaderboard_df"])
    assert set(ns["_ruleshift_benchmark_v1_binary_row"].last_evaluation_data["split"]) == {
        "public_leaderboard",
        "private_leaderboard",
    }

    assert ns["score"] == (ns["payload"]["numerator"], ns["payload"]["denominator"])
    assert ns["ruleshift_benchmark_v1_binary"].last_result == ns["score"]
    assert ns["_RULESHIFT_PAYLOAD"] == ns["payload"]
    assert ns["_RULESHIFT_OFFICIAL_RESULT"] == ns["score"]
    assert len(ns["audit_catalog"]) == len(ns["frozen_splits"]["public_leaderboard"])
    assert set(ns["audit_catalog"]["split"]) == {"public_leaderboard"}
    assert set(ns["audit_balance"]["dimension"]) == {
        "difficulty",
        "transition",
        "template_family",
        "template_id",
    }
    assert list(ns["audit_failures"].columns) == [
        "episode_id",
        "split",
        "difficulty",
        "transition",
        "template_family",
        "template_id",
        "num_correct",
        "total",
        "missed",
    ]
    validate_kaggle_payload(ns["payload"])
    assert set(ns["payload"]) == {
        "score",
        "numerator",
        "denominator",
        "total_episodes",
        "benchmark_version",
        "split",
        "manifest_version",
    }
    assert ns["payload"]["total_episodes"] == len(ns["leaderboard_df"])
    assert ns["payload"]["total_episodes"] == _EXPECTED_ATTACHED_EPISODES
    assert ns["payload"]["split"] == "frozen_leaderboard"
    assert ns["_RULESHIFT_BINARY_DF"] is not None
    assert len(ns["_RULESHIFT_BINARY_DF"]) == len(ns["leaderboard_df"])
    assert "RUN_LOG_PATH" not in ns
    assert "DIAGNOSTICS_SUMMARY_PATH" not in ns
    assert "RUN_MANIFEST_PATH" not in ns
    assert "RUN_EPISODE_LEDGER_PATH" not in ns

    artifact_paths = [path.name for path in kbench.list_artifacts()]
    assert artifact_paths == [
        "ruleshift_benchmark_v1_binary.run.json",
        "ruleshift_benchmark_v1_binary.task.json",
    ]
    assert all("row" not in name for name in artifact_paths)

    task_artifact = json.loads(kbench.list_artifacts()[1].read_text(encoding="utf-8"))
    run_artifact = json.loads(kbench.list_artifacts()[0].read_text(encoding="utf-8"))
    assert task_artifact["task_name"] == "ruleshift_benchmark_v1_binary"
    assert task_artifact["artifact_scope"] == "intermediate"
    assert run_artifact["task_name"] == "ruleshift_benchmark_v1_binary"
    assert run_artifact["run_type"] == "single_invocation"
    assert run_artifact["result"] == list(ns["score"])
    assert "total_episodes" not in run_artifact


def test_choose_publishes_only_aggregate_artifacts():
    ns = _execute_notebook_cells()

    published_payload = _execute_choose_magic()

    assert published_payload == ns["score"]
    artifact_paths = [path.name for path in kbench.list_artifacts()]
    assert artifact_paths == [
        "published.run.json",
        "published.task.json",
        "ruleshift_benchmark_v1_binary.run.json",
        "ruleshift_benchmark_v1_binary.task.json",
    ]

    published_task = json.loads((Path(os.environ["RULESHIFT_RUN_OUTPUT_DIR"]) / "published.task.json").read_text(encoding="utf-8"))
    published_run = json.loads((Path(os.environ["RULESHIFT_RUN_OUTPUT_DIR"]) / "published.run.json").read_text(encoding="utf-8"))
    assert published_task["task_name"] == "ruleshift_benchmark_v1_binary"
    assert published_task["artifact_scope"] == "published"
    assert published_run["task_name"] == "ruleshift_benchmark_v1_binary"
    assert published_run["artifact_scope"] == "published"
    assert published_run["run_type"] == "single_invocation"
    assert published_run["result"] == list(ns["score"])
    assert "row" not in published_task["task_name"]
    assert ns["_RULESHIFT_PAYLOAD"] == ns["payload"]
    assert ns["_RULESHIFT_OFFICIAL_RESULT"] == ns["score"]


def test_notebook_executes_public_only_without_private_mount(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RULESHIFT_PRIVATE_DATASET_ROOT", raising=False)
    ns = _execute_notebook_cells()

    assert ns["PRIVATE_DATASET_ROOT"] is None
    assert set(ns["frozen_splits"]) == {"public_leaderboard"}
    assert set(ns["leaderboard_df"]["split"]) == {"public_leaderboard"}
    assert len(ns["frozen_splits"]["public_leaderboard"]) == _EXPECTED_PUBLIC_EPISODES
    assert len(ns["leaderboard_df"]) == _EXPECTED_PUBLIC_EPISODES
    assert ns["score"] == (ns["payload"]["numerator"], ns["payload"]["denominator"])
    assert ns["_RULESHIFT_OFFICIAL_RESULT"] == ns["score"]
    assert len(ns["audit_catalog"]) == _EXPECTED_PUBLIC_EPISODES
    assert set(ns["audit_catalog"]["split"]) == {"public_leaderboard"}
    assert ns["payload"]["total_episodes"] == len(ns["leaderboard_df"])
    assert ns["payload"]["split"] == "public_leaderboard"


def test_payload_cell_fails_clearly_when_internal_payload_is_missing():
    ns = _execute_notebook_cells(stop_before_cell_id="cell-payload")
    ns["ruleshift_benchmark_v1_binary"].fn = lambda llm: (1, 2)

    with pytest.raises(RuntimeError, match="did not populate _RULESHIFT_PAYLOAD"):
        _execute_code_cell(ns, "cell-payload")


def test_last_code_cell_selects_binary_task():
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    last_code = next(cell for cell in reversed(notebook["cells"]) if cell.get("cell_type") == "code")
    magic_lines = [line.strip() for line in "".join(last_code.get("source", ())).splitlines() if line.strip().startswith("%")]

    assert magic_lines == ["%choose ruleshift_benchmark_v1_binary"]
