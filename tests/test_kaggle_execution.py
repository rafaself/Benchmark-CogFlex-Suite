from __future__ import annotations

from dataclasses import dataclass, fields

import pytest

from core.kaggle import KaggleExecutionError, load_leaderboard_dataframe, run_binary_task
from core.kaggle.runner import BinaryResponse, Label


class _RaisingLLM:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def prompt(self, *_args, **_kwargs):
        raise self._exc


class _StringLLM:
    def prompt(self, *_args, **_kwargs):
        return "attract, repel, attract, repel"


class _MappingLLM:
    def prompt(self, *_args, **_kwargs):
        return {
            "probe_6": "attract",
            "probe_7": "repel",
            "probe_8": "attract",
            "probe_9": "repel",
        }


def test_run_binary_task_scores_string_and_mapping_responses():
    targets = ("attract", "repel", "attract", "repel")

    assert run_binary_task(
        llm=_StringLLM(),
        prompt_binary="prompt",
        probe_targets=targets,
    ) == (4, 4)
    assert run_binary_task(
        llm=_MappingLLM(),
        prompt_binary="prompt",
        probe_targets=targets,
    ) == (4, 4)


def test_run_binary_task_raises_for_non_scoreable_response():
    @dataclass(frozen=True)
    class _BadShapeLLM:
        def prompt(self, *_args, **_kwargs):
            return {"unexpected": 1}

    targets = ("attract", "repel", "attract", "repel")

    with pytest.raises(
        KaggleExecutionError,
        match=r"unscoreable response of type dict",
    ):
        run_binary_task(
            llm=_BadShapeLLM(),
            prompt_binary="prompt",
            probe_targets=targets,
        )


def test_binary_response_uses_concrete_label_field_types():
    assert [field.type for field in fields(BinaryResponse)] == [Label, Label, Label, Label]


def test_run_binary_task_surfaces_provider_exception():
    targets = ("attract", "repel", "attract", "repel")

    with pytest.raises(KaggleExecutionError, match="llm.prompt failed"):
        run_binary_task(
            llm=_RaisingLLM(RuntimeError("provider unavailable")),
            prompt_binary="prompt",
            probe_targets=targets,
        )


def test_run_binary_task_surfaces_timeout_like_failure():
    targets = ("attract", "repel", "attract", "repel")

    with pytest.raises(KaggleExecutionError, match="llm.prompt failed"):
        run_binary_task(
            llm=_RaisingLLM(TimeoutError("provider timeout")),
            prompt_binary="prompt",
            probe_targets=targets,
        )


def test_load_leaderboard_dataframe_preserves_public_private_behavior(monkeypatch):
    private_root, frozen_splits, leaderboard_df = load_leaderboard_dataframe()

    assert private_root is not None
    assert set(frozen_splits) == {"public_leaderboard", "private_leaderboard"}
    assert set(leaderboard_df["split"]) == {"public_leaderboard", "private_leaderboard"}

    monkeypatch.delenv("RULESHIFT_PRIVATE_DATASET_ROOT", raising=False)
    private_root, frozen_splits, leaderboard_df = load_leaderboard_dataframe()

    assert private_root is None
    assert set(frozen_splits) == {"public_leaderboard"}
    assert set(leaderboard_df["split"]) == {"public_leaderboard"}
