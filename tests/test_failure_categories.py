from __future__ import annotations

from core.kaggle import (
    FAILURE_CATEGORY_BINARY_PARSE_FAILURE,
    FAILURE_CATEGORY_INVALID_PREDICTION_SHAPE,
    FAILURE_CATEGORY_NARRATIVE_PARSE_FAILURE,
    FAILURE_CATEGORY_PROVIDER_FAILURE,
    FAILURE_CATEGORY_SCHEMA_COERCION_FAILURE,
    FAILURE_CATEGORY_TIMEOUT,
    OUTCOME_KIND_MODEL_PARSE_FAILURE,
    OUTCOME_KIND_OPERATIONAL_FAILURE,
    OUTCOME_KIND_SCORED_MODEL_RESULT,
    classify_binary_parse_status,
    classify_narrative_parse_status,
    classify_operational_exception,
)
from core.parser import NarrativeParseStatus, ParseStatus


def test_classify_binary_parse_status_distinguishes_model_parse_and_operational_paths():
    assert classify_binary_parse_status(ParseStatus.VALID) == (
        OUTCOME_KIND_SCORED_MODEL_RESULT,
        None,
    )
    assert classify_binary_parse_status(ParseStatus.INVALID) == (
        OUTCOME_KIND_MODEL_PARSE_FAILURE,
        FAILURE_CATEGORY_BINARY_PARSE_FAILURE,
    )
    assert classify_binary_parse_status(ParseStatus.SKIPPED_PROVIDER_FAILURE) == (
        OUTCOME_KIND_OPERATIONAL_FAILURE,
        FAILURE_CATEGORY_PROVIDER_FAILURE,
    )


def test_classify_narrative_parse_status_distinguishes_model_parse_and_operational_paths():
    assert classify_narrative_parse_status(NarrativeParseStatus.VALID) == (
        OUTCOME_KIND_SCORED_MODEL_RESULT,
        None,
    )
    assert classify_narrative_parse_status(NarrativeParseStatus.INVALID_FORMAT) == (
        OUTCOME_KIND_MODEL_PARSE_FAILURE,
        FAILURE_CATEGORY_NARRATIVE_PARSE_FAILURE,
    )
    assert classify_narrative_parse_status(NarrativeParseStatus.SKIPPED_PROVIDER_FAILURE) == (
        OUTCOME_KIND_OPERATIONAL_FAILURE,
        FAILURE_CATEGORY_PROVIDER_FAILURE,
    )


def test_classify_operational_exception_maps_timeout_and_shape_errors():
    assert classify_operational_exception(
        exc=TimeoutError("provider timeout"),
        failure_stage="provider_call",
    ) == FAILURE_CATEGORY_TIMEOUT
    assert classify_operational_exception(
        exc=ValueError("probe_targets must contain exactly 4 valid labels"),
        failure_stage="episode_scoring",
    ) == FAILURE_CATEGORY_INVALID_PREDICTION_SHAPE
    assert classify_operational_exception(
        exc=TypeError("schema wrapper exploded"),
        failure_stage="response_parse",
    ) == FAILURE_CATEGORY_SCHEMA_COERCION_FAILURE
