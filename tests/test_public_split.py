from __future__ import annotations

from collections import Counter
from itertools import combinations

from core.splits import load_frozen_split, load_split_manifest
from tasks.ruleshift_benchmark.render import render_binary_prompt


def test_public_leaderboard_manifest_freezes_exactly_54_episodes():
    manifest = load_split_manifest("public_leaderboard")
    records = load_frozen_split("public_leaderboard")

    assert manifest.seed_bank_version == "R14-public-5"
    assert len(manifest.seeds) == 54
    assert len(records) == 54
    assert tuple(range(16524, 16578)) == manifest.seeds


def test_public_leaderboard_is_structurally_balanced_for_audit():
    records = load_frozen_split("public_leaderboard")
    episodes = [record.episode for record in records]

    assert Counter(episode.difficulty.value for episode in episodes) == {
        "easy": 18,
        "medium": 18,
        "hard": 18,
    }
    assert Counter(episode.transition.value for episode in episodes) == {
        "R_std_to_R_inv": 27,
        "R_inv_to_R_std": 27,
    }
    assert Counter(episode.template_family.value for episode in episodes) == {
        "canonical": 18,
        "observation_log": 18,
        "case_ledger": 18,
    }
    assert Counter(episode.template_id.value for episode in episodes) == {
        "T1": 18,
        "T2": 18,
        "T3": 18,
    }

    combo_counts = Counter(
        (
            episode.difficulty.value,
            episode.transition.value,
            episode.template_family.value,
            episode.template_id.value,
        )
        for episode in episodes
    )
    assert len(combo_counts) == 54
    assert set(combo_counts.values()) == {1}


def test_public_leaderboard_has_no_exact_prompt_or_episode_duplicates():
    records = load_frozen_split("public_leaderboard")
    prompts = [render_binary_prompt(record.episode) for record in records]
    fingerprints = [
        (
            record.episode.difficulty.value,
            record.episode.transition.value,
            record.episode.template_family.value,
            record.episode.template_id.value,
            tuple(
                (item.q1, item.q2, getattr(item.label, "value", None))
                for item in record.episode.items
            ),
            tuple(target.value for target in record.episode.probe_targets),
        )
        for record in records
    ]

    assert len(prompts) == len(set(prompts))
    assert len(fingerprints) == len(set(fingerprints))


def test_public_leaderboard_pair_overlap_stays_below_near_duplicate_threshold():
    records = load_frozen_split("public_leaderboard")
    pair_sets = [
        {(item.q1, item.q2) for item in record.episode.items}
        for record in records
    ]

    max_overlap = max(
        len(pair_sets[i] & pair_sets[j])
        for i, j in combinations(range(len(pair_sets)), 2)
    )

    assert max_overlap <= 6
