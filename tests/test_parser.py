from core.parser import (
    NarrativeParseStatus,
    NarrativeParsedResult,
    ParseStatus,
    ParsedPrediction,
    parse_binary_output,
    parse_narrative_audit_output,
)
from tasks.ruleshift_benchmark.protocol import InteractionLabel

ATTRACT = InteractionLabel.ATTRACT
REPEL = InteractionLabel.REPEL


def _make_valid_narrative_text(final_decision: str = "attract, repel, repel, attract") -> str:
    return "\n".join(
        (
            "rule_before: opposite-sign attract, same-sign repel",
            "shift_evidence: observations 3-5 contradict the initial rule",
            "rule_after: same-sign attract, opposite-sign repel",
            f"final_decision: {final_decision}",
        )
    )


def test_binary_output_parses_canonical_and_whitespace_variants():
    expected = ParsedPrediction(
        labels=(ATTRACT, REPEL, REPEL, ATTRACT),
        status=ParseStatus.VALID,
    )

    assert parse_binary_output("attract, repel, repel, attract") == expected
    assert parse_binary_output("  ATTRACT,\nrepel,\nREPEL,\nattract  ") == expected


def test_binary_output_rejects_wrong_length_and_unknown_labels():
    invalid = ParsedPrediction(labels=(), status=ParseStatus.INVALID)

    assert parse_binary_output("attract, repel, repel") == invalid
    assert parse_binary_output("attract, repel, bounce, attract") == invalid


def test_narrative_parser_accepts_contract_and_code_block_wrapper():
    result = parse_narrative_audit_output(_make_valid_narrative_text())
    wrapped = parse_narrative_audit_output(f"```\n{_make_valid_narrative_text()}\n```")

    for parsed in (result, wrapped):
        assert parsed.status is NarrativeParseStatus.VALID
        assert parsed.output is not None
        assert parsed.output.final_decision == (ATTRACT, REPEL, REPEL, ATTRACT)


def test_narrative_parser_rejects_unknown_or_duplicate_fields():
    unknown = parse_narrative_audit_output(
        "\n".join(
            (
                "rule_before: rule A",
                "shift_evidence: evidence",
                "rule_after: rule B",
                "final_answer: attract, repel, repel, attract",
            )
        )
    )
    duplicate = parse_narrative_audit_output(
        "\n".join(
            (
                "rule_before: rule A",
                "shift_evidence: evidence",
                "rule_after: rule B",
                "rule_after: another rule",
            )
        )
    )

    assert unknown.status is NarrativeParseStatus.INVALID_FORMAT
    assert "unknown narrative field" in (unknown.failure_detail or "")
    assert duplicate.status is NarrativeParseStatus.INVALID_FORMAT
    assert "duplicate narrative field" in (duplicate.failure_detail or "")


def test_narrative_parser_rejects_empty_fields_and_invalid_labels():
    missing = parse_narrative_audit_output(
        "\n".join(
            (
                "rule_before: ",
                "shift_evidence: evidence",
                "rule_after: rule B",
                "final_decision: attract, repel, repel, attract",
            )
        )
    )
    invalid_labels = parse_narrative_audit_output(
        _make_valid_narrative_text("attract, repel, bounce, attract")
    )

    assert missing.status is NarrativeParseStatus.MISSING_FIELD
    assert "rule_before" in (missing.failure_detail or "")
    assert invalid_labels.status is NarrativeParseStatus.INVALID_LABELS


def test_narrative_parsed_result_skipped_provider_failure_factory():
    result = NarrativeParsedResult.skipped_provider_failure()

    assert result.status is NarrativeParseStatus.SKIPPED_PROVIDER_FAILURE
    assert result.output is None
