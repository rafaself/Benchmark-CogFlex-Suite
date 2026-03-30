from __future__ import annotations

from core.kaggle.runner import normalize_binary_response, score_episode


def test_empty_output_is_scored_as_wrong_answer():
    targets = ("attract", "repel", "attract", "repel")

    parsed = normalize_binary_response("")

    assert parsed is None
    assert score_episode(parsed, targets) == (0, 4)


def test_malformed_but_still_scoreable_output_is_preserved():
    targets = ("attract", "repel", "attract", "repel")

    parsed = normalize_binary_response("`attract\nrepel\nattract\nrepel`")

    assert parsed == targets
    assert score_episode(parsed, targets) == (4, 4)

