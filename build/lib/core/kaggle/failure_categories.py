from __future__ import annotations

from core.parser import NarrativeParseStatus, ParseStatus

__all__ = [
    "FAILURE_CATEGORY_BINARY_PARSE_FAILURE",
    "FAILURE_CATEGORY_NARRATIVE_PARSE_FAILURE",
    "FAILURE_CATEGORY_PROVIDER_FAILURE",
    "FAILURE_CATEGORY_SCHEMA_COERCION_FAILURE",
    "FAILURE_CATEGORY_TIMEOUT",
    "FAILURE_CATEGORY_TRANSPORT_FAILURE",
    "FAILURE_CATEGORY_UNEXPECTED_RUNTIME_ERROR",
    "FAILURE_CATEGORY_INVALID_PREDICTION_SHAPE",
    "OUTCOME_KIND_MODEL_PARSE_FAILURE",
    "OUTCOME_KIND_OPERATIONAL_FAILURE",
    "OUTCOME_KIND_SCORED_MODEL_RESULT",
    "classify_binary_parse_status",
    "classify_narrative_parse_status",
    "classify_operational_exception",
]

FAILURE_CATEGORY_PROVIDER_FAILURE = "provider_failure"
FAILURE_CATEGORY_TRANSPORT_FAILURE = "transport_failure"
FAILURE_CATEGORY_TIMEOUT = "timeout"
FAILURE_CATEGORY_BINARY_PARSE_FAILURE = "binary_parse_failure"
FAILURE_CATEGORY_NARRATIVE_PARSE_FAILURE = "narrative_parse_failure"
FAILURE_CATEGORY_SCHEMA_COERCION_FAILURE = "schema_coercion_failure"
FAILURE_CATEGORY_INVALID_PREDICTION_SHAPE = "invalid_prediction_shape"
FAILURE_CATEGORY_UNEXPECTED_RUNTIME_ERROR = "unexpected_runtime_error"

OUTCOME_KIND_SCORED_MODEL_RESULT = "scored_model_result"
OUTCOME_KIND_MODEL_PARSE_FAILURE = "model_parse_failure"
OUTCOME_KIND_OPERATIONAL_FAILURE = "operational_failure"


def classify_binary_parse_status(
    status: ParseStatus,
) -> tuple[str, str | None]:
    if status is ParseStatus.VALID:
        return OUTCOME_KIND_SCORED_MODEL_RESULT, None
    if status is ParseStatus.SKIPPED_PROVIDER_FAILURE:
        return OUTCOME_KIND_OPERATIONAL_FAILURE, FAILURE_CATEGORY_PROVIDER_FAILURE
    return OUTCOME_KIND_MODEL_PARSE_FAILURE, FAILURE_CATEGORY_BINARY_PARSE_FAILURE


def classify_narrative_parse_status(
    status: NarrativeParseStatus,
) -> tuple[str, str | None]:
    if status is NarrativeParseStatus.VALID:
        return OUTCOME_KIND_SCORED_MODEL_RESULT, None
    if status is NarrativeParseStatus.SKIPPED_PROVIDER_FAILURE:
        return OUTCOME_KIND_OPERATIONAL_FAILURE, FAILURE_CATEGORY_PROVIDER_FAILURE
    return OUTCOME_KIND_MODEL_PARSE_FAILURE, FAILURE_CATEGORY_NARRATIVE_PARSE_FAILURE


def classify_operational_exception(
    *,
    exc: BaseException,
    failure_stage: str,
) -> str:
    if failure_stage == "provider_call":
        return _classify_provider_exception(exc)
    if failure_stage == "response_parse":
        return FAILURE_CATEGORY_SCHEMA_COERCION_FAILURE
    if failure_stage == "episode_scoring":
        message = str(exc).lower()
        if "exactly 4" in message or "same number of rows" in message:
            return FAILURE_CATEGORY_INVALID_PREDICTION_SHAPE
        return FAILURE_CATEGORY_UNEXPECTED_RUNTIME_ERROR
    return FAILURE_CATEGORY_UNEXPECTED_RUNTIME_ERROR


def _classify_provider_exception(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return FAILURE_CATEGORY_TIMEOUT
    if isinstance(exc, (ConnectionError, BrokenPipeError)):
        return FAILURE_CATEGORY_TRANSPORT_FAILURE

    message = str(exc).lower()
    if "timeout" in message or "timed out" in message:
        return FAILURE_CATEGORY_TIMEOUT
    if any(token in message for token in ("connection", "transport", "network", "socket")):
        return FAILURE_CATEGORY_TRANSPORT_FAILURE
    return FAILURE_CATEGORY_PROVIDER_FAILURE
