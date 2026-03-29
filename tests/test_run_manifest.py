from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.kaggle import (
    RUN_MANIFEST_FILENAME,
    BenchmarkRunLogger,
    build_run_context,
    write_run_manifest,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_write_run_manifest_creates_compact_provenance_artifact(tmp_path):
    context = build_run_context(
        repo_root=_REPO_ROOT,
        run_id="run-manifest-001",
        output_dir=tmp_path / "manifest-run",
    )
    logger = BenchmarkRunLogger(context)
    logger.log_run_started(output_dir=str(context.output_dir))
    logger.log_run_finished(output_dir=str(context.output_dir), total_exceptions=0)

    manifest_path = write_run_manifest(context=context, repo_root=_REPO_ROOT)

    assert manifest_path == context.output_dir / RUN_MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    notebook_path = _REPO_ROOT / "packaging" / "kaggle" / "ruleshift_notebook_task.ipynb"
    expected_hash = hashlib.sha256(notebook_path.read_bytes()).hexdigest()

    assert manifest["run_id"] == "run-manifest-001"
    assert manifest["git_commit"]
    assert manifest["benchmark_version"] == "R14"
    assert manifest["parser_version"] == "v2"
    assert manifest["metrics_version"] == "v1"
    assert manifest["notebook_bundle_hash"] == expected_hash
    assert manifest["runtime_dataset_id"] == "raptorengineer/ruleshift-runtime"
    assert manifest["runtime_dataset_version"] is None
    assert manifest["provider"] == "unknown"
    assert manifest["model"] == "unknown"
    assert isinstance(manifest["started_at"], str) and manifest["started_at"]
    assert isinstance(manifest["finished_at"], str) and manifest["finished_at"]
