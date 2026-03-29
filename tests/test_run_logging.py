from __future__ import annotations

import json

from core.kaggle import (
    BENCHMARK_LOG_FILENAME,
    BenchmarkRunLogger,
    build_run_context,
)


class _LLMIdentityStub:
    provider_name = "shim-provider"
    model_name = "shim-model"


def test_benchmark_run_logger_appends_valid_json_lines(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        llm=_LLMIdentityStub(),
        run_id="run-123",
        output_dir=tmp_path / "run-output",
    )
    logger = BenchmarkRunLogger(context)

    logger.log(
        phase="run",
        event="startup",
        level="info",
        status="started",
        task_mode="notebook",
        episode_id=None,
    )
    logger.log(
        phase="official_binary_evaluation",
        event="episode_scored",
        level="warning",
        status="skipped_provider_failure",
        task_mode="binary",
        episode_id="ep-001",
        num_correct=0,
        total=4,
    )

    log_path = tmp_path / "run-output" / BENCHMARK_LOG_FILENAME
    assert log_path.is_file()

    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2

    required_fields = {
        "timestamp",
        "run_id",
        "phase",
        "event",
        "level",
        "episode_id",
        "task_mode",
        "provider",
        "model",
        "status",
    }
    for record in records:
        assert required_fields.issubset(record)
        assert record["run_id"] == "run-123"
        assert record["provider"] == "shim-provider"
        assert record["model"] == "shim-model"

    assert records[0]["event"] == "startup"
    assert records[1]["episode_id"] == "ep-001"
    assert records[1]["num_correct"] == 0
    assert records[1]["total"] == 4


def test_benchmark_run_logger_flushes_single_event_without_close(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-456",
        output_dir=tmp_path / "partial-run",
    )
    logger = BenchmarkRunLogger(context)

    logger.log(
        phase="run",
        event="startup",
        level="info",
        status="started",
        task_mode="notebook",
        episode_id=None,
    )

    log_path = tmp_path / "partial-run" / BENCHMARK_LOG_FILENAME
    line = log_path.read_text(encoding="utf-8").splitlines()[0]
    record = json.loads(line)

    assert record["run_id"] == "run-456"
    assert record["event"] == "startup"
    assert record["status"] == "started"


def test_build_run_context_defaults_unknown_identity(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-789",
        output_dir=tmp_path / "identity-run",
    )

    assert context.provider == "unknown"
    assert context.model == "unknown"
    assert context.output_dir == (tmp_path / "identity-run").resolve()
