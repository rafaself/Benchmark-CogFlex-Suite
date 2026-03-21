from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, TypeVar


class ProtocolEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


ProtocolEnumT = TypeVar("ProtocolEnumT", bound=ProtocolEnum)


def _parse_enum(
    enum_type: type[ProtocolEnumT],
    value: ProtocolEnumT | str,
    field_name: str,
) -> ProtocolEnumT:
    if isinstance(value, enum_type):
        return value

    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(
            f"unknown {field_name}: {value}. expected one of: {allowed}"
        ) from exc


class RuleName(ProtocolEnum):
    R_STD = "R_std"
    R_INV = "R_inv"

    @property
    def opposite(self) -> "RuleName":
        return RuleName.R_INV if self is RuleName.R_STD else RuleName.R_STD


class InteractionLabel(ProtocolEnum):
    ATTRACT = "attract"
    REPEL = "repel"


class TemplateId(ProtocolEnum):
    T1 = "T1"
    T2 = "T2"


class Transition(ProtocolEnum):
    R_STD_TO_R_INV = "R_std_to_R_inv"
    R_INV_TO_R_STD = "R_inv_to_R_std"

    @classmethod
    def from_rules(
        cls,
        rule_a: RuleName | str,
        rule_b: RuleName | str,
    ) -> "Transition":
        start = parse_rule(rule_a)
        end = parse_rule(rule_b)

        if start is end:
            raise ValueError(
                "transition requires two distinct rules"
            )

        if start is RuleName.R_STD:
            return cls.R_STD_TO_R_INV

        return cls.R_INV_TO_R_STD


class Split(ProtocolEnum):
    DEV = "dev"
    PUBLIC = "public"
    PRIVATE = "private"


class Difficulty(ProtocolEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Phase(ProtocolEnum):
    PRE = "pre"
    POST = "post"


class ItemKind(ProtocolEnum):
    LABELED = "labeled"
    PROBE = "probe"


CHARGES: Final[tuple[int, ...]] = (-3, -2, -1, 1, 2, 3)
CASE_SPACE: Final[tuple[tuple[int, int], ...]] = tuple(
    (q1, q2) for q1 in CHARGES for q2 in CHARGES
)
PROBE_COUNT: Final[int] = 4
LABELED_ITEM_COUNT: Final[int] = 5
EPISODE_LENGTH: Final[int] = LABELED_ITEM_COUNT + PROBE_COUNT

RULES: Final[frozenset[RuleName]] = frozenset(RuleName)
LABELS: Final[frozenset[InteractionLabel]] = frozenset(InteractionLabel)
TEMPLATE_IDS: Final[frozenset[TemplateId]] = frozenset(TemplateId)
TRANSITIONS: Final[frozenset[Transition]] = frozenset(Transition)
SPLITS: Final[frozenset[Split]] = frozenset(Split)
DIFFICULTIES: Final[frozenset[Difficulty]] = frozenset(Difficulty)
PHASES: Final[frozenset[Phase]] = frozenset(Phase)
ITEM_KINDS: Final[frozenset[ItemKind]] = frozenset(ItemKind)


@dataclass(frozen=True)
class TemplateSpec:
    template_id: TemplateId
    pre_count: int
    post_labeled_count: int
    probe_count: int = PROBE_COUNT

    @property
    def shift_after_position(self) -> int:
        return self.pre_count

    @property
    def total_items(self) -> int:
        return self.pre_count + self.post_labeled_count + self.probe_count


TEMPLATES: Final[dict[TemplateId, TemplateSpec]] = {
    TemplateId.T1: TemplateSpec(
        template_id=TemplateId.T1,
        pre_count=2,
        post_labeled_count=3,
    ),
    TemplateId.T2: TemplateSpec(
        template_id=TemplateId.T2,
        pre_count=3,
        post_labeled_count=2,
    ),
}


def parse_rule(value: RuleName | str) -> RuleName:
    return _parse_enum(RuleName, value, "rule")


def parse_label(value: InteractionLabel | str) -> InteractionLabel:
    return _parse_enum(InteractionLabel, value, "label")


def parse_template_id(value: TemplateId | str) -> TemplateId:
    return _parse_enum(TemplateId, value, "template_id")
