from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Sequence

from core.parser import (
    NarrativeParsedResult,
    NarrativeParseStatus,
    ParsedPrediction,
    ParseStatus,
    parse_binary_output,
    parse_narrative_audit_output,
)
from tasks.ruleshift_benchmark.protocol import PROBE_COUNT, InteractionLabel, parse_label

__all__ = [
    "Label",
    "BinaryResponse",
    "ConfidenceInterval",
    "parse_binary_response",
    "parse_narrative_response",
    "normalize_binary_response",
    "normalize_narrative_response",
    "score_episode",
    "compute_bootstrap_confidence_interval",
]


class Label(str, Enum):
    attract = "attract"
    repel = "repel"


@dataclass(frozen=True, slots=True)
class BinaryResponse:
    probe_6: Label
    probe_7: Label
    probe_8: Label
    probe_9: Label

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.probe_6.value,
            self.probe_7.value,
            self.probe_8.value,
            self.probe_9.value,
        )


def normalize_binary_response(response: object) -> tuple[str, ...] | None:
    parsed = parse_binary_response(response)
    if parsed.status is ParseStatus.VALID:
        return tuple(label.value for label in parsed.labels)
    return None


def normalize_narrative_response(response: object) -> tuple[str, ...] | None:
    parsed = parse_narrative_response(response)
    if parsed.status is NarrativeParseStatus.VALID and parsed.output is not None:
        return tuple(label.value for label in parsed.output.final_decision)
    return None


def parse_binary_response(response: object) -> ParsedPrediction:
    if response is None:
        return ParsedPrediction.skipped_provider_failure()

    if isinstance(response, BinaryResponse):
        return ParsedPrediction(
            labels=tuple(parse_label(label) for label in response.as_tuple()),
            status=ParseStatus.VALID,
        )

    if isinstance(response, str):
        return parse_binary_output(response)

    return ParsedPrediction(labels=(), status=ParseStatus.INVALID)


def parse_narrative_response(response: object) -> NarrativeParsedResult:
    if response is None:
        return NarrativeParsedResult.skipped_provider_failure()

    if isinstance(response, str):
        return parse_narrative_audit_output(response)

    return NarrativeParsedResult(
        output=None,
        status=NarrativeParseStatus.INVALID_FORMAT,
        failure_detail="unsupported response type",
    )


def score_episode(
    predictions: tuple[str, ...] | tuple[InteractionLabel, ...] | None,
    probe_targets: tuple[str, ...] | tuple[InteractionLabel, ...],
) -> tuple[int, int]:
    normalized_targets = _normalize_labels(probe_targets)
    if normalized_targets is None:
        raise ValueError(f"probe_targets must contain exactly {PROBE_COUNT} valid labels")

    normalized_predictions = _normalize_labels(predictions)
    if normalized_predictions is None:
        return (0, PROBE_COUNT)

    num_correct = sum(
        prediction is target
        for prediction, target in zip(normalized_predictions, normalized_targets)
    )
    return (num_correct, PROBE_COUNT)


def _normalize_labels(
    labels: tuple[str, ...] | tuple[InteractionLabel, ...] | None,
) -> tuple[InteractionLabel, ...] | None:
    if labels is None:
        return None

    normalized_labels = tuple(parse_label(label) for label in labels)
    if len(normalized_labels) != PROBE_COUNT:
        return None
    return normalized_labels


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    mean: float
    lower: float
    upper: float
    level: float
    margin: float


def compute_bootstrap_confidence_interval(
    num_correct: Sequence[int],
    total: Sequence[int],
    *,
    level: float = 0.95,
    n_bootstraps: int = 1000,
    seed: int = 2025,
) -> ConfidenceInterval:
    if len(num_correct) != len(total):
        raise ValueError("num_correct and total must have the same length")

    n = len(num_correct)
    if n == 0:
        return ConfidenceInterval(0.0, 0.0, 0.0, level, 0.0)

    nc = list(num_correct)
    tot = list(total)
    grand_total_probes = sum(tot)

    if grand_total_probes == 0:
        return ConfidenceInterval(0.0, 0.0, 0.0, level, 0.0)

    grand_mean = sum(nc) / grand_total_probes

    rng = random.Random(seed)
    indices = range(n)
    means: list[float] = []

    for _ in range(n_bootstraps):
        sample_indices = rng.choices(indices, k=n)
        s_c = sum(nc[i] for i in sample_indices)
        s_t = sum(tot[i] for i in sample_indices)
        if s_t > 0:
            means.append(s_c / s_t)
        else:
            means.append(0.0)

    means.sort()

    alpha = 1.0 - level
    lower_idx = int(n_bootstraps * (alpha / 2))
    upper_idx = int(n_bootstraps * (1 - (alpha / 2)))

    lower_idx = max(0, min(lower_idx, n_bootstraps - 1))
    upper_idx = max(0, min(upper_idx, n_bootstraps - 1))

    lower = means[lower_idx]
    upper = means[upper_idx]

    margin = max(grand_mean - lower, upper - grand_mean)

    return ConfidenceInterval(
        mean=grand_mean,
        lower=lower,
        upper=upper,
        level=level,
        margin=margin,
    )
