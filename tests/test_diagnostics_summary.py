from __future__ import annotations

import json

from core.kaggle import (
    DIAGNOSTICS_SUMMARY_FILENAME,
    BenchmarkRunLogger,
    EpisodeResultLedgerWriter,
    build_run_context,
    write_diagnostics_summary,
)


def test_write_diagnostics_summary_creates_compact_run_health_artifact(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-diag-001",
        output_dir=tmp_path / "diag-run",
    )
    logger = BenchmarkRunLogger(context)
    ledger = EpisodeResultLedgerWriter(context)

    logger.log_run_started(output_dir=str(context.output_dir))
    logger.log_provider_call_failed(
        phase="official_binary_evaluation",
        task_mode="binary",
        episode_id="ep-001",
        failure_stage="provider_call",
        detail="provider timeout",
    )
    logger.log_response_parse_failed(
        phase="official_binary_evaluation",
        task_mode="binary",
        episode_id="ep-001",
        status="operational_failure",
        level="error",
        parse_status="operational_failure",
        failure_stage="provider_call",
    )
    logger.log_response_parse_failed(
        phase="official_narrative_evaluation",
        task_mode="narrative",
        episode_id="ep-002",
        status="invalid_format",
        parse_status="invalid_format",
    )

    try:
        raise RuntimeError("provider timeout")
    except RuntimeError as exc:
        logger.log_exception(
            exc,
            phase="official_binary_evaluation",
            task_mode="binary",
            episode_id="ep-001",
            failure_stage="provider_call",
        )

    logger.log_run_invalidated(
        phase="official_binary_evaluation",
        reason="official_binary_evaluation_failed",
        detail="Binary evaluation failed",
    )
    ledger.write_record(
        episode_id="ep-001",
        split="public_leaderboard",
        task_mode="binary",
        call_status="failed",
        parse_status="operational_failure",
        outcome_kind="operational_failure",
        failure_category="provider_failure",
        latency_ms=8,
        prediction=None,
        target=["attract", "repel", "attract", "repel"],
        score={"num_correct": 0, "total": 4},
        exception_ref="exceptions.jsonl#2026-03-29T12:00:00Z",
    )
    ledger.write_record(
        episode_id="ep-002",
        split="public_leaderboard",
        task_mode="narrative",
        call_status="completed",
        parse_status="invalid_format",
        outcome_kind="model_parse_failure",
        failure_category="narrative_parse_failure",
        latency_ms=6,
        prediction=None,
        target=["attract", "repel", "attract", "repel"],
        score={"num_correct": 0, "total": 4},
        exception_ref=None,
    )
    logger.log_run_finished(output_dir=str(context.output_dir), total_exceptions=1)

    summary_path = write_diagnostics_summary(
        context=context,
        binary_parse_valid_rate=0.5,
        narrative_schema_valid_rate=0.75,
    )

    assert summary_path == context.output_dir / DIAGNOSTICS_SUMMARY_FILENAME
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary == {
        "run_id": "run-diag-001",
        "run_valid": False,
        "invalidation_reasons": ["official_binary_evaluation_failed"],
        "binary_parse_valid_rate": 0.5,
        "narrative_schema_valid_rate": 0.75,
        "provider_failure_count": 1,
        "failure_category_counts": {
            "provider_failure": 1,
            "narrative_parse_failure": 1,
        },
        "total_exception_count": 1,
        "total_logged_events": 7,
        "started_at": summary["started_at"],
        "finished_at": summary["finished_at"],
    }
    assert isinstance(summary["started_at"], str) and summary["started_at"]
    assert isinstance(summary["finished_at"], str) and summary["finished_at"]
