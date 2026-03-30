from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from tasks.ruleshift_benchmark.protocol import (
    PROBE_COUNT,
    InteractionLabel,
    parse_label,
)

__all__ = [
    "PARSER_VERSION",
    "ParseStatus",
    "ParsedPrediction",
    "parse_binary_output",
    "NarrativeParseStatus",
    "NarrativeAuditOutput",
    "NarrativeParsedResult",
    "parse_narrative_audit_output",
]

PARSER_VERSION = "v2"
_SEPARATOR_PATTERN = re.compile(r"[\n,]+")
_CODE_BLOCK_RE = re.compile(r"\A```(?:[^\n`]*)?\s*\n(.*?)\n\s*```\Z", re.DOTALL)
_NARRATIVE_FIELD_ORDER = (
    "rule_before",
    "shift_evidence",
    "rule_after",
    "final_decision",
)
_NARRATIVE_FIELD_SET = frozenset(_NARRATIVE_FIELD_ORDER)


class ParseStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    SKIPPED_PROVIDER_FAILURE = "skipped_provider_failure"


@dataclass(frozen=True, slots=True)
class ParsedPrediction:
    labels: tuple[InteractionLabel, ...]
    status: ParseStatus

    @classmethod
    def skipped_provider_failure(cls) -> "ParsedPrediction":
        return cls(labels=(), status=ParseStatus.SKIPPED_PROVIDER_FAILURE)


_INVALID_PREDICTION = ParsedPrediction(labels=(), status=ParseStatus.INVALID)


class NarrativeParseStatus(StrEnum):
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    MISSING_FIELD = "missing_field"
    INVALID_LABELS = "invalid_labels"
    SKIPPED_PROVIDER_FAILURE = "skipped_provider_failure"


@dataclass(frozen=True, slots=True)
class NarrativeAuditOutput:
    rule_before: str
    shift_evidence: str
    rule_after: str
    final_decision: tuple[InteractionLabel, ...]


@dataclass(frozen=True, slots=True)
class NarrativeParsedResult:
    output: NarrativeAuditOutput | None
    status: NarrativeParseStatus
    failure_detail: str | None = None

    @classmethod
    def skipped_provider_failure(cls) -> "NarrativeParsedResult":
        return cls(output=None, status=NarrativeParseStatus.SKIPPED_PROVIDER_FAILURE)


def parse_binary_output(text: str) -> ParsedPrediction:
    return _parse_labels_payload(text)


def parse_narrative_audit_output(text: str) -> NarrativeParsedResult:
    """Parse a four-line narrative audit response."""
    if not text or not text.strip():
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_FORMAT,
            failure_detail="empty response",
        )

    normalized_text = text.strip()
    block_match = _CODE_BLOCK_RE.fullmatch(normalized_text)
    if block_match:
        normalized_text = block_match.group(1).strip()

    payload: dict[str, str] = {}
    content_lines = tuple(
        line.strip() for line in normalized_text.splitlines() if line.strip()
    )
    if len(content_lines) != len(_NARRATIVE_FIELD_ORDER):
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_FORMAT,
            failure_detail="response must contain exactly 4 non-empty contract lines",
        )

    for line in content_lines:
        key, separator, value = line.partition(":")
        if not separator:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.INVALID_FORMAT,
                failure_detail="each contract line must be formatted as key: value",
            )
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key not in _NARRATIVE_FIELD_SET:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.INVALID_FORMAT,
                failure_detail=f"unknown narrative field: {key.strip()!r}",
            )
        if normalized_key in payload:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.INVALID_FORMAT,
                failure_detail=f"duplicate narrative field: {normalized_key!r}",
            )
        if not normalized_value:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.MISSING_FIELD,
                failure_detail=f"{normalized_key!r} must be a non-empty string",
            )
        payload[normalized_key] = normalized_value

    for field_name in _NARRATIVE_FIELD_ORDER:
        if field_name not in payload:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.MISSING_FIELD,
                failure_detail=f"missing required field: {field_name!r}",
            )

    parsed_labels = _parse_labels_payload(payload["final_decision"])
    if parsed_labels.status is not ParseStatus.VALID:
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_LABELS,
            failure_detail=(
                f"final_decision must contain exactly {PROBE_COUNT} labels "
                "using only attract or repel"
            ),
        )

    return NarrativeParsedResult(
        output=NarrativeAuditOutput(
            rule_before=payload["rule_before"],
            shift_evidence=payload["shift_evidence"],
            rule_after=payload["rule_after"],
            final_decision=parsed_labels.labels,
        ),
        status=NarrativeParseStatus.VALID,
    )


def _parse_labels_payload(text: str) -> ParsedPrediction:
    normalized_text = text.strip()
    if not normalized_text:
        return _INVALID_PREDICTION

    raw_tokens = tuple(_SEPARATOR_PATTERN.split(normalized_text))
    normalized_tokens = tuple(token.strip().lower() for token in raw_tokens if token.strip())
    if len(normalized_tokens) != PROBE_COUNT:
        return _INVALID_PREDICTION

    try:
        labels = tuple(parse_label(token) for token in normalized_tokens)
    except ValueError:
        return _INVALID_PREDICTION

    return ParsedPrediction(labels=labels, status=ParseStatus.VALID)
