from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from protocol import (
    CHARGES,
    EPISODE_LENGTH,
    LABELED_ITEM_COUNT,
    PROBE_COUNT,
    InteractionLabel,
    ItemKind,
    Phase,
    RuleName,
    TemplateId,
    TEMPLATES,
    parse_item_kind,
    parse_label,
    parse_phase,
    parse_rule,
    parse_template_id,
)

__all__ = [
    "SPEC_VERSION",
    "GENERATOR_VERSION",
    "TEMPLATE_SET_VERSION",
    "EpisodeItem",
    "Episode",
]

SPEC_VERSION: Final[str] = "v1"
GENERATOR_VERSION: Final[str] = "R2"
TEMPLATE_SET_VERSION: Final[str] = "v1"


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class EpisodeItem:
    position: int
    phase: Phase
    kind: ItemKind
    q1: int
    q2: int
    label: InteractionLabel | None = None

    def __post_init__(self) -> None:
        if not _is_plain_int(self.position):
            raise TypeError("position must be an int")
        if self.position < 1 or self.position > EPISODE_LENGTH:
            raise ValueError(f"position must be between 1 and {EPISODE_LENGTH}")

        object.__setattr__(self, "phase", parse_phase(self.phase))
        object.__setattr__(self, "kind", parse_item_kind(self.kind))

        if not _is_plain_int(self.q1):
            raise TypeError("q1 must be an int")
        if not _is_plain_int(self.q2):
            raise TypeError("q2 must be an int")
        if self.q1 not in CHARGES:
            raise ValueError(f"unsupported q1: {self.q1}")
        if self.q2 not in CHARGES:
            raise ValueError(f"unsupported q2: {self.q2}")

        if self.kind is ItemKind.LABELED:
            if self.label is None:
                raise ValueError("labeled items must include a label")
            object.__setattr__(self, "label", parse_label(self.label))
            return

        if self.phase is not Phase.POST:
            raise ValueError("probe items must use the post phase")
        if self.label is not None:
            raise ValueError("probe items must not include a label")


@dataclass(frozen=True, slots=True)
class Episode:
    episode_id: str
    template_id: TemplateId
    rule_A: RuleName
    rule_B: RuleName
    pre_count: int
    post_labeled_count: int
    shift_after_position: int
    items: tuple[EpisodeItem, ...]
    spec_version: str = SPEC_VERSION
    generator_version: str = GENERATOR_VERSION
    template_set_version: str = TEMPLATE_SET_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.episode_id, str) or not self.episode_id:
            raise ValueError("episode_id must be a non-empty string")

        object.__setattr__(self, "template_id", parse_template_id(self.template_id))
        object.__setattr__(self, "rule_A", parse_rule(self.rule_A))
        object.__setattr__(self, "rule_B", parse_rule(self.rule_B))

        if self.rule_B is not self.rule_A.opposite:
            raise ValueError("rule_B must be the opposite of rule_A")

        for field_name in ("pre_count", "post_labeled_count", "shift_after_position"):
            value = getattr(self, field_name)
            if not _is_plain_int(value):
                raise TypeError(f"{field_name} must be an int")

        template = TEMPLATES[self.template_id]
        if self.pre_count != template.pre_count:
            raise ValueError("pre_count does not match template_id")
        if self.post_labeled_count != template.post_labeled_count:
            raise ValueError("post_labeled_count does not match template_id")
        if self.shift_after_position != self.pre_count:
            raise ValueError("shift_after_position must equal pre_count")

        normalized_items = tuple(self.items)
        if len(normalized_items) != EPISODE_LENGTH:
            raise ValueError(f"items must contain exactly {EPISODE_LENGTH} entries")
        if not all(isinstance(item, EpisodeItem) for item in normalized_items):
            raise TypeError("items must contain EpisodeItem values")
        object.__setattr__(self, "items", normalized_items)

        if self.pre_count + self.post_labeled_count != LABELED_ITEM_COUNT:
            raise ValueError(
                f"pre_count + post_labeled_count must equal {LABELED_ITEM_COUNT}"
            )

        expected_positions = tuple(range(1, EPISODE_LENGTH + 1))
        actual_positions = tuple(item.position for item in normalized_items)
        if actual_positions != expected_positions:
            raise ValueError("items must use positions 1..9 in order")

        labeled_items = normalized_items[:LABELED_ITEM_COUNT]
        probe_items = normalized_items[LABELED_ITEM_COUNT:]

        if len(probe_items) != PROBE_COUNT:
            raise ValueError(f"items must contain exactly {PROBE_COUNT} probes")

        if any(item.kind is not ItemKind.LABELED for item in labeled_items):
            raise ValueError("the first 5 items must be labeled")
        if any(item.kind is not ItemKind.PROBE for item in probe_items):
            raise ValueError("the last 4 items must be probes")

        for item in labeled_items[: self.pre_count]:
            if item.phase is not Phase.PRE:
                raise ValueError("pre-shift labeled items must use the pre phase")

        for item in labeled_items[self.pre_count :]:
            if item.phase is not Phase.POST:
                raise ValueError("post-shift labeled items must use the post phase")

        if any(item.phase is not Phase.POST for item in probe_items):
            raise ValueError("probe items must use the post phase")

        pairs = tuple((item.q1, item.q2) for item in normalized_items)
        if len(set(pairs)) != len(pairs):
            raise ValueError("items must not repeat a (q1, q2) pair")

        if self.spec_version != SPEC_VERSION:
            raise ValueError(f"spec_version must equal {SPEC_VERSION}")
        if self.generator_version != GENERATOR_VERSION:
            raise ValueError(f"generator_version must equal {GENERATOR_VERSION}")
        if self.template_set_version != TEMPLATE_SET_VERSION:
            raise ValueError(
                f"template_set_version must equal {TEMPLATE_SET_VERSION}"
            )
