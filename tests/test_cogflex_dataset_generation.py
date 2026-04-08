import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.build_cogflex_dataset import (
    NOTEBOOK_ID,
    PUBLIC_DATASET_ID,
    PUBLIC_QUALITY_REPORT_PATH,
    PUBLIC_ROWS_PATH,
    SUITE_TASKS,
    TASK_NAME,
    attack_limits_for_task,
    build_public_artifacts,
    dataset_metadata,
    episode_signature,
)


ROOT = Path(__file__).resolve().parents[1]
KERNEL_METADATA_PATH = ROOT / "kaggle/notebook/kernel-metadata.json"
MAKEFILE_PATH = ROOT / "Makefile"
README_PATH = ROOT / "README.md"


class CogflexDatasetGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated_rows, cls.generated_answers, cls.generated_report = build_public_artifacts()
        cls.tracked_rows = json.loads(PUBLIC_ROWS_PATH.read_text(encoding="utf-8"))
        cls.tracked_report = json.loads(PUBLIC_QUALITY_REPORT_PATH.read_text(encoding="utf-8"))

    def test_generated_public_split_matches_tracked_public_rows(self) -> None:
        self.assertEqual(self.generated_rows, self.tracked_rows)

    def test_generated_public_quality_report_matches_tracked_report(self) -> None:
        self.assertEqual(self.generated_report, self.tracked_report)

    def test_generated_public_split_has_expected_suite_shape(self) -> None:
        row = self.generated_rows[0]
        self.assertEqual(len(row["inference"]["turns"]), 3)
        self.assertEqual(len(row["scoring"]["final_probe_targets"]), 8)
        self.assertEqual(
            sorted(row["analysis"]),
            ["difficulty_bin", "faculty_id", "shift_mode", "suite_task_id"],
        )
        self.assertIn("shape=", row["inference"]["turns"][0])
        self.assertIn("tone=", row["inference"]["turns"][0])

    def test_generated_public_split_has_expected_counts(self) -> None:
        self.assertEqual(len(self.generated_rows), 120)
        task_counts = Counter(row["analysis"]["suite_task_id"] for row in self.generated_rows)
        self.assertEqual(task_counts, Counter({suite_task_id: 30 for suite_task_id in SUITE_TASKS}))
        difficulty_counts = Counter(row["analysis"]["difficulty_bin"] for row in self.generated_rows)
        self.assertEqual(difficulty_counts, Counter({"hard": 60, "medium": 60}))

    def test_generated_public_split_has_no_semantic_duplicates(self) -> None:
        signatures = {episode_signature(answer) for answer in self.generated_answers}
        self.assertEqual(len(signatures), len(self.generated_answers))

    def test_public_report_tracks_transition_family_and_disagreement_coverage(self) -> None:
        self.assertEqual(self.generated_report["transition_family_count"], 15)
        self.assertGreaterEqual(len(self.generated_report["disagreement_bin_counts"]), 2)
        usage_counts = Counter(self.generated_report["transition_family_usage"].values())
        self.assertEqual(usage_counts, Counter({8: 15}))

    def test_generated_public_answers_respect_attack_limits(self) -> None:
        for answer in self.generated_answers:
            limits = attack_limits_for_task(answer["suite_task_id"])
            diagnostics = answer["generator_diagnostics"]
            for metric, ceiling in limits.items():
                value = diagnostics.get(metric)
                if value is None:
                    continue
                self.assertLessEqual(float(value), ceiling, (answer["episode_id"], metric, value, ceiling))

    def test_public_dataset_metadata_payload_matches_expected_id(self) -> None:
        self.assertEqual(
            dataset_metadata(PUBLIC_DATASET_ID, "CogFlex Suite Runtime"),
            {
                "id": "raptorengineer/cogflex-suite-runtime",
                "title": "CogFlex Suite Runtime",
                "licenses": [{"name": "CC0-1.0"}],
            },
        )

    def test_makefile_and_kernel_metadata_point_to_cogflex_assets(self) -> None:
        makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
        self.assertIn(".venv/bin/python -m scripts.verify_cogflex --split public", makefile)
        self.assertIn(".venv/bin/python -m scripts.verify_cogflex --split private", makefile)
        self.assertIn("cogflex_notebook_task.ipynb", makefile)
        metadata = json.loads(KERNEL_METADATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metadata["id"], NOTEBOOK_ID)
        self.assertEqual(metadata["code_file"], "cogflex_notebook_task.ipynb")

    def test_readme_references_new_generator_and_private_bundle_contract(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn(TASK_NAME, readme)
        self.assertIn("build_cogflex_dataset.py", readme)
        self.assertIn("verify_cogflex.py", readme)
        self.assertIn("COGFLEX_PRIVATE_BUNDLE_DIR", readme)
        self.assertNotIn("rule" + "shift", readme.lower())
