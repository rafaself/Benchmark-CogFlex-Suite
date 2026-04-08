import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from cogflex_fixtures import public_fixture, write_private_bundle


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "kaggle/notebook/cogflex_notebook_task.ipynb"
PUBLIC_ROWS_PATH = ROOT / "kaggle/dataset/public/public_leaderboard_rows.json"


class _BenchStub:
    @staticmethod
    def task(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator


class _StrictBenchStub:
    @staticmethod
    def task(*args, **kwargs):
        def decorator(fn):
            if fn.__annotations__.get("return") is not dict:
                raise TypeError("task return annotation must be plain dict")
            return fn

        return decorator


def _load_code_cells() -> dict[str, str]:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return {
        cell["id"]: "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    }


def load_bootstrap_namespace() -> dict[str, object]:
    code_cells = _load_code_cells()
    fake_kbench = types.ModuleType("kaggle_benchmarks")
    fake_kbench.task = _BenchStub.task
    fake_pd = types.ModuleType("pandas")

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_root = Path(tmpdir)
        (dataset_root / "public_leaderboard_rows.json").write_text("[]", encoding="utf-8")
        namespace: dict[str, object] = {}
        with patch.dict(
            sys.modules,
            {"kaggle_benchmarks": fake_kbench, "pandas": fake_pd},
        ), patch.dict(
            os.environ,
            {
                "COGFLEX_EVAL_SPLIT": "public",
                "COGFLEX_DATASET_ROOT": str(dataset_root),
                "COGFLEX_PRIVATE_DATASET_ROOT": "",
                "COGFLEX_PRIVATE_ANSWER_KEY_PATH": "",
            },
            clear=False,
        ):
            exec(code_cells["cell-bootstrap"], namespace)
    return namespace


def load_notebook_namespace() -> dict[str, object]:
    code_cells = _load_code_cells()
    namespace: dict[str, object] = {
        "Path": Path,
        "kbench": _BenchStub(),
        "pd": None,
        "PROBE_COUNT": 8,
        "TURN_COUNT": 3,
        "FACULTY_ID": "executive_functions/cognitive_flexibility",
        "TURN_HEADER_PREFIX": "CogFlex suite task. Episode ",
        "OUTPUT_INSTRUCTION": "Return exactly 8 outputs in order, one per probe. Use only type_a or type_b.",
        "ALLOWED_SUITE_TASKS": {
            "explicit_rule_update",
            "latent_rule_update",
            "context_binding",
            "trial_cued_switch",
        },
        "SUITE_SHIFT_MODES": {
            "explicit_rule_update": "explicit_instruction",
            "latent_rule_update": "latent_example_change",
            "context_binding": "context_gate",
            "trial_cued_switch": "cue_switching",
        },
    }
    exec(code_cells["cell-runtime-types"], namespace)
    exec(code_cells["cell-runtime-normalize"], namespace)
    exec(code_cells["cell-runtime-score"], namespace)
    runtime_load_prefix = code_cells["cell-runtime-load"].split("leaderboard_rows = load_selected_rows()", 1)[0]
    exec(runtime_load_prefix, namespace)
    namespace.update(
        {
            "EVAL_SPLIT": "public",
            "ROWS_PATH": PUBLIC_ROWS_PATH,
            "EXPECTED_PUBLIC_EPISODE_COUNT": 120,
            "EXPECTED_PRIVATE_EPISODE_COUNT": 480,
            "EXPECTED_EPISODES_PER_TASK": {"public": 30, "private": 120},
            "PRIVATE_ANSWER_KEY_PATH_ENV_VAR": "COGFLEX_PRIVATE_ANSWER_KEY_PATH",
            "PRIVATE_ANSWER_KEY_PATH": None,
        }
    )
    return namespace


class FakeLLM:
    def __init__(self, final_response: object) -> None:
        self.final_response = final_response
        self.calls: list[tuple[str, object | None]] = []

    def prompt(self, prompt: str, schema: object | None = None) -> object:
        self.calls.append((prompt, schema))
        if schema is None:
            return "ack"
        return self.final_response


class FakeRuns:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self._results = results

    def __bool__(self) -> bool:
        return True

    def as_dataframe(self):
        class _ResultFrame:
            def __init__(self, results):
                self.result = results

            def reset_index(self, drop: bool = True):
                return self

            def __len__(self):
                return len(self.result)

        return _ResultFrame(self._results)


class CogflexNotebookRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bootstrap_namespace = load_bootstrap_namespace()
        cls.namespace = load_notebook_namespace()
        cls.rows, _answers, _report = public_fixture()

    def test_load_rows_accepts_the_public_split(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            loaded_rows = self.namespace["_load_rows"](PUBLIC_ROWS_PATH)
        self.assertEqual(len(loaded_rows), 120)
        self.assertEqual(len(loaded_rows[0]["inference"]["turns"]), 3)
        self.assertEqual(
            sorted(loaded_rows[0]["analysis"]),
            ["difficulty_bin", "faculty_id", "shift_mode", "suite_task_id"],
        )
        self.assertEqual(len(loaded_rows[0]["scoring"]["final_probe_targets"]), 8)

    def test_runtime_score_cell_uses_plain_dict_return_type_for_kbench_task(self) -> None:
        code_cells = _load_code_cells()
        namespace: dict[str, object] = {
            "Path": Path,
            "kbench": _StrictBenchStub(),
            "pd": None,
            "PROBE_COUNT": 8,
            "TURN_COUNT": 3,
        }
        exec(code_cells["cell-runtime-types"], namespace)
        exec(code_cells["cell-runtime-normalize"], namespace)
        exec(code_cells["cell-runtime-score"], namespace)
        self.assertIs(namespace["run_binary_task"].__annotations__["return"], dict)

    def test_bootstrap_uses_expected_kaggle_dataset_roots(self) -> None:
        self.assertEqual(
            self.bootstrap_namespace["DEFAULT_DATASET_ROOT"],
            Path("/kaggle/input/datasets/raptorengineer/cogflex-suite-runtime"),
        )
        self.assertEqual(
            self.bootstrap_namespace["DEFAULT_PRIVATE_DATASET_ROOT"],
            Path("/kaggle/input/datasets/raptorengineer/cogflex-suite-runtime-private"),
        )

    def test_notebook_selects_main_task_with_choose_cell(self) -> None:
        code_cells = _load_code_cells()
        self.assertIn("cell-choose", code_cells)
        self.assertIn("%choose cogflex_suite_binary", code_cells["cell-choose"])

    def test_load_rows_accepts_private_inference_only_split(self) -> None:
        self.namespace["EVAL_SPLIT"] = "private"
        with tempfile.TemporaryDirectory() as tmpdir, contextlib.redirect_stdout(io.StringIO()):
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            loaded_rows = self.namespace["_load_rows"](bundle_paths["rows"])
        self.assertEqual(len(loaded_rows), 480)
        self.assertNotIn("scoring", loaded_rows[0])
        self.namespace["EVAL_SPLIT"] = "public"

    def test_attach_private_scoring_joins_by_episode_id(self) -> None:
        self.namespace["EVAL_SPLIT"] = "private"
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            private_rows = self.namespace["_load_rows"](bundle_paths["rows"])
            self.namespace["PRIVATE_ANSWER_KEY_PATH"] = bundle_paths["answer_key"]
            attached_rows = self.namespace["_attach_private_scoring"](private_rows)
        self.assertIn("scoring", attached_rows[0])
        self.assertEqual(len(attached_rows[0]["scoring"]["final_probe_targets"]), 8)
        self.namespace["PRIVATE_ANSWER_KEY_PATH"] = None
        self.namespace["EVAL_SPLIT"] = "public"

    def test_attach_private_scoring_requires_external_answer_key(self) -> None:
        self.namespace["EVAL_SPLIT"] = "private"
        self.namespace["PRIVATE_ANSWER_KEY_PATH"] = None
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            private_rows = self.namespace["_load_rows"](bundle_paths["rows"])
        with self.assertRaisesRegex(RuntimeError, "Private split requires an external answer key"):
            self.namespace["attach_selected_scoring"](private_rows)
        self.namespace["EVAL_SPLIT"] = "public"

    def test_validate_row_rejects_missing_turn(self) -> None:
        row = json.loads(json.dumps(self.rows[0]))
        row["inference"]["turns"] = row["inference"]["turns"][:2]
        with self.assertRaisesRegex(ValueError, "expected exactly 3 turns"):
            self.namespace["_validate_row"](row)

    def test_run_binary_task_sends_first_two_turns_before_scored_turn(self) -> None:
        row = self.rows[0]
        llm = FakeLLM(
            {
                **{f"probe_{index}": ("type_a" if index % 2 else "type_b") for index in range(1, 9)},
            }
        )
        result = self.namespace["run_binary_task"](llm, row["inference"]["turns"], tuple(row["scoring"]["final_probe_targets"]))
        self.assertEqual(result["denominator"], 8)
        self.assertEqual(len(result["predictions"]), 8)
        self.assertEqual(len(llm.calls), 3)
        self.assertIsNone(llm.calls[0][1])
        self.assertIsNone(llm.calls[1][1])
        self.assertIs(self.namespace["BinaryResponse"], llm.calls[2][1])

    def test_score_episode_returns_json_safe_predictions(self) -> None:
        predictions = tuple("type_a" if index % 2 else "type_b" for index in range(1, 9))
        result = self.namespace["score_episode"](predictions, predictions)
        self.assertEqual(result["predictions"], list(predictions))
        self.assertIsInstance(result["predictions"], list)

    def test_normalize_binary_response_accepts_plain_text(self) -> None:
        normalized = self.namespace["normalize_binary_response"](
            "type_a, type_b, type_a, type_b, type_a, type_b, type_a, type_b"
        )
        self.assertEqual(
            normalized,
            ("type_a", "type_b", "type_a", "type_b", "type_a", "type_b", "type_a", "type_b"),
        )

    def test_suite_summary_uses_macro_average(self) -> None:
        code_cells = _load_code_cells()
        namespace = dict(self.namespace)
        exec(code_cells["cell-task"], namespace)
        rows = [
            {"analysis": {"suite_task_id": "explicit_rule_update", "shift_mode": "explicit_instruction", "difficulty_bin": "hard"}},
            {"analysis": {"suite_task_id": "latent_rule_update", "shift_mode": "latent_example_change", "difficulty_bin": "hard"}},
            {"analysis": {"suite_task_id": "context_binding", "shift_mode": "context_gate", "difficulty_bin": "medium"}},
            {"analysis": {"suite_task_id": "trial_cued_switch", "shift_mode": "cue_switching", "difficulty_bin": "medium"}},
        ]
        runs = FakeRuns(
            [
                {"numerator": 8, "denominator": 8, "predictions": ["type_a"] * 8},
                {"numerator": 4, "denominator": 8, "predictions": ["type_a"] * 8},
                {"numerator": 8, "denominator": 8, "predictions": ["type_a"] * 8},
                {"numerator": 0, "denominator": 8, "predictions": ["type_a"] * 8},
            ]
        )
        summary = namespace["summarize_suite_benchmark"](runs, rows)
        self.assertAlmostEqual(summary["micro_accuracy"], 0.625)
        self.assertAlmostEqual(summary["macro_accuracy"], 0.625)
        self.assertEqual(
            set(summary["per_task_accuracy"]),
            {"explicit_rule_update", "latent_rule_update", "context_binding", "trial_cued_switch"},
        )
