from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from core.kaggle.types import compute_bootstrap_confidence_interval
from core.slices import SLICE_DIMENSIONS, ErrorType, SliceReport
from core.splits import MANIFEST_VERSION

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "REQUIRED_SLICE_DIMENSIONS",
    "build_kaggle_payload",
    "normalize_count_result_df",
    "validate_kaggle_payload",
]

REQUIRED_SLICE_DIMENSIONS: Final[tuple[str, ...]] = SLICE_DIMENSIONS

_SLICE_METADATA_COLS: Final[dict[str, str]] = {
    "template": "template_id",
    "template_family": "template_family",
    "difficulty": "difficulty",
    "shift_position": "shift_position",
    "transition_type": "transition_type",
}


def validate_kaggle_payload(payload: dict[str, object]) -> None:
    """Validates the canonical Kaggle benchmark payload structure.

    Fails hard if the payload is malformed, missing required fields, has zero
    evaluated episodes, is missing Narrative results, or matches the old bad
    kbench conversations/results/numericResult shape.

    Raises:
        TypeError: If payload is not a dict.
        ValueError: If required fields are absent, total_episodes is 0,
            narrative_result or comparison is missing/None/malformed,
            episode_count_aligned is not True, or the payload has the old kbench shape.
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

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

    if "narrative_result" not in payload:
        raise ValueError("payload must contain 'narrative_result'")
    narrative = payload["narrative_result"]
    if narrative is None:
        raise ValueError(
            "narrative_result is None; Narrative evaluation is mandatory for a valid release"
        )
    if not isinstance(narrative, dict):
        raise ValueError("narrative_result must be a dict")
    _REQUIRED_NR: frozenset[str] = frozenset(
        {"score", "numerator", "denominator", "total_episodes", "confidence_interval"}
    )
    missing_nr = _REQUIRED_NR - set(narrative.keys())
    if missing_nr:
        raise ValueError(
            f"narrative_result is missing required fields: {sorted(missing_nr)}"
        )
    if narrative["total_episodes"] == 0:
        raise ValueError(
            "narrative_result.total_episodes is 0; "
            "Narrative evaluation output is missing or empty"
        )
    if narrative["denominator"] == 0:
        raise ValueError(
            "narrative_result.denominator is 0; Narrative evaluation output is malformed"
        )
    nar_ci = narrative["confidence_interval"]
    if not isinstance(nar_ci, dict):
        raise ValueError("narrative_result.confidence_interval must be a dict")
    missing_nar_ci = _REQUIRED_CI - set(nar_ci.keys())
    if missing_nar_ci:
        raise ValueError(
            f"narrative_result.confidence_interval is missing required fields: {sorted(missing_nar_ci)}"
        )

    if "comparison" not in payload:
        raise ValueError("payload must contain 'comparison'")
    comparison = payload["comparison"]
    if comparison is None:
        raise ValueError(
            "comparison is None; Binary vs Narrative comparison is mandatory for a valid release"
        )
    if not isinstance(comparison, dict):
        raise ValueError("comparison must be a dict")
    _REQUIRED_COMP: frozenset[str] = frozenset(
        {
            "binary_score",
            "narrative_score",
            "delta",
            "episode_count_aligned",
            "binary_total_episodes",
            "narrative_total_episodes",
        }
    )
    missing_comp = _REQUIRED_COMP - set(comparison.keys())
    if missing_comp:
        raise ValueError(
            f"comparison is missing required fields: {sorted(missing_comp)}"
        )
    if comparison["episode_count_aligned"] is not True:
        raise ValueError(
            "comparison.episode_count_aligned is not True; "
            "Binary and Narrative must evaluate the same frozen episodes"
        )

    if "slices" not in payload:
        raise ValueError("payload must contain 'slices'")
    slices_val = payload["slices"]
    if not isinstance(slices_val, dict):
        raise ValueError("slices must be a dict")
    for dim in REQUIRED_SLICE_DIMENSIONS:
        if dim not in slices_val:
            raise ValueError(f"slices is missing required dimension: {dim!r}")

    if "metadata" not in payload:
        raise ValueError("payload must contain 'metadata'")


def build_kaggle_payload(
    binary_df: Any,
    narrative_df: Any,
    *,
    slice_report: SliceReport | None = None,
) -> dict[str, object]:
    """Constructs the canonical final Kaggle payload from task results.

    Both Binary and Narrative results are required for a valid release.
    Fails hard if narrative_df is None, empty, mismatched in episode count,
    or mismatched in denominator basis.

    Args:
        binary_df: pandas DataFrame containing count-based task results in one
            of the supported shapes: canonical ``num_correct``/``total``,
            Kaggle SDK ``result`` tuples, or legacy ``score_0``/``score_1`` /
            ``0``/``1`` columns.
        narrative_df: pandas DataFrame containing count-based task results in
            one of the supported shapes: canonical ``num_correct``/``total``,
            Kaggle SDK ``result`` tuples, or legacy ``score_0``/``score_1`` /
            ``0``/``1`` columns. Must align with binary_df on episode count
            and total denominator.

    Returns:
        A dictionary representing the JSON payload to be emitted, including
        primary_result, narrative_result, comparison, slices, and metadata.

    Raises:
        ValueError: If binary_df or narrative_df is missing, empty, or misaligned.
        ImportError: If pandas is not available.
        TypeError: If binary_df or narrative_df is not a pandas DataFrame.
    """
    binary_df = normalize_count_result_df(binary_df, dataframe_label="binary_df")
    if binary_df.empty:
        raise ValueError("binary_df cannot be empty; evaluation results are required")

    if "num_correct" not in binary_df.columns or "total" not in binary_df.columns:
        raise ValueError(
            "binary_df must contain 'num_correct' and 'total' columns"
        )

    _reject_dev_rows(binary_df, "binary_df")

    if narrative_df is None:
        raise ValueError(
            "narrative_df is required for a valid release; "
            "Narrative evaluation is missing or was skipped"
        )

    narrative_df = normalize_count_result_df(
        narrative_df,
        dataframe_label="narrative_df",
    )
    if narrative_df.empty:
        raise ValueError(
            "narrative_df cannot be empty; Narrative evaluation results are required"
        )

    if "num_correct" not in narrative_df.columns or "total" not in narrative_df.columns:
        raise ValueError(
            "narrative_df must contain 'num_correct' and 'total' columns"
        )

    _reject_dev_rows(narrative_df, "narrative_df")

    bin_episodes = len(binary_df)
    nar_episodes = len(narrative_df)
    if bin_episodes != nar_episodes:
        raise ValueError(
            f"Binary and Narrative episode counts do not match: "
            f"binary={bin_episodes}, narrative={nar_episodes}. "
            "Both must evaluate the same frozen episodes."
        )

    bin_den = int(binary_df["total"].sum())
    nar_den = int(narrative_df["total"].sum())
    if bin_den != nar_den:
        raise ValueError(
            f"Binary and Narrative denominators do not match: "
            f"binary={bin_den}, narrative={nar_den}. "
            "Both must use the same probe count basis."
        )

    bin_num = int(binary_df["num_correct"].sum())
    bin_ci = compute_bootstrap_confidence_interval(
        binary_df["num_correct"].tolist(),
        binary_df["total"].tolist(),
    )

    nar_num = int(narrative_df["num_correct"].sum())
    nar_ci = compute_bootstrap_confidence_interval(
        narrative_df["num_correct"].tolist(),
        narrative_df["total"].tolist(),
    )

    payload: dict[str, object] = {
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
        "narrative_result": {
            "score": nar_ci.mean,
            "numerator": nar_num,
            "denominator": nar_den,
            "total_episodes": nar_episodes,
            "confidence_interval": {
                "mean": nar_ci.mean,
                "lower": nar_ci.lower,
                "upper": nar_ci.upper,
                "level": nar_ci.level,
                "margin": nar_ci.margin,
            },
        },
        "comparison": {
            "binary_score": bin_ci.mean,
            "narrative_score": nar_ci.mean,
            "delta": bin_ci.mean - nar_ci.mean,
            "episode_count_aligned": True,
            "binary_total_episodes": bin_episodes,
            "narrative_total_episodes": nar_episodes,
            "binary_denominator": bin_den,
            "narrative_denominator": nar_den,
        },
        "slices": (
            slice_report.to_dict()
            if slice_report is not None
            else _build_payload_slices(binary_df)
        ),
        "metadata": {
            "benchmark_version": MANIFEST_VERSION,
        },
    }

    return payload


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def normalize_count_result_df(
    df: "pd.DataFrame",
    *,
    dataframe_label: str = "result_df",
) -> "pd.DataFrame":
    """Normalizes count-based result DataFrames to ``num_correct`` / ``total``.

    Supported input shapes:
    - canonical ``num_correct`` / ``total`` columns
    - Kaggle SDK ``result`` column with 2-item tuple/list values
    - legacy ``score_0`` / ``score_1`` columns
    - integer ``0`` / ``1`` columns

    Non-result metadata columns are preserved. The returned DataFrame is always
    a copy of the input.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for normalize_count_result_df")

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{dataframe_label} must be a pandas DataFrame")

    out = df.copy()

    if "num_correct" in out.columns and "total" in out.columns:
        return out

    if "result" in out.columns:
        invalid_mask = ~out["result"].map(
            lambda value: isinstance(value, (tuple, list)) and len(value) == 2
        )
        if invalid_mask.any():
            raise ValueError(
                f"{dataframe_label}.result must contain 2-item tuple/list values"
            )

        if out.empty:
            out = out.drop(columns=["result"])
            out["num_correct"] = pd.Series(index=out.index, dtype="object")
            out["total"] = pd.Series(index=out.index, dtype="object")
            return out

        expanded = pd.DataFrame(out["result"].tolist(), index=out.index)
        out[["num_correct", "total"]] = expanded
        return out.drop(columns=["result"])

    if "score_0" in out.columns and "score_1" in out.columns:
        return out.rename(columns={"score_0": "num_correct", "score_1": "total"})

    if 0 in out.columns and 1 in out.columns:
        return out.rename(columns={0: "num_correct", 1: "total"})

    return out


def _reject_dev_rows(df: Any, label: str) -> None:
    if "split" not in df.columns:
        return
    dev_count = int((df["split"] == "dev").sum())
    if dev_count > 0:
        raise ValueError(
            f"{label} contains {dev_count} dev row(s); "
            "only leaderboard results may be aggregated into the official payload. "
            "Drop the dev split before calling build_kaggle_payload."
        )


def _build_payload_slices(binary_df: Any) -> dict[str, object]:
    slices: dict[str, object] = {}

    for dim, col in _SLICE_METADATA_COLS.items():
        if col in binary_df.columns:
            slices[dim] = _accuracy_by_column(binary_df, col)
        else:
            slices[dim] = {}

    slices["error_type"] = _error_type_counts(binary_df)
    return slices


def _accuracy_by_column(df: Any, col: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for value, group in df.groupby(col, sort=True):
        nc = int(group["num_correct"].sum())
        tot = int(group["total"].sum())
        result[str(value)] = {
            "episode_count": len(group),
            "correct_probes": nc,
            "total_probes": tot,
            "accuracy": nc / tot if tot > 0 else 0.0,
        }
    return result


def _error_type_counts(df: Any) -> dict[str, int]:
    counts: dict[str, int] = {et.value: 0 for et in ErrorType}
    for _, row in df.iterrows():
        nc = int(row["num_correct"])
        total = int(row["total"])
        if nc >= total:
            continue
        if nc == 0:
            counts[ErrorType.OLD_RULE_PERSISTENCE.value] += 1
        else:
            counts[ErrorType.PREMATURE_SWITCH.value] += 1
    return counts
