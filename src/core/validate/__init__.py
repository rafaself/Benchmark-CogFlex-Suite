from __future__ import annotations

from importlib import import_module

from core.validate.episode import (
    EpisodeValidationResult,
    RegenerationCheck,
    ValidationIssue,
    normalize_episode_payload,
    validate_episode,
)
from core.validate.dataset import (
    DatasetDistributionSummary,
    DatasetValidationResult,
    validate_dataset,
)

__all__ = [
    "ValidationIssue",
    "RegenerationCheck",
    "EpisodeValidationResult",
    "DatasetDistributionSummary",
    "DatasetValidationResult",
    "SplitBaselineAccuracySummary",
    "BaselineAccuracySummary",
    "ShortcutUpperBoundRule",
    "DominantHeuristicRule",
    "SubsetSeparationRule",
    "ValidityGateConfig",
    "ValidityGateCheck",
    "BenchmarkValidityReport",
    "R13_VALIDITY_GATE",
    "normalize_episode_payload",
    "run_benchmark_validity_report",
    "evaluate_benchmark_validity_gate",
    "serialize_benchmark_validity_report",
    "validate_benchmark_validity",
    "validate_episode",
    "validate_dataset",
]

_GATE_EXPORTS = {
    "SplitBaselineAccuracySummary",
    "BaselineAccuracySummary",
    "ShortcutUpperBoundRule",
    "DominantHeuristicRule",
    "SubsetSeparationRule",
    "ValidityGateConfig",
    "ValidityGateCheck",
    "BenchmarkValidityReport",
    "R13_VALIDITY_GATE",
    "run_benchmark_validity_report",
    "evaluate_benchmark_validity_gate",
    "serialize_benchmark_validity_report",
    "validate_benchmark_validity",
}


def __getattr__(name: str):
    if name not in _GATE_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module("core.validate.gate")
    value = getattr(module, name)
    globals()[name] = value
    return value
