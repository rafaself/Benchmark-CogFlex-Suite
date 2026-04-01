from __future__ import annotations

import pandas as pd

from core.kaggle.audit import (
    AUDIT_BALANCE_DIMENSIONS,
    AUDIT_CATALOG_COLUMNS,
    AUDIT_FAILURE_COLUMNS,
    build_audit_balance,
    build_audit_catalog,
    build_audit_failures,
)
from core.splits import load_frozen_split


def test_build_audit_catalog_has_one_row_per_public_episode_and_required_fields():
    public_records = load_frozen_split("public_leaderboard")

    audit_catalog = build_audit_catalog(public_records)

    assert list(audit_catalog.columns) == list(AUDIT_CATALOG_COLUMNS)
    assert len(audit_catalog) == len(public_records)
    assert audit_catalog["episode_id"].is_unique
    assert set(audit_catalog["split"]) == {"public_leaderboard"}
    assert set(audit_catalog["difficulty"]) <= {"easy", "medium", "hard"}
    assert set(audit_catalog["template_family"]) <= {
        "canonical",
        "observation_log",
        "case_ledger",
    }


def test_build_audit_balance_summarizes_each_dimension_over_public_catalog():
    audit_catalog = build_audit_catalog(load_frozen_split("public_leaderboard"))

    audit_balance = build_audit_balance(audit_catalog)

    assert set(audit_balance["dimension"]) == set(AUDIT_BALANCE_DIMENSIONS)
    for dimension in AUDIT_BALANCE_DIMENSIONS:
        dimension_view = audit_balance[audit_balance["dimension"] == dimension]
        assert int(dimension_view["episodes"].sum()) == len(audit_catalog)
        assert all(value == dimension for value in dimension_view["dimension"])


def test_build_audit_failures_joins_public_results_with_audit_metadata_only():
    audit_catalog = build_audit_catalog(load_frozen_split("public_leaderboard"))
    public_row = audit_catalog.iloc[0]
    private_like_row = {
        "episode_id": "private-episode",
        "split": "private_leaderboard",
        "num_correct": 0,
        "total": 4,
    }
    binary_df = pd.DataFrame(
        [
            {
                "episode_id": public_row["episode_id"],
                "split": public_row["split"],
                "num_correct": 1,
                "total": 4,
            },
            private_like_row,
        ]
    )

    audit_failures = build_audit_failures(binary_df, audit_catalog)

    assert list(audit_failures.columns) == list(AUDIT_FAILURE_COLUMNS)
    assert len(audit_failures) == 1
    assert audit_failures.loc[0, "episode_id"] == public_row["episode_id"]
    assert audit_failures.loc[0, "split"] == "public_leaderboard"
    assert audit_failures.loc[0, "missed"] == 3
    assert audit_failures.loc[0, "difficulty"] == public_row["difficulty"]
    assert audit_failures.loc[0, "transition"] == public_row["transition"]


def test_build_audit_failures_returns_empty_frame_with_expected_columns_when_no_public_failures():
    audit_catalog = build_audit_catalog(load_frozen_split("public_leaderboard"))
    binary_df = pd.DataFrame(
        [
            {
                "episode_id": audit_catalog.iloc[0]["episode_id"],
                "split": "public_leaderboard",
                "num_correct": 4,
                "total": 4,
            }
        ]
    )

    audit_failures = build_audit_failures(binary_df, audit_catalog)

    assert audit_failures.empty
    assert list(audit_failures.columns) == list(AUDIT_FAILURE_COLUMNS)
