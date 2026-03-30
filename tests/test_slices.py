from __future__ import annotations

from core.parser import NarrativeParseStatus, NarrativeParsedResult, ParseStatus, ParsedPrediction
from core.slices import (
    SLICE_DIMENSIONS,
    ErrorType,
    EpisodeSliceData,
    SliceAccuracy,
    build_slice_report,
    classify_binary_error_type,
    compute_episode_slice_data,
)
from tasks.ruleshift_benchmark.generator import generate_episode
from tasks.ruleshift_benchmark.protocol import PROBE_COUNT, InteractionLabel

ATTRACT = InteractionLabel.ATTRACT
REPEL = InteractionLabel.REPEL


class _FakeMeta:
    def __init__(self, old: InteractionLabel, new: InteractionLabel) -> None:
        self.old_rule_label = old
        self.new_rule_label = new


def _valid_prediction(*labels: InteractionLabel) -> ParsedPrediction:
    return ParsedPrediction(labels=labels, status=ParseStatus.VALID)


def _invalid_narrative() -> NarrativeParsedResult:
    return NarrativeParsedResult(output=None, status=NarrativeParseStatus.INVALID_FORMAT)


def _make_episode_slice(
    *,
    template: str = "T1",
    template_family: str = "canonical",
    difficulty: str = "easy",
    shift_position: str = "2",
    transition_type: str = "R_std_to_R_inv",
    error_type: ErrorType = ErrorType.UNKNOWN,
    correct_probes: int = 4,
) -> EpisodeSliceData:
    return EpisodeSliceData(
        episode_id="ep-1",
        template=template,
        template_family=template_family,
        difficulty=difficulty,
        shift_position=shift_position,
        transition_type=transition_type,
        error_type=error_type,
        correct_probes=correct_probes,
        total_probes=PROBE_COUNT,
    )


def test_classify_binary_error_type_preserves_priority_order():
    targets = (ATTRACT, ATTRACT, ATTRACT, ATTRACT)

    assert classify_binary_error_type(
        prediction=_valid_prediction(REPEL, REPEL, REPEL, REPEL),
        targets=targets,
        probe_metadata=tuple(_FakeMeta(REPEL, ATTRACT) for _ in range(PROBE_COUNT)),
        narrative_result=_invalid_narrative(),
    ) is ErrorType.INVALID_NARRATIVE

    assert classify_binary_error_type(
        prediction=_valid_prediction(REPEL, REPEL, REPEL, REPEL),
        targets=targets,
        probe_metadata=tuple(_FakeMeta(REPEL, ATTRACT) for _ in range(PROBE_COUNT)),
    ) is ErrorType.OLD_RULE_PERSISTENCE

    assert classify_binary_error_type(
        prediction=_valid_prediction(ATTRACT, ATTRACT, ATTRACT, ATTRACT),
        targets=(REPEL, REPEL, REPEL, REPEL),
        probe_metadata=tuple(_FakeMeta(REPEL, ATTRACT) for _ in range(PROBE_COUNT)),
    ) is ErrorType.RECENCY_OVERWEIGHT

    assert classify_binary_error_type(
        prediction=_valid_prediction(REPEL, REPEL, ATTRACT, ATTRACT),
        targets=targets,
        probe_metadata=(
            _FakeMeta(REPEL, ATTRACT),
            _FakeMeta(ATTRACT, REPEL),
            _FakeMeta(REPEL, ATTRACT),
            _FakeMeta(REPEL, ATTRACT),
        ),
    ) is ErrorType.PREMATURE_SWITCH


def test_compute_episode_slice_data_extracts_runtime_metadata():
    episode = generate_episode(0)
    result = compute_episode_slice_data(
        episode=episode,
        prediction=_valid_prediction(*episode.probe_targets),
    )

    assert result.episode_id == episode.episode_id
    assert result.template == episode.template_id.value
    assert result.template_family == episode.template_family.value
    assert result.difficulty == episode.difficulty.value
    assert result.shift_position == str(episode.shift_after_position)
    assert result.transition_type == episode.transition.value
    assert result.correct_probes == PROBE_COUNT
    assert result.total_probes == PROBE_COUNT


def test_slice_accuracy_and_report_preserve_canonical_output_shape():
    accuracy = SliceAccuracy(episode_count=2, correct_probes=6, total_probes=8)
    assert accuracy.accuracy == 0.75

    report = build_slice_report(
        [
            _make_episode_slice(template="T2", difficulty="medium", correct_probes=2),
            _make_episode_slice(
                template="T1",
                template_family="observation_log",
                difficulty="easy",
                error_type=ErrorType.OLD_RULE_PERSISTENCE,
                correct_probes=0,
            ),
        ]
    )

    report_dict = report.to_dict()
    assert tuple(report_dict) == SLICE_DIMENSIONS
    assert list(report_dict["template"]) == ["T1", "T2"]
    assert list(report_dict["difficulty"]) == ["easy", "medium", "hard"]
    assert report_dict["error_type"][ErrorType.OLD_RULE_PERSISTENCE.value] == 1
    assert report_dict["error_type"][ErrorType.UNKNOWN.value] == 1
