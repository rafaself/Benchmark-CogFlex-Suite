import pandas as pd
import pytest

from core.kaggle import (
    build_kaggle_payload,
    compute_bootstrap_confidence_interval,
    normalize_count_result_df,
    validate_kaggle_payload,
)
from core.slices import EpisodeSliceData, ErrorType, build_slice_report


def _make_binary_df(rows: list[dict] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows or [{"num_correct": 3, "total": 4}] * 4)


def _make_narrative_df(rows: list[dict] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows or [{"num_correct": 2, "total": 4}] * 4)


def test_compute_bootstrap_confidence_interval_is_deterministic_and_valid():
    num_correct = [3, 4, 2, 4, 1] * 10
    total = [4] * 50

    left = compute_bootstrap_confidence_interval(num_correct, total, seed=2025)
    right = compute_bootstrap_confidence_interval(num_correct, total, seed=2025)

    assert left == right
    assert left.lower <= left.mean <= left.upper
    assert left.margin >= 0.0


def test_normalize_count_result_df_supports_runtime_input_shapes():
    tuple_df = pd.DataFrame([{"result": (3, 4), "difficulty": "easy"}])
    legacy_df = pd.DataFrame([{"score_0": 3, "score_1": 4}])
    indexed_df = pd.DataFrame([{0: 3, 1: 4}])

    normalized_tuple = normalize_count_result_df(tuple_df)
    normalized_legacy = normalize_count_result_df(legacy_df)
    normalized_indexed = normalize_count_result_df(indexed_df)

    assert normalized_tuple.loc[0, "num_correct"] == 3
    assert normalized_tuple.loc[0, "total"] == 4
    assert normalized_tuple.loc[0, "difficulty"] == "easy"
    assert normalized_legacy.loc[0, "num_correct"] == 3
    assert normalized_legacy.loc[0, "total"] == 4
    assert normalized_indexed.loc[0, "num_correct"] == 3
    assert normalized_indexed.loc[0, "total"] == 4


def test_build_kaggle_payload_emits_canonical_contract():
    slice_report = build_slice_report(
        (
            EpisodeSliceData(
                episode_id="ep-1",
                template="T1",
                template_family="canonical",
                difficulty="easy",
                shift_position="2",
                transition_type="R_std_to_R_inv",
                error_type=ErrorType.OLD_RULE_PERSISTENCE,
                correct_probes=0,
                total_probes=4,
            ),
            EpisodeSliceData(
                episode_id="ep-2",
                template="T2",
                template_family="observation_log",
                difficulty="medium",
                shift_position="3",
                transition_type="R_inv_to_R_std",
                error_type=ErrorType.PREMATURE_SWITCH,
                correct_probes=2,
                total_probes=4,
            ),
        )
    )

    payload = build_kaggle_payload(_make_binary_df(), _make_narrative_df(), slice_report=slice_report)
    validate_kaggle_payload(payload)

    assert payload["primary_result"]["numerator"] == 12
    assert payload["primary_result"]["denominator"] == 16
    assert payload["primary_result"]["total_episodes"] == 4
    assert payload["narrative_result"]["total_episodes"] == 4
    assert payload["comparison"]["episode_count_aligned"] is True
    assert payload["slices"] == slice_report.to_dict()
    assert payload["metadata"]["benchmark_version"] is not None


def test_build_kaggle_payload_rejects_dev_rows_and_alignment_mismatches():
    with pytest.raises(ValueError, match="dev row"):
        build_kaggle_payload(
            _make_binary_df([{"num_correct": 3, "total": 4, "split": "dev"}]),
            _make_narrative_df(),
        )

    with pytest.raises(ValueError, match="episode counts do not match"):
        build_kaggle_payload(_make_binary_df(), _make_narrative_df([{"num_correct": 2, "total": 4}] * 3))

    with pytest.raises(ValueError, match="denominators do not match"):
        build_kaggle_payload(_make_binary_df(), _make_narrative_df([{"num_correct": 2, "total": 6}] * 4))


def test_validate_kaggle_payload_rejects_old_or_incomplete_shapes():
    payload = build_kaggle_payload(_make_binary_df(), _make_narrative_df())

    with pytest.raises(ValueError, match="old kbench"):
        validate_kaggle_payload({"results": [{"numericResult": {"confidenceInterval": {}}}]})

    with pytest.raises(ValueError, match="narrative_result is None"):
        validate_kaggle_payload({**payload, "narrative_result": None})

    with pytest.raises(ValueError, match="episode_count_aligned is not True"):
        validate_kaggle_payload(
            {**payload, "comparison": {**payload["comparison"], "episode_count_aligned": False}}
        )
