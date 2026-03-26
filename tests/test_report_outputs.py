from __future__ import annotations

from pathlib import Path

from core.report_outputs import (
    build_timestamped_snapshot_path,
    write_json_with_timestamped_snapshot,
    write_text_with_timestamped_snapshot,
)


def test_snapshot_for_latest_path_is_written_to_history_directory(tmp_path: Path):
    report_path = tmp_path / "reports" / "integrity" / "latest" / "report.json"

    canonical_path, snapshot_path = write_text_with_timestamped_snapshot(
        report_path,
        "{}\n",
        timestamp="20260322_210000",
    )

    assert canonical_path == report_path
    assert snapshot_path == (
        tmp_path
        / "reports"
        / "integrity"
        / "history"
        / "report__20260322_210000.json"
    )
    assert snapshot_path.read_text(encoding="utf-8") == "{}\n"


def test_snapshot_for_non_latest_path_stays_beside_canonical_file(tmp_path: Path):
    output_path = tmp_path / "integrity.json"

    snapshot_path = build_timestamped_snapshot_path(
        output_path,
        timestamp="20260322_210500",
    )

    assert snapshot_path == tmp_path / "integrity__20260322_210500.json"


def test_write_json_with_timestamped_snapshot_writes_canonical_and_history_files(
    tmp_path: Path,
):
    output_path = tmp_path / "integrity" / "latest" / "payload.json"

    canonical_path, snapshot_path = write_json_with_timestamped_snapshot(
        output_path,
        '{\n  "passed": true\n}\n',
        timestamp="20260323_120000",
    )

    assert canonical_path.read_text(encoding="utf-8") == '{\n  "passed": true\n}\n'
    assert snapshot_path == (
        tmp_path
        / "integrity"
        / "history"
        / "payload__20260323_120000.json"
    )
