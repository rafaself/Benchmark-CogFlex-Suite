from __future__ import annotations

import random

from protocol import (
    CASE_SPACE,
    LABELED_ITEM_COUNT,
    Difficulty,
    ItemKind,
    Phase,
    RuleName,
    Split,
    TemplateId,
    TEMPLATES,
    Transition,
)
from rules import label
from schema import Episode, EpisodeItem, ProbeMetadata

RULE_CHOICES: tuple[RuleName, ...] = (RuleName.R_STD, RuleName.R_INV)
TEMPLATE_CHOICES: tuple[TemplateId, ...] = (TemplateId.T1, TemplateId.T2)


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _build_items(
    sampled_pairs: tuple[tuple[int, int], ...],
    pre_count: int,
    rule_a: RuleName,
    rule_b: RuleName,
) -> tuple[EpisodeItem, ...]:
    items: list[EpisodeItem] = []
    for position, (q1, q2) in enumerate(sampled_pairs, start=1):
        if position <= pre_count:
            active_rule = rule_a
            phase = Phase.PRE
            kind = ItemKind.LABELED
            item_label = label(active_rule, q1, q2)
        elif position <= LABELED_ITEM_COUNT:
            active_rule = rule_b
            phase = Phase.POST
            kind = ItemKind.LABELED
            item_label = label(active_rule, q1, q2)
        else:
            phase = Phase.POST
            kind = ItemKind.PROBE
            item_label = None

        items.append(
            EpisodeItem(
                position=position,
                phase=phase,
                kind=kind,
                q1=q1,
                q2=q2,
                label=item_label,
            )
        )

    return tuple(items)


def _build_probe_targets(
    items: tuple[EpisodeItem, ...],
    rule_b: RuleName,
) -> tuple:
    return tuple(label(rule_b, item.q1, item.q2) for item in items[LABELED_ITEM_COUNT:])


def _build_probe_metadata(
    items: tuple[EpisodeItem, ...],
    rule_a: RuleName,
    rule_b: RuleName,
) -> tuple[ProbeMetadata, ...]:
    probe_items = items[LABELED_ITEM_COUNT:]
    return tuple(
        ProbeMetadata(
            position=item.position,
            is_disagreement_probe=label(RuleName.R_STD, item.q1, item.q2)
            != label(RuleName.R_INV, item.q1, item.q2),
            old_rule_label=label(rule_a, item.q1, item.q2),
            new_rule_label=label(rule_b, item.q1, item.q2),
        )
        for item in probe_items
    )


def _assign_difficulty(template_id: TemplateId, probe_targets: tuple) -> Difficulty:
    attract_count = sum(target.value == "attract" for target in probe_targets)
    repel_count = len(probe_targets) - attract_count
    balance = min(attract_count, repel_count)

    if template_id is TemplateId.T1 and balance == 2:
        return Difficulty.EASY
    if balance == 2:
        return Difficulty.MEDIUM
    return Difficulty.HARD


def generate_episode(seed: int, split: Split | str = Split.DEV) -> Episode:
    if not _is_plain_int(seed):
        raise TypeError("seed must be an int")

    rng = random.Random(seed)
    rule_a = rng.choice(RULE_CHOICES)
    rule_b = rule_a.opposite
    template_id = rng.choice(TEMPLATE_CHOICES)
    template = TEMPLATES[template_id]

    while True:
        sampled_pairs = tuple(rng.sample(CASE_SPACE, k=template.total_items))
        items = _build_items(sampled_pairs, template.pre_count, rule_a, rule_b)
        probe_targets = _build_probe_targets(items, rule_b)
        if len(set(probe_targets)) >= 2:
            break

    probe_metadata = _build_probe_metadata(items, rule_a, rule_b)

    return Episode(
        episode_id=f"ife-r2-{seed}",
        split=split,
        difficulty=_assign_difficulty(template_id, probe_targets),
        template_id=template_id,
        rule_A=rule_a,
        rule_B=rule_b,
        transition=Transition.from_rules(rule_a, rule_b),
        pre_count=template.pre_count,
        post_labeled_count=template.post_labeled_count,
        shift_after_position=template.shift_after_position,
        items=items,
        probe_targets=probe_targets,
        probe_metadata=probe_metadata,
    )
