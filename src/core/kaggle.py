from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Final, Sequence

from core.parser import ParseStatus, parse_binary_output, parse_narrative_output
from core.splits import MANIFEST_VERSION, PARTITIONS, load_split_manifest
from tasks.ruleshift_benchmark.protocol import PROBE_COUNT, InteractionLabel, parse_label
from tasks.ruleshift_benchmark.schema import (
    DIFFICULTY_VERSION,
    GENERATOR_VERSION,
    SPEC_VERSION,
    TEMPLATE_SET_VERSION,
)

__all__ = [
    "Label",
    "BinaryResponse",
    "ConfidenceInterval",
    "KAGGLE_STAGING_MANIFEST_PATH",
    "build_kaggle_payload",
    "compute_bootstrap_confidence_interval",
    "load_kaggle_staging_manifest",
    "normalize_binary_response",
    "normalize_narrative_response",
    "resolve_kaggle_artifact_path",
    "score_episode",
    "validate_kaggle_payload",
    "validate_kaggle_staging_manifest",
]

_ARTIFACT_GROUPS: Final[tuple[str, ...]] = (
    "entry_points",
    "frozen_split_manifests",
)
_RUNTIME_ENTRY_POINTS: Final[tuple[str, ...]] = (
    "kbench_notebook",
    "kernel_metadata",
)
_EXPECTED_BENCHMARK_VERSIONS: Final[dict[str, str]] = {
    "manifest_version": MANIFEST_VERSION,
    "spec_version": SPEC_VERSION,
    "generator_version": GENERATOR_VERSION,
    "template_set_version": TEMPLATE_SET_VERSION,
    "difficulty_version": DIFFICULTY_VERSION,
}


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


def _repo_root(repo_root: Path | str | None = None) -> Path:
    if repo_root is None:
        return Path(__file__).resolve().parents[2]
    return Path(repo_root).resolve()


def _manifest_path(repo_root: Path | str | None = None) -> Path:
    # The filename is retained for compatibility, but its role is now the
    # official Kaggle runtime-contract manifest rather than a broad package index.
    return _repo_root(repo_root) / "packaging" / "kaggle" / "frozen_artifacts_manifest.json"


KAGGLE_STAGING_MANIFEST_PATH: Final[Path] = _manifest_path()


def load_kaggle_staging_manifest(
    repo_root: Path | str | None = None,
) -> dict[str, object]:
    return json.loads(_manifest_path(repo_root).read_text(encoding="utf-8"))


def resolve_kaggle_artifact_path(
    relative_path: str,
    *,
    repo_root: Path | str | None = None,
) -> Path:
    return _repo_root(repo_root) / relative_path


def validate_kaggle_staging_manifest(
    repo_root: Path | str | None = None,
) -> None:
    manifest = load_kaggle_staging_manifest(repo_root)

    if manifest.get("bundle_version") != "R16":
        raise ValueError("bundle_version must equal R16")
    if manifest.get("task_id") != "ruleshift_benchmark_v1":
        raise ValueError("task_id must equal ruleshift_benchmark_v1")
    if manifest.get("task_name") != "RuleShift Benchmark v1":
        raise ValueError("task_name must equal RuleShift Benchmark v1")

    benchmark_versions = manifest.get("benchmark_versions")
    if benchmark_versions != _EXPECTED_BENCHMARK_VERSIONS:
        raise ValueError(
            "benchmark_versions must match the canonical split and schema versions"
        )

    if manifest.get("current_emitted_difficulty_labels") != ["easy", "medium"]:
        raise ValueError(
            "current_emitted_difficulty_labels must equal ['easy', 'medium']"
        )
    if manifest.get("reserved_difficulty_labels") != ["hard"]:
        raise ValueError("reserved_difficulty_labels must equal ['hard']")

    frozen_split_manifests = _require_mapping(
        manifest,
        "frozen_split_manifests",
    )
    entry_points = _require_mapping(
        manifest,
        "entry_points",
    )
    if tuple(entry_points) != _RUNTIME_ENTRY_POINTS:
        raise ValueError("entry_points must contain only the official runtime submission paths")
    if tuple(frozen_split_manifests) != PARTITIONS:
        raise ValueError("frozen_split_manifests must follow the canonical partition order")

    for partition in PARTITIONS:
        artifact = _require_mapping(frozen_split_manifests, partition)
        split_manifest = load_split_manifest(partition)
        if artifact.get("manifest_version") != split_manifest.manifest_version:
            raise ValueError(f"{partition} manifest_version does not match the frozen split")
        if artifact.get("seed_bank_version") != split_manifest.seed_bank_version:
            raise ValueError(f"{partition} seed_bank_version does not match the frozen split")
        if artifact.get("episode_split") != split_manifest.episode_split.value:
            raise ValueError(f"{partition} episode_split does not match the frozen split")

    for group_name in _ARTIFACT_GROUPS:
        artifact_group = _require_mapping(manifest, group_name)
        for label, artifact in artifact_group.items():
            artifact_map = _require_mapping(artifact_group, label)
            relative_path = artifact_map.get("path")
            if not isinstance(relative_path, str) or not relative_path:
                raise ValueError(f"{group_name}.{label} must define a non-empty path")
            sha256 = artifact_map.get("sha256")
            if not isinstance(sha256, str) or not sha256:
                raise ValueError(f"{group_name}.{label} must define a non-empty sha256")

            artifact_path = resolve_kaggle_artifact_path(
                relative_path,
                repo_root=repo_root,
            )
            if not artifact_path.is_file():
                raise FileNotFoundError(
                    f"{group_name}.{label} points to a missing file: {artifact_path}"
                )

            actual_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_sha256 != sha256:
                raise ValueError(
                    f"{group_name}.{label} sha256 mismatch: expected {sha256}, got {actual_sha256}"
                )


def normalize_binary_response(response: object) -> tuple[str, ...] | None:
    if isinstance(response, BinaryResponse):
        return response.as_tuple()

    if isinstance(response, str):
        parsed = parse_binary_output(response)
        if parsed.status is ParseStatus.VALID:
            return tuple(label.value for label in parsed.labels)

    return None


def normalize_narrative_response(response: object) -> tuple[str, ...] | None:
    if isinstance(response, str):
        parsed = parse_narrative_output(response)
        if parsed.status is ParseStatus.VALID:
            return tuple(label.value for label in parsed.labels)

    return None


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


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a mapping")
    return value


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

    # Convert to lists for efficient indexing
    nc = list(num_correct)
    tot = list(total)
    grand_total_probes = sum(tot)

    if grand_total_probes == 0:
        return ConfidenceInterval(0.0, 0.0, 0.0, level, 0.0)

    grand_mean = sum(nc) / grand_total_probes

    # Deterministic bootstrap
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

    # Clamp indices
    lower_idx = max(0, min(lower_idx, n_bootstraps - 1))
    upper_idx = max(0, min(upper_idx, n_bootstraps - 1))

    lower = means[lower_idx]
    upper = means[upper_idx]
    
    # Report the larger side as the margin for conservatism
    margin = max(grand_mean - lower, upper - grand_mean)

    return ConfidenceInterval(
        mean=grand_mean,
        lower=lower,
        upper=upper,
        level=level,
        margin=margin,
    )


def validate_kaggle_payload(payload: dict[str, object]) -> None:
    """Validates the canonical Kaggle benchmark payload structure.

    Fails hard if the payload is malformed, missing required fields, has zero
    evaluated episodes, or matches the old bad kbench conversations/results/
    numericResult shape that only carried a confidenceInterval.

    Raises:
        TypeError: If payload is not a dict.
        ValueError: If required fields are absent, total_episodes is 0,
            or the payload has the old kbench shape.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    # Reject the old bad kbench shape: conversations/results/numericResult with only CI.
    if "conversations" in payload or "results" in payload:
        raise ValueError(
            "Payload has the old kbench conversations/results/numericResult shape. "
            "Use build_kaggle_payload() to produce the canonical result structure."
        )

    if "primary_result" not in payload:
        raise ValueError("payload must contain 'primary_result'")

    primary = payload["primary_result"]
    if not isinstance(primary, dict):
        raise ValueError("primary_result must be a dict")

    _REQUIRED_PR: frozenset[str] = frozenset(
        {"score", "numerator", "denominator", "total_episodes", "confidence_interval"}
    )
    missing_pr = _REQUIRED_PR - set(primary.keys())
    if missing_pr:
        raise ValueError(
            f"primary_result is missing required fields: {sorted(missing_pr)}"
        )

    if primary["total_episodes"] == 0:
        raise ValueError(
            "primary_result.total_episodes is 0; "
            "evaluation output is missing or empty — do not substitute zeros"
        )

    if primary["denominator"] == 0:
        raise ValueError(
            "primary_result.denominator is 0; evaluation output is malformed"
        )

    ci = primary["confidence_interval"]
    if not isinstance(ci, dict):
        raise ValueError("primary_result.confidence_interval must be a dict")

    _REQUIRED_CI: frozenset[str] = frozenset({"mean", "lower", "upper", "level", "margin"})
    missing_ci = _REQUIRED_CI - set(ci.keys())
    if missing_ci:
        raise ValueError(
            f"confidence_interval is missing required fields: {sorted(missing_ci)}"
        )

    for placeholder in ("narrative_result", "comparison", "slices"):
        if placeholder not in payload:
            raise ValueError(f"payload must contain '{placeholder}' placeholder")

    if "metadata" not in payload:
        raise ValueError("payload must contain 'metadata'")


def build_kaggle_payload(
    binary_df: Any,
    narrative_df: Any | None = None,
) -> dict[str, object]:
    """Constructs the canonical final Kaggle payload from task results.

    Args:
        binary_df: pandas DataFrame containing 'num_correct' and 'total' columns.
        narrative_df: Optional pandas DataFrame for narrative results (MR-2 placeholder).

    Returns:
        A dictionary representing the JSON payload to be emitted.
    
    Raises:
        ValueError: If binary_df is empty or missing required columns.
        ImportError: If pandas is not available.
        TypeError: If binary_df is not a pandas DataFrame.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for build_kaggle_payload")

    if not isinstance(binary_df, pd.DataFrame):
        raise TypeError("binary_df must be a pandas DataFrame")

    if binary_df.empty:
        raise ValueError("binary_df cannot be empty; evaluation results are required")

    if "num_correct" not in binary_df.columns or "total" not in binary_df.columns:
        raise ValueError(
            "binary_df must contain 'num_correct' and 'total' columns"
        )

    # Compute aggregate metrics
    bin_num = int(binary_df["num_correct"].sum())
    bin_den = int(binary_df["total"].sum())
    bin_episodes = len(binary_df)

    # Compute bootstrap CI
    bin_ci = compute_bootstrap_confidence_interval(
        binary_df["num_correct"].tolist(),
        binary_df["total"].tolist(),
    )

    # Narrative placeholder (MR-1: Explicitly None as per requirement)
    # "Binary vs Narrative comparison field or summary hook... leave a stable placeholder"
    narrative_result = None

    # Comparison placeholder (MR-2)
    comparison = None

    # Slices placeholder
    slices: dict[str, object] = {}

    return {
        "primary_result": {
            "score": bin_ci.mean,
            "numerator": bin_num,
            "denominator": bin_den,
            "total_episodes": bin_episodes,
            "confidence_interval": {
                "mean": bin_ci.mean,
                "lower": bin_ci.lower,
                "upper": bin_ci.upper,
                "level": bin_ci.level,
                "margin": bin_ci.margin,
            },
        },
        "narrative_result": narrative_result,
        "comparison": comparison,
        "slices": slices,
        "metadata": {
            "benchmark_version": MANIFEST_VERSION,
        },
    }
