from __future__ import annotations

import random

from protocol import CASE_SPACE, LABELED_ITEM_COUNT, ItemKind, Phase, RuleName, TemplateId, TEMPLATES
from rules import label
from schema import Episode, EpisodeItem

RULE_CHOICES: tuple[RuleName, ...] = (RuleName.R_STD, RuleName.R_INV)
TEMPLATE_CHOICES: tuple[TemplateId, ...] = (TemplateId.T1, TemplateId.T2)


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def generate_episode(seed: int) -> Episode:
    if not _is_plain_int(seed):
        raise TypeError("seed must be an int")

    rng = random.Random(seed)
    rule_a = rng.choice(RULE_CHOICES)
    rule_b = rule_a.opposite
    template_id = rng.choice(TEMPLATE_CHOICES)
    template = TEMPLATES[template_id]
    sampled_pairs = rng.sample(CASE_SPACE, k=template.total_items)

    items: list[EpisodeItem] = []
    for position, (q1, q2) in enumerate(sampled_pairs, start=1):
        if position <= template.pre_count:
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

    return Episode(
        episode_id=f"ife-r2-{seed}",
        template_id=template_id,
        rule_A=rule_a,
        rule_B=rule_b,
        pre_count=template.pre_count,
        post_labeled_count=template.post_labeled_count,
        shift_after_position=template.shift_after_position,
        items=tuple(items),
    )
