import pandas as pd
import pytest

from core.kaggle import (
    build_kaggle_payload,
    normalize_count_result_df,
    validate_kaggle_payload,
)


def _make_binary_df(rows: list[dict] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows or [{"num_correct": 3, "total": 4}] * 4)


def test_normalize_count_result_df_supports_runtime_input_shapes():
    tuple_df = pd.DataFrame([{"result": (3, 4), "difficulty": "easy"}])
    canonical_df = pd.DataFrame([{"num_correct": 3, "total": 4, "difficulty": "easy"}])

    normalized_tuple = normalize_count_result_df(tuple_df)
    normalized_canonical = normalize_count_result_df(canonical_df)

    assert normalized_tuple.loc[0, "num_correct"] == 3
    assert normalized_tuple.loc[0, "total"] == 4
    assert normalized_tuple.loc[0, "difficulty"] == "easy"
    assert normalized_canonical.equals(canonical_df)


def test_build_kaggle_payload_emits_canonical_contract():
    payload = build_kaggle_payload(
        _make_binary_df([{"num_correct": 3, "total": 4, "split": "public_leaderboard"}] * 4)
    )
    validate_kaggle_payload(payload)

    assert payload == {
        "score": payload["score"],
        "numerator": 12,
        "denominator": 16,
        "total_episodes": 4,
        "benchmark_version": "R14",
        "split": "public_leaderboard",
        "manifest_version": "R14",
    }
    assert payload["score"] == payload["numerator"] / payload["denominator"]


def test_build_kaggle_payload_rejects_non_leaderboard_rows():
    with pytest.raises(ValueError, match="non-leaderboard split values"):
        build_kaggle_payload(
            _make_binary_df([{"num_correct": 3, "total": 4, "split": "practice"}])
        )


def test_validate_kaggle_payload_rejects_old_or_incomplete_shapes():
    payload = build_kaggle_payload(_make_binary_df())

    with pytest.raises(ValueError, match="old kbench"):
        validate_kaggle_payload({"results": [{"numericResult": {"confidenceInterval": {}}}]})

    with pytest.raises(ValueError, match="exactly these fields"):
        validate_kaggle_payload({**payload, "narrative_result": {}})

    with pytest.raises(ValueError, match="denominator is 0"):
        validate_kaggle_payload({**payload, "denominator": 0})
