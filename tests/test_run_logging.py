from __future__ import annotations

import json

from core.kaggle import (
    BENCHMARK_LOG_FILENAME,
    EXCEPTIONS_LOG_FILENAME,
    BenchmarkRunLogger,
    ExceptionSummary,
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


def test_log_exception_writes_full_record_to_exceptions_file(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        llm=_LLMIdentityStub(),
        run_id="run-exc-001",
        output_dir=tmp_path / "exc-run",
    )
    logger = BenchmarkRunLogger(context)

    try:
        raise ValueError("something went wrong")
    except ValueError as exc:
        logger.log_exception(
            exc,
            phase="official_binary_evaluation",
            task_mode="binary",
            episode_id="ep-abc",
        )

    exc_path = tmp_path / "exc-run" / EXCEPTIONS_LOG_FILENAME
    assert exc_path.is_file()

    records = [json.loads(line) for line in exc_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    record = records[0]

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
        "exception_type",
        "exception_message",
        "traceback",
    }
    assert required_fields.issubset(record)
    assert record["run_id"] == "run-exc-001"
    assert record["provider"] == "shim-provider"
    assert record["model"] == "shim-model"
    assert record["phase"] == "official_binary_evaluation"
    assert record["event"] == "exception"
    assert record["level"] == "error"
    assert record["status"] == "exception"
    assert record["episode_id"] == "ep-abc"
    assert record["task_mode"] == "binary"
    assert record["exception_type"] == "ValueError"
    assert record["exception_message"] == "something went wrong"
    assert "ValueError" in record["traceback"]
    assert "something went wrong" in record["traceback"]


def test_log_exception_writes_compact_summary_to_benchmark_log(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-exc-002",
        output_dir=tmp_path / "exc-run-2",
    )
    logger = BenchmarkRunLogger(context)

    try:
        raise RuntimeError("provider timeout")
    except RuntimeError as exc:
        logger.log_exception(
            exc,
            phase="official_narrative_evaluation",
            task_mode="narrative",
        )

    log_path = tmp_path / "exc-run-2" / BENCHMARK_LOG_FILENAME
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "exception"
    assert record["exception_type"] == "RuntimeError"
    assert record["exception_message"] == "provider timeout"
    assert "traceback" not in record


def test_log_exception_traceback_includes_call_site(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-exc-003",
        output_dir=tmp_path / "exc-run-3",
    )
    logger = BenchmarkRunLogger(context)

    try:
        raise ZeroDivisionError("division by zero")
    except ZeroDivisionError as exc:
        logger.log_exception(exc, phase="bootstrap", task_mode="notebook")

    exc_path = tmp_path / "exc-run-3" / EXCEPTIONS_LOG_FILENAME
    record = json.loads(exc_path.read_text(encoding="utf-8").splitlines()[0])
    assert "ZeroDivisionError" in record["traceback"]
    assert record["exception_type"] == "ZeroDivisionError"


def test_log_exception_episode_id_none_is_valid(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-exc-004",
        output_dir=tmp_path / "exc-run-4",
    )
    logger = BenchmarkRunLogger(context)

    try:
        raise KeyError("missing key")
    except KeyError as exc:
        logger.log_exception(exc, phase="bootstrap", task_mode="notebook", episode_id=None)

    exc_path = tmp_path / "exc-run-4" / EXCEPTIONS_LOG_FILENAME
    record = json.loads(exc_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["episode_id"] is None
    assert record["exception_type"] == "KeyError"


def test_log_exception_file_remains_readable_after_multiple_writes(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-exc-005",
        output_dir=tmp_path / "exc-run-5",
    )
    logger = BenchmarkRunLogger(context)

    exceptions = [ValueError("first"), RuntimeError("second"), OSError("third")]
    for exc in exceptions:
        try:
            raise exc
        except Exception as e:
            logger.log_exception(e, phase="run", task_mode="notebook")

    exc_path = tmp_path / "exc-run-5" / EXCEPTIONS_LOG_FILENAME
    lines = exc_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    for line in lines:
        record = json.loads(line)
        assert "exception_type" in record
        assert "traceback" in record


def test_summarize_exceptions_clean_run(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        run_id="run-sum-001",
        output_dir=tmp_path / "sum-run-1",
    )
    logger = BenchmarkRunLogger(context)

    summary = logger.summarize_exceptions()

    assert isinstance(summary, ExceptionSummary)
    assert summary.total == 0
    assert summary.by_phase == {}

    log_path = tmp_path / "sum-run-1" / BENCHMARK_LOG_FILENAME
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "exception_summary"
    assert record["level"] == "info"
    assert record["status"] == "clean"
    assert record["total_exceptions"] == 0
    assert record["by_phase"] == {}


def test_summarize_exceptions_counts_by_phase(tmp_path):
    context = build_run_context(
        repo_root=tmp_path,
        llm=_LLMIdentityStub(),
        run_id="run-sum-002",
        output_dir=tmp_path / "sum-run-2",
    )
    logger = BenchmarkRunLogger(context)

    for phase, exc in [
        ("official_binary_evaluation", ValueError("bad response")),
        ("official_binary_evaluation", RuntimeError("timeout")),
        ("official_narrative_evaluation", OSError("connection lost")),
    ]:
        try:
            raise exc
        except Exception as e:
            logger.log_exception(e, phase=phase, task_mode="binary")

    summary = logger.summarize_exceptions()

    assert summary.total == 3
    assert summary.by_phase == {
        "official_binary_evaluation": 2,
        "official_narrative_evaluation": 1,
    }

    log_path = tmp_path / "sum-run-2" / BENCHMARK_LOG_FILENAME
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    summary_record = [r for r in records if r["event"] == "exception_summary"][0]
    assert summary_record["level"] == "warning"
    assert summary_record["status"] == "exceptions_found"
    assert summary_record["total_exceptions"] == 3
    assert summary_record["by_phase"]["official_binary_evaluation"] == 2
