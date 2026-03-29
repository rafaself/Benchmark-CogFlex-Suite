from __future__ import annotations

import json
import os
import traceback as _tb
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "BENCHMARK_LOG_FILENAME",
    "EXCEPTIONS_LOG_FILENAME",
    "RUN_ID_ENV_VAR",
    "RUN_OUTPUT_DIR_ENV_VAR",
    "BenchmarkRunContext",
    "BenchmarkRunLogger",
    "ExceptionSummary",
    "build_run_context",
]

BENCHMARK_LOG_FILENAME = "benchmark_log.jsonl"
EXCEPTIONS_LOG_FILENAME = "exceptions.jsonl"
RUN_ID_ENV_VAR = "RULESHIFT_RUN_ID"
RUN_OUTPUT_DIR_ENV_VAR = "RULESHIFT_RUN_OUTPUT_DIR"


@dataclass(frozen=True, slots=True)
class BenchmarkRunContext:
    run_id: str
    output_dir: Path
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class ExceptionSummary:
    total: int
    by_phase: dict[str, int]


def build_run_context(
    *,
    repo_root: Path | str | None = None,
    llm: object | None = None,
    run_id: str | None = None,
    output_dir: Path | str | None = None,
) -> BenchmarkRunContext:
    resolved_run_id = _resolve_run_id(run_id)
    resolved_output_dir = _resolve_output_dir(
        repo_root=repo_root,
        run_id=resolved_run_id,
        output_dir=output_dir,
    )
    provider, model = _resolve_provider_model(llm)
    return BenchmarkRunContext(
        run_id=resolved_run_id,
        output_dir=resolved_output_dir,
        provider=provider,
        model=model,
    )


class BenchmarkRunLogger:
    def __init__(self, context: BenchmarkRunContext) -> None:
        self.context = context
        self.context.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.context.output_dir / BENCHMARK_LOG_FILENAME
        self.exceptions_path = self.context.output_dir / EXCEPTIONS_LOG_FILENAME

    def log(
        self,
        *,
        phase: str,
        event: str,
        level: str,
        status: str,
        task_mode: str,
        episode_id: str | None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "timestamp": _timestamp_utc(),
            "run_id": self.context.run_id,
            "phase": phase,
            "event": event,
            "level": level,
            "episode_id": episode_id,
            "task_mode": task_mode,
            "provider": self.context.provider,
            "model": self.context.model,
            "status": status,
        }
        record.update(extra_fields)
        serialized = json.dumps(record, ensure_ascii=True, sort_keys=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def log_exception(
        self,
        exc: BaseException,
        *,
        phase: str,
        task_mode: str,
        episode_id: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        tb_text = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))
        full_record: dict[str, Any] = {
            "timestamp": _timestamp_utc(),
            "run_id": self.context.run_id,
            "phase": phase,
            "event": "exception",
            "level": "error",
            "episode_id": episode_id,
            "task_mode": task_mode,
            "provider": self.context.provider,
            "model": self.context.model,
            "status": "exception",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": tb_text,
        }
        full_record.update(extra_fields)
        serialized = json.dumps(full_record, ensure_ascii=True, sort_keys=True)
        with self.exceptions_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.log(
            phase=phase,
            event="exception",
            level="error",
            status="exception",
            task_mode=task_mode,
            episode_id=episode_id,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
        )
        return full_record

    def summarize_exceptions(self) -> ExceptionSummary:
        """Read exceptions.jsonl, count by phase, and emit a summary event."""
        by_phase: dict[str, int] = {}
        total = 0
        if self.exceptions_path.exists():
            for line in self.exceptions_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    phase_key = "_unparseable"
                else:
                    phase_key = record.get("phase", "_unknown")
                by_phase[phase_key] = by_phase.get(phase_key, 0) + 1
                total += 1
        self.log(
            phase="run",
            event="exception_summary",
            level="warning" if total > 0 else "info",
            status="exceptions_found" if total > 0 else "clean",
            task_mode="notebook",
            episode_id=None,
            total_exceptions=total,
            by_phase=by_phase,
        )
        return ExceptionSummary(total=total, by_phase=by_phase)


def _resolve_run_id(run_id: str | None) -> str:
    if run_id is not None and run_id.strip():
        return run_id.strip()
    env_run_id = os.getenv(RUN_ID_ENV_VAR, "").strip()
    if env_run_id:
        return env_run_id
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ruleshift-{timestamp}-{uuid.uuid4().hex[:8]}"


def _resolve_output_dir(
    *,
    repo_root: Path | str | None,
    run_id: str,
    output_dir: Path | str | None,
) -> Path:
    if output_dir is not None:
        return Path(output_dir).resolve()

    env_output_dir = os.getenv(RUN_OUTPUT_DIR_ENV_VAR, "").strip()
    if env_output_dir:
        return Path(env_output_dir).resolve()

    kaggle_working_dir = Path("/kaggle/working")
    if kaggle_working_dir.exists():
        return kaggle_working_dir / run_id

    if repo_root is None:
        repo_root = Path.cwd()

    return Path(repo_root).resolve() / "reports" / "local" / run_id


def _resolve_provider_model(llm: object | None) -> tuple[str, str]:
    provider = _resolve_identity_field(
        llm,
        "provider",
        "provider_name",
        env_var="RULESHIFT_PROVIDER",
    )
    model = _resolve_identity_field(
        llm,
        "model",
        "model_name",
        env_var="RULESHIFT_MODEL",
    )
    return provider, model


def _resolve_identity_field(
    llm: object | None,
    *attribute_names: str,
    env_var: str,
) -> str:
    for attribute_name in attribute_names:
        try:
            value = getattr(llm, attribute_name)
        except Exception:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()

    env_value = os.getenv(env_var, "").strip()
    if env_value:
        return env_value

    return "unknown"


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )
