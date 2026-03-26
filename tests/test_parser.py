import json

from parser import (
    NarrativeAuditOutput,
    NarrativeParseStatus,
    NarrativeParsedResult,
    ParsedPrediction,
    ParseStatus,
    parse_binary_output,
    parse_narrative_audit_output,
)
from protocol import InteractionLabel

ATTRACT = InteractionLabel.ATTRACT
REPEL = InteractionLabel.REPEL


# ---------------------------------------------------------------------------
# Binary parser tests
# ---------------------------------------------------------------------------


def test_binary_output_parses_exactly_four_labels_in_order():
    parsed = parse_binary_output("attract, repel, repel, attract")

    assert parsed == ParsedPrediction(
        labels=(ATTRACT, REPEL, REPEL, ATTRACT),
        status=ParseStatus.VALID,
    )


def test_safe_formatting_variants_normalize_to_canonical_labels():
    expected = ParsedPrediction(
        labels=(ATTRACT, REPEL, REPEL, ATTRACT),
        status=ParseStatus.VALID,
    )

    assert parse_binary_output("  ATTRACT, repel,\nREPEL,\nattract  ") == expected
    assert parse_binary_output("\nattract\nrepel\nrepel\nattract\n") == expected


def test_malformed_binary_outputs_are_rejected():
    invalid = ParsedPrediction(labels=(), status=ParseStatus.INVALID)

    assert parse_binary_output("attract, repel, repels, attract") == invalid
    assert parse_binary_output("attract, repel, repel, attract because of the shift") == invalid


def test_wrong_length_binary_outputs_use_invalid_result():
    invalid = ParsedPrediction(labels=(), status=ParseStatus.INVALID)

    assert parse_binary_output("attract, repel, repel") == invalid
    assert parse_binary_output("attract, repel, repel, attract, attract") == invalid


# ---------------------------------------------------------------------------
# Narrative audit parser — valid cases
# ---------------------------------------------------------------------------


def _make_valid_json(labels=None) -> str:
    if labels is None:
        labels = ["attract", "repel", "repel", "attract"]
    return json.dumps({
        "inferred_rule_before": "opposite-sign attract, same-sign repel",
        "shift_evidence": "observations 3-5 contradict the initial rule",
        "inferred_rule_after": "same-sign attract, opposite-sign repel",
        "final_binary_answer": labels,
    })


def test_narrative_audit_parses_valid_json_with_all_fields():
    result = parse_narrative_audit_output(_make_valid_json())

    assert result.status is NarrativeParseStatus.VALID
    assert result.output is not None
    assert result.output.inferred_rule_before == "opposite-sign attract, same-sign repel"
    assert result.output.shift_evidence == "observations 3-5 contradict the initial rule"
    assert result.output.inferred_rule_after == "same-sign attract, opposite-sign repel"
    assert result.output.final_binary_answer == (ATTRACT, REPEL, REPEL, ATTRACT)
    assert result.failure_detail is None


def test_narrative_audit_output_is_frozen_dataclass():
    result = parse_narrative_audit_output(_make_valid_json())
    assert result.status is NarrativeParseStatus.VALID
    assert isinstance(result, NarrativeParsedResult)
    assert isinstance(result.output, NarrativeAuditOutput)


def test_narrative_audit_handles_json_in_markdown_code_block():
    text = "```json\n" + _make_valid_json() + "\n```"
    result = parse_narrative_audit_output(text)
    assert result.status is NarrativeParseStatus.VALID
    assert result.output.final_binary_answer == (ATTRACT, REPEL, REPEL, ATTRACT)


def test_narrative_audit_handles_plain_markdown_code_block():
    text = "```\n" + _make_valid_json() + "\n```"
    result = parse_narrative_audit_output(text)
    assert result.status is NarrativeParseStatus.VALID


def test_narrative_audit_case_insensitive_labels():
    result = parse_narrative_audit_output(json.dumps({
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["ATTRACT", "Repel", "REPEL", "Attract"],
    }))
    assert result.status is NarrativeParseStatus.VALID
    assert result.output.final_binary_answer == (ATTRACT, REPEL, REPEL, ATTRACT)


def test_narrative_audit_strips_whitespace_from_text_fields():
    result = parse_narrative_audit_output(json.dumps({
        "inferred_rule_before": "  rule A  ",
        "shift_evidence": "  evidence  ",
        "inferred_rule_after": "  rule B  ",
        "final_binary_answer": ["attract", "repel", "repel", "attract"],
    }))
    assert result.status is NarrativeParseStatus.VALID
    assert result.output.inferred_rule_before == "rule A"
    assert result.output.shift_evidence == "evidence"
    assert result.output.inferred_rule_after == "rule B"


# ---------------------------------------------------------------------------
# Narrative audit parser — invalid cases
# ---------------------------------------------------------------------------


def test_narrative_audit_rejects_empty_text():
    result = parse_narrative_audit_output("")
    assert result.status is NarrativeParseStatus.INVALID_FORMAT
    assert result.output is None


def test_narrative_audit_rejects_whitespace_only_text():
    result = parse_narrative_audit_output("   \n  ")
    assert result.status is NarrativeParseStatus.INVALID_FORMAT


def test_narrative_audit_rejects_non_json_prose():
    result = parse_narrative_audit_output(
        "The rule shifted after observation 3. My answers are attract, repel, repel, attract."
    )
    assert result.status is NarrativeParseStatus.INVALID_FORMAT
    assert result.output is None


def test_narrative_audit_rejects_json_array_root():
    result = parse_narrative_audit_output('["attract", "repel", "repel", "attract"]')
    assert result.status is NarrativeParseStatus.INVALID_FORMAT


def test_narrative_audit_rejects_missing_inferred_rule_before():
    payload = {
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "repel", "attract"],
    }
    result = parse_narrative_audit_output(json.dumps(payload))
    assert result.status is NarrativeParseStatus.MISSING_FIELD
    assert "inferred_rule_before" in (result.failure_detail or "")


def test_narrative_audit_rejects_missing_shift_evidence():
    payload = {
        "inferred_rule_before": "rule A",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "repel", "attract"],
    }
    result = parse_narrative_audit_output(json.dumps(payload))
    assert result.status is NarrativeParseStatus.MISSING_FIELD
    assert "shift_evidence" in (result.failure_detail or "")


def test_narrative_audit_rejects_missing_final_binary_answer():
    payload = {
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
    }
    result = parse_narrative_audit_output(json.dumps(payload))
    assert result.status is NarrativeParseStatus.MISSING_FIELD
    assert "final_binary_answer" in (result.failure_detail or "")


def test_narrative_audit_rejects_empty_string_text_field():
    payload = {
        "inferred_rule_before": "",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "repel", "attract"],
    }
    result = parse_narrative_audit_output(json.dumps(payload))
    assert result.status is NarrativeParseStatus.MISSING_FIELD


def test_narrative_audit_rejects_invalid_label_value():
    payload = {
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "bounce", "attract"],
    }
    result = parse_narrative_audit_output(json.dumps(payload))
    assert result.status is NarrativeParseStatus.INVALID_LABELS
    assert result.output is None


def test_narrative_audit_rejects_too_few_labels():
    result = parse_narrative_audit_output(json.dumps({
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "repel"],
    }))
    assert result.status is NarrativeParseStatus.INVALID_LABELS


def test_narrative_audit_rejects_too_many_labels():
    result = parse_narrative_audit_output(json.dumps({
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": ["attract", "repel", "repel", "attract", "attract"],
    }))
    assert result.status is NarrativeParseStatus.INVALID_LABELS


def test_narrative_audit_rejects_non_list_final_binary_answer():
    result = parse_narrative_audit_output(json.dumps({
        "inferred_rule_before": "rule A",
        "shift_evidence": "evidence",
        "inferred_rule_after": "rule B",
        "final_binary_answer": "attract, repel, repel, attract",
    }))
    assert result.status is NarrativeParseStatus.INVALID_LABELS


# ---------------------------------------------------------------------------
# NarrativeParsedResult factory methods
# ---------------------------------------------------------------------------


def test_narrative_parsed_result_skipped_provider_failure_factory():
    result = NarrativeParsedResult.skipped_provider_failure()
    assert result.status is NarrativeParseStatus.SKIPPED_PROVIDER_FAILURE
    assert result.output is None
