import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cogflex_fixtures import write_private_bundle
from scripts.verify_cogflex import (
    attach_private_scoring,
    load_private_answer_key,
    verify_manifest,
    verify_private_answer_key,
    verify_private_bundle,
    verify_public_split,
    verify_quality_report,
)


class CogflexVerificationTests(unittest.TestCase):
    def test_verify_public_reports_attack_suite_summary(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            verify_public_split()
        payload = json.loads(stdout.getvalue())
        self.assertIn("attack_suite", payload)
        self.assertIn("transition_family_count", payload)
        self.assertIn("suite_task_counts", payload)

    def test_attach_private_scoring_accepts_inference_only_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_paths = write_private_bundle(Path(tmpdir) / "bundle")
            private_rows = json.loads(bundle_paths["rows"].read_text(encoding="utf-8"))
            answer_key = load_private_answer_key(bundle_paths["answer_key"])
            attached = attach_private_scoring(private_rows[:3], {
                **answer_key,
                "episodes": answer_key["episodes"][:3],
            })
        self.assertEqual(len(attached), 3)
        self.assertIn("scoring", attached[0])
        self.assertEqual(len(attached[0]["scoring"]["final_probe_targets"]), 8)

    def test_verify_private_bundle_accepts_valid_external_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, contextlib.redirect_stdout(io.StringIO()):
            bundle_dir = Path(tmpdir) / "bundle"
            write_private_bundle(bundle_dir)
            verify_private_bundle(bundle_dir)

    def test_verify_private_bundle_rejects_missing_quality_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            bundle_paths["quality"].unlink()
            with self.assertRaisesRegex(RuntimeError, "missing required files"):
                verify_private_bundle(bundle_dir)

    def test_verify_private_answer_key_rejects_analysis_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            private_rows = json.loads(bundle_paths["rows"].read_text(encoding="utf-8"))
            answer_key = load_private_answer_key(bundle_paths["answer_key"])
            answer_key["episodes"][0]["difficulty_bin"] = "mismatch"
            with self.assertRaisesRegex(RuntimeError, "difficulty_bin mismatch"):
                verify_private_answer_key(answer_key, private_rows)

    def test_verify_manifest_rejects_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            payload = json.loads(bundle_paths["manifest"].read_text(encoding="utf-8"))
            payload["sha256"]["private_leaderboard_rows.json"] = "0" * 64
            bundle_paths["manifest"].write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
                verify_manifest(bundle_paths["manifest"], bundle_paths)

    def test_verify_quality_report_requires_three_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_paths = write_private_bundle(bundle_dir)
            payload = json.loads(bundle_paths["quality"].read_text(encoding="utf-8"))
            payload["calibration_summary"]["models"] = payload["calibration_summary"]["models"][:2]
            bundle_paths["quality"].write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "exactly 3 models"):
                verify_quality_report(bundle_paths["quality"])
