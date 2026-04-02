"""Audit views for notebook-side episode inspection.

Shipped in the public runtime package but not part of the official
Kaggle contract payload. These views are derived from public_leaderboard
episodes and displayed in the notebook for catalog, balance, and failure
analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    import pandas as pd

AUDIT_CATALOG_COLUMNS: Final[tuple[str, ...]] = (
    "episode_id",
    "split",
    "difficulty",
    "transition",
    "template_family",
    "template_id",
    "difficulty_profile_id",
    "pre_count",
    "post_labeled_count",
    "contradiction_count_post",
)
AUDIT_BALANCE_DIMENSIONS: Final[tuple[str, ...]] = (
    "difficulty",
    "transition",
    "template_family",
    "template_id",
)
AUDIT_FAILURE_COLUMNS: Final[tuple[str, ...]] = (
    "episode_id",
    "split",
    "difficulty",
    "transition",
    "template_family",
    "template_id",
    "num_correct",
    "total",
    "missed",
)

__all__ = [
    "AUDIT_BALANCE_DIMENSIONS",
    "AUDIT_CATALOG_COLUMNS",
    "AUDIT_FAILURE_COLUMNS",
    "build_audit_balance",
    "build_audit_catalog",
    "build_audit_failures",
]


def build_audit_catalog(public_records: Any) -> "pd.DataFrame":
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for build_audit_catalog")

    rows: list[dict[str, object]] = []
    for record in public_records:
        if record.partition != "public_leaderboard":
            raise ValueError("build_audit_catalog expects only public_leaderboard records")
        episode = record.episode
        rows.append(
            {
                "episode_id": episode.episode_id,
                "split": record.partition,
                "difficulty": episode.difficulty.value,
                "transition": episode.transition.value,
                "template_family": episode.template_family.value,
                "template_id": episode.template_id.value,
                "difficulty_profile_id": episode.difficulty_profile_id.value,
                "pre_count": episode.pre_count,
                "post_labeled_count": episode.post_labeled_count,
                "contradiction_count_post": episode.contradiction_count_post,
            }
        )

    audit_catalog = pd.DataFrame(rows, columns=AUDIT_CATALOG_COLUMNS)
    if audit_catalog["episode_id"].duplicated().any():
        raise ValueError("audit catalog episode_id values must be unique")
    return audit_catalog


def build_audit_balance(audit_catalog: "pd.DataFrame") -> "pd.DataFrame":
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for build_audit_balance")

    _validate_audit_catalog(audit_catalog)

    views: list["pd.DataFrame"] = []
    for dimension in AUDIT_BALANCE_DIMENSIONS:
        dimension_view = (
            audit_catalog.groupby(dimension, dropna=False)
            .size()
            .reset_index(name="episodes")
            .rename(columns={dimension: "value"})
        )
        dimension_view.insert(0, "dimension", dimension)
        views.append(dimension_view[["dimension", "value", "episodes"]])

    if not views:
        return pd.DataFrame(columns=["dimension", "value", "episodes"])

    balance = pd.concat(views, ignore_index=True)
    return balance.sort_values(["dimension", "value"], ignore_index=True)


def build_audit_failures(
    binary_df: "pd.DataFrame",
    audit_catalog: "pd.DataFrame",
) -> "pd.DataFrame":
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for build_audit_failures")

    _validate_audit_catalog(audit_catalog)

    if not isinstance(binary_df, pd.DataFrame):
        raise TypeError("binary_df must be a pandas DataFrame")
    required_result_fields = {"episode_id", "split", "num_correct", "total"}
    missing = required_result_fields - set(binary_df.columns)
    if missing:
        raise ValueError(f"binary_df is missing required columns: {sorted(missing)}")

    public_results = binary_df[binary_df["split"] == "public_leaderboard"].copy()
    if public_results.empty:
        return pd.DataFrame(columns=AUDIT_FAILURE_COLUMNS)

    public_results["missed"] = public_results["total"] - public_results["num_correct"]
    failures = public_results[public_results["missed"] > 0].copy()
    if failures.empty:
        return pd.DataFrame(columns=AUDIT_FAILURE_COLUMNS)

    merged = failures.merge(
        audit_catalog,
        how="inner",
        on=["episode_id", "split"],
        validate="one_to_one",
    )
    result = merged[
        [
            "episode_id",
            "split",
            "difficulty",
            "transition",
            "template_family",
            "template_id",
            "num_correct",
            "total",
            "missed",
        ]
    ].copy()
    return result.sort_values(
        ["missed", "episode_id"],
        ascending=[False, True],
        ignore_index=True,
    )


def _validate_audit_catalog(audit_catalog: "pd.DataFrame") -> None:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for audit catalog validation")

    if not isinstance(audit_catalog, pd.DataFrame):
        raise TypeError("audit_catalog must be a pandas DataFrame")
    missing = set(AUDIT_CATALOG_COLUMNS) - set(audit_catalog.columns)
    if missing:
        raise ValueError(f"audit_catalog is missing required columns: {sorted(missing)}")
