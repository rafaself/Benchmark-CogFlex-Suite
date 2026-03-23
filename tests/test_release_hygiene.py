from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_README_PATH = _REPO_ROOT / "README.md"
_CANONICAL_M1_REPORT_PATH = (
    _REPO_ROOT
    / "reports"
    / "live"
    / "gemini-first-panel"
    / "binary-vs-narrative"
    / "latest"
    / "report.md"
)
_CANONICAL_M1_ARTIFACT_PATH = (
    _REPO_ROOT
    / "reports"
    / "live"
    / "gemini-first-panel"
    / "binary-vs-narrative"
    / "latest"
    / "artifact.json"
)
_M1_ALIAS_REPORT_PATH = (
    _REPO_ROOT / "reports" / "m1_binary_vs_narrative_robustness_report.md"
)
_M1_ALIAS_ARTIFACT_PATH = (
    _REPO_ROOT / "reports" / "m1_binary_vs_narrative_robustness_report.json"
)


def test_readme_does_not_report_stale_m3_status():
    text = _README_PATH.read_text(encoding="utf-8")

    assert "- **M3**: Not started." not in text


def test_committed_m1_aliases_match_canonical_latest_surfaces():
    assert _M1_ALIAS_REPORT_PATH.read_text(encoding="utf-8") == (
        _CANONICAL_M1_REPORT_PATH.read_text(encoding="utf-8")
    )
    assert _M1_ALIAS_ARTIFACT_PATH.read_text(encoding="utf-8") == (
        _CANONICAL_M1_ARTIFACT_PATH.read_text(encoding="utf-8")
    )


def test_committed_m1_artifact_uses_current_diagnostic_schema():
    payload = json.loads(_CANONICAL_M1_ARTIFACT_PATH.read_text(encoding="utf-8"))

    assert payload["artifact_schema_version"] == "v1.1"
    assert "execution_summary" in payload
    assert "diagnostic_summary" in payload
    assert "diagnostic_episode_rows" in payload
    assert payload["prompt_modes"] == ["binary", "narrative"]

    first_mode_payload = payload["splits"][0]["rows"][0]["modes"]["binary"]
    assert "response_text" not in first_mode_payload
    assert "error_message" not in first_mode_payload


def test_committed_m1_report_exposes_current_diagnostic_sections():
    text = _CANONICAL_M1_REPORT_PATH.read_text(encoding="utf-8")

    assert "Binary-only headline metric" in text
    assert "## Execution Provenance (diagnostic-only)" in text
    assert "## Failure Decomposition (diagnostic-only)" in text
    assert "## Direct Disagreement Diagnostics (diagnostic-only)" in text
    assert "## Diagnostic Failure Slices (diagnostic-only)" in text
