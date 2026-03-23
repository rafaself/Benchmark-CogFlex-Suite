from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

__all__ = [
    "CANONICAL_RUN_METADATA_SCHEMA_VERSION",
    "CanonicalRunWriteResult",
    "build_timestamped_snapshot_path",
    "build_timestamped_sample_path",
    "build_latest_report_path",
    "current_report_timestamp",
    "metadata_path_for_report",
    "write_canonical_run_outputs",
    "write_json_with_timestamped_snapshot",
    "write_text_with_timestamped_snapshot",
]

_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
_LATEST_DIRNAME = "latest"
_HISTORY_DIRNAME = "history"
_SAMPLES_DIRNAME = "samples"
CANONICAL_RUN_METADATA_SCHEMA_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class CanonicalRunWriteResult:
    report_path: Path
    artifact_path: Path
    metadata_path: Path
    sample_path: Path
    snapshot_report_path: Path
    snapshot_artifact_path: Path
    snapshot_metadata_path: Path


def current_report_timestamp() -> str:
    return datetime.now().astimezone().strftime(_TIMESTAMP_FORMAT)


def build_latest_report_path(*segments: str, filename: str) -> Path:
    return _reports_root().joinpath(*segments, _LATEST_DIRNAME, filename)


def build_timestamped_snapshot_path(path: Path, *, timestamp: str) -> Path:
    history_dir = _snapshot_directory_for(path)
    snapshot_path = history_dir / f"{path.stem}__{timestamp}{path.suffix}"
    if not snapshot_path.exists():
        return snapshot_path

    counter = 1
    while True:
        candidate = history_dir / (
            f"{path.stem}__{timestamp}_{counter:02d}{path.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def build_timestamped_sample_path(
    path: Path,
    *,
    stem: str,
    suffix: str,
    timestamp: str,
) -> Path:
    samples_dir = _samples_directory_for(path)
    sample_path = samples_dir / f"{stem}__{timestamp}{suffix}"
    if not sample_path.exists():
        return sample_path

    counter = 1
    while True:
        candidate = samples_dir / f"{stem}__{timestamp}_{counter:02d}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def metadata_path_for_report(report_path: Path) -> Path:
    if report_path.name == "report.md" and report_path.parent.name == _LATEST_DIRNAME:
        return report_path.with_name("metadata.json")
    return report_path.with_name(f"{report_path.stem}.metadata.json")


def write_text_with_timestamped_snapshot(
    path: Path,
    text: str,
    *,
    timestamp: str | None = None,
) -> tuple[Path, Path]:
    resolved_timestamp = current_report_timestamp() if timestamp is None else timestamp
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    snapshot_path = build_timestamped_snapshot_path(path, timestamp=resolved_timestamp)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(text, encoding="utf-8")
    return path, snapshot_path


def write_json_with_timestamped_snapshot(
    path: Path,
    payload: str,
    *,
    timestamp: str | None = None,
) -> tuple[Path, Path]:
    return write_text_with_timestamped_snapshot(
        path,
        payload,
        timestamp=timestamp,
    )


def write_canonical_run_outputs(
    *,
    report_path: Path,
    report_markdown: str,
    artifact_payload: dict[str, object],
    raw_capture_payload: dict[str, object],
    metadata_payload: dict[str, object],
    timestamp: str | None = None,
    sample_stem: str = "raw_capture",
) -> CanonicalRunWriteResult:
    resolved_timestamp = current_report_timestamp() if timestamp is None else timestamp
    artifact_path = _artifact_path_for_report(report_path)
    metadata_path = metadata_path_for_report(report_path)
    sample_path = build_timestamped_sample_path(
        report_path,
        stem=sample_stem,
        suffix=".json",
        timestamp=resolved_timestamp,
    )
    _validate_metadata_payload(metadata_payload)

    _, snapshot_report_path = write_text_with_timestamped_snapshot(
        report_path,
        report_markdown,
        timestamp=resolved_timestamp,
    )
    _, snapshot_artifact_path = write_json_with_timestamped_snapshot(
        artifact_path,
        _serialize_json_payload(artifact_payload),
        timestamp=resolved_timestamp,
    )
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(
        _serialize_json_payload(raw_capture_payload),
        encoding="utf-8",
    )

    storage_payload = {
        "report": _build_storage_record(report_path, snapshot_report_path),
        "artifact": _build_storage_record(artifact_path, snapshot_artifact_path),
        "sample": _build_storage_record(sample_path, None),
    }
    metadata_payload = dict(metadata_payload)
    metadata_payload["storage"] = storage_payload
    _, snapshot_metadata_path = write_json_with_timestamped_snapshot(
        metadata_path,
        _serialize_json_payload(metadata_payload),
        timestamp=resolved_timestamp,
    )

    return CanonicalRunWriteResult(
        report_path=report_path,
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        sample_path=sample_path,
        snapshot_report_path=snapshot_report_path,
        snapshot_artifact_path=snapshot_artifact_path,
        snapshot_metadata_path=snapshot_metadata_path,
    )


def _snapshot_directory_for(path: Path) -> Path:
    if path.parent.name == _LATEST_DIRNAME:
        return path.parent.parent / _HISTORY_DIRNAME
    return path.parent


def _samples_directory_for(path: Path) -> Path:
    if path.parent.name == _LATEST_DIRNAME:
        return path.parent.parent / _SAMPLES_DIRNAME
    return path.parent / _SAMPLES_DIRNAME


def _reports_root() -> Path:
    return Path(__file__).resolve().parents[2] / "reports"


def _artifact_path_for_report(report_path: Path) -> Path:
    if report_path.name == "report.md" and report_path.parent.name == _LATEST_DIRNAME:
        return report_path.with_name("artifact.json")
    return report_path.with_suffix(".json")


def _validate_metadata_payload(metadata_payload: dict[str, object]) -> None:
    if metadata_payload.get("run_metadata_schema_version") != (
        CANONICAL_RUN_METADATA_SCHEMA_VERSION
    ):
        raise ValueError("canonical run metadata must declare the current schema version")


def _serialize_json_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def _build_storage_record(
    latest_path: Path,
    snapshot_path: Path | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "latest": {
            "path": _relative_to_repo_root(latest_path),
            "sha256": _sha256_for_path(latest_path),
        }
    }
    if snapshot_path is not None:
        record["history"] = {
            "path": _relative_to_repo_root(snapshot_path),
            "sha256": _sha256_for_path(snapshot_path),
        }
    return record


def _relative_to_repo_root(path: Path) -> str:
    resolved_path = path.resolve()
    try:
        return str(resolved_path.relative_to(_repo_root()))
    except ValueError:
        return str(resolved_path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256_for_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
