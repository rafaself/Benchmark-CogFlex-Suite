from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
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

PARSER_VERSION = "v1"
_SEPARATOR_PATTERN = re.compile(r"[\n,]+")
_NUMBER_PREFIX_RE = re.compile(r"^\d+\.?\s*")
_BOLD_MARKER_RE = re.compile(r"\*+")
_JSON_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL | re.IGNORECASE)

_NARRATIVE_SCHEMA_FIELDS = (
    "inferred_rule_before",
    "shift_evidence",
    "inferred_rule_after",
    "final_binary_answer",
)


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
    inferred_rule_before: str
    shift_evidence: str
    inferred_rule_after: str
    final_binary_answer: tuple[InteractionLabel, ...]


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
    """Parse a structured JSON narrative audit response.

    Expects a JSON object with fields: inferred_rule_before, shift_evidence,
    inferred_rule_after, final_binary_answer (list of exactly 4 labels).
    """
    if not text or not text.strip():
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_FORMAT,
            failure_detail="empty response",
        )

    json_text = text.strip()
    # Unwrap markdown code block if present.
    block_match = _JSON_CODE_BLOCK_RE.search(json_text)
    if block_match:
        json_text = block_match.group(1).strip()

    try:
        payload = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_FORMAT,
            failure_detail="response is not valid JSON",
        )

    if not isinstance(payload, dict):
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_FORMAT,
            failure_detail="JSON root must be an object",
        )

    for field_name in _NARRATIVE_SCHEMA_FIELDS:
        if field_name not in payload:
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.MISSING_FIELD,
                failure_detail=f"missing required field: {field_name!r}",
            )

    for field_name in ("inferred_rule_before", "shift_evidence", "inferred_rule_after"):
        if not isinstance(payload[field_name], str) or not payload[field_name].strip():
            return NarrativeParsedResult(
                output=None,
                status=NarrativeParseStatus.MISSING_FIELD,
                failure_detail=f"{field_name!r} must be a non-empty string",
            )

    raw_labels = payload["final_binary_answer"]
    if not isinstance(raw_labels, list) or len(raw_labels) != PROBE_COUNT:
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_LABELS,
            failure_detail=f"final_binary_answer must be a list of exactly {PROBE_COUNT} labels",
        )

    try:
        labels = tuple(parse_label(str(lbl).strip().lower()) for lbl in raw_labels)
    except ValueError as exc:
        return NarrativeParsedResult(
            output=None,
            status=NarrativeParseStatus.INVALID_LABELS,
            failure_detail=f"invalid label value: {exc}",
        )

    return NarrativeParsedResult(
        output=NarrativeAuditOutput(
            inferred_rule_before=payload["inferred_rule_before"].strip(),
            shift_evidence=payload["shift_evidence"].strip(),
            inferred_rule_after=payload["inferred_rule_after"].strip(),
            final_binary_answer=labels,
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
