from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from core.kaggle.types import (
    BinaryResponse,
    Label,
    normalize_binary_response,
    parse_binary_response,
    parse_narrative_response,
    score_episode,
)
from core.parser import NarrativeParseStatus, ParseStatus
from tasks.ruleshift_benchmark.protocol import InteractionLabel

ATTRACT = InteractionLabel.ATTRACT
REPEL = InteractionLabel.REPEL
_VALID_TARGETS = ("attract", "repel", "repel", "attract")


def _make_valid_narrative_text() -> str:
    return "\n".join(
        (
            "rule_before: opposite-sign attract, same-sign repel",
            "shift_evidence: observations 3-5 contradict the initial rule",
            "rule_after: same-sign attract, opposite-sign repel",
            "final_decision: attract, repel, repel, attract",
        )
    )


def test_binary_response_accepts_supported_structured_shapes():
    dataclass_response = BinaryResponse(Label.attract, Label.repel, Label.repel, Label.attract)
    mapping_response = MappingProxyType(
        {"probe_6": "attract", "probe_7": "repel", "probe_8": "repel", "probe_9": "attract"}
    )

    @dataclass(frozen=True)
    class SDKResponse:
        probe_6: str
        probe_7: str
        probe_8: str
        probe_9: str

    attribute_response = SDKResponse("attract", "repel", "repel", "attract")

    class CustomLabel(Enum):
        ATTRACT = "attract"
        REPEL = "repel"

    enum_mapping = {
        "probe_6": CustomLabel.ATTRACT,
        "probe_7": CustomLabel.REPEL,
        "probe_8": CustomLabel.REPEL,
        "probe_9": CustomLabel.ATTRACT,
    }

    for response in (dataclass_response, mapping_response, attribute_response, enum_mapping):
        parsed = parse_binary_response(response)
        assert parsed.status is ParseStatus.VALID
        assert tuple(label.value for label in parsed.labels) == _VALID_TARGETS


def test_binary_response_distinguishes_provider_failure_from_invalid_shape():
    assert parse_binary_response(None).status is ParseStatus.SKIPPED_PROVIDER_FAILURE
    assert parse_binary_response({}).status is ParseStatus.INVALID
    assert parse_binary_response({"probe_6": "attract", "probe_7": "repel"}).status is ParseStatus.INVALID


def test_binary_response_shape_regression_still_scores_correctly():
    response = {"probe_6": "attract", "probe_7": "repel", "probe_8": "repel", "probe_9": "attract"}
    parsed = parse_binary_response(response)

    assert normalize_binary_response(response) == _VALID_TARGETS
    assert score_episode(tuple(label.value for label in parsed.labels), _VALID_TARGETS) == (4, 4)
    assert score_episode(None, _VALID_TARGETS) == (0, 4)


def test_narrative_response_accepts_dict_and_wrapper_text_shapes():
    @dataclass
    class Wrapper:
        content: str

    dict_result = parse_narrative_response({"text": _make_valid_narrative_text()})
    wrapper_result = parse_narrative_response(Wrapper(content=_make_valid_narrative_text()))

    assert dict_result.status is NarrativeParseStatus.VALID
    assert wrapper_result.status is NarrativeParseStatus.VALID


def test_narrative_response_preserves_invalid_format_for_unsupported_shapes():
    parsed = parse_narrative_response({"unrecognized": 42})

    assert parsed.status is NarrativeParseStatus.INVALID_FORMAT
    assert "unsupported response type" in (parsed.failure_detail or "")
