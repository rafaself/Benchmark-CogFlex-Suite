from metrics import MetricSummary, compute_metrics, compute_post_shift_probe_accuracy
from parser import ParsedPrediction, ParseStatus
from protocol import InteractionLabel


def _valid_prediction(*labels: InteractionLabel) -> ParsedPrediction:
    return ParsedPrediction(labels=labels, status=ParseStatus.VALID)


def _invalid_prediction() -> ParsedPrediction:
    return ParsedPrediction(labels=(), status=ParseStatus.INVALID)


def test_post_shift_probe_accuracy_matches_hand_checked_fixture():
    predictions = (
        _valid_prediction(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        _valid_prediction(
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )
    targets = (
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
        ),
    )

    assert compute_post_shift_probe_accuracy(predictions, targets) == 0.75


def test_invalid_parses_contribute_zero_correct_probes():
    predictions = (
        _valid_prediction(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        _invalid_prediction(),
    )
    targets = (
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        (
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )

    assert compute_post_shift_probe_accuracy(predictions, targets) == 0.5


def test_binary_and_narrative_accuracy_match_when_final_labels_match():
    shared_predictions = (
        _valid_prediction(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        _valid_prediction(
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
        ),
    )
    shared_targets = (
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        (
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
        ),
    )

    summary = compute_metrics(
        binary_predictions=shared_predictions,
        binary_targets=shared_targets,
        narrative_predictions=shared_predictions,
        narrative_targets=shared_targets,
    )

    assert summary.binary_accuracy == summary.narrative_accuracy == 0.875


def test_compute_metrics_returns_stable_mixed_mode_scores():
    binary_predictions = (
        _valid_prediction(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        _invalid_prediction(),
    )
    binary_targets = (
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        (
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )
    narrative_predictions = (
        _valid_prediction(
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )
    narrative_targets = (
        (
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
        ),
    )

    assert compute_metrics(
        binary_predictions=binary_predictions,
        binary_targets=binary_targets,
        narrative_predictions=narrative_predictions,
        narrative_targets=narrative_targets,
    ) == MetricSummary(
        post_shift_probe_accuracy=0.5,
        parse_valid_rate=2 / 3,
        binary_accuracy=0.5,
        narrative_accuracy=0.75,
    )


def test_narrative_cannot_change_the_headline_binary_metric():
    binary_predictions = (
        _valid_prediction(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )
    binary_targets = (
        (
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
    )
    narrative_predictions = (_invalid_prediction(),)
    narrative_targets = binary_targets

    assert compute_metrics(
        binary_predictions=binary_predictions,
        binary_targets=binary_targets,
        narrative_predictions=narrative_predictions,
        narrative_targets=narrative_targets,
    ) == MetricSummary(
        post_shift_probe_accuracy=1.0,
        parse_valid_rate=0.5,
        binary_accuracy=1.0,
        narrative_accuracy=0.0,
    )
