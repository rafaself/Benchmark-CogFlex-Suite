from dataclasses import fields, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol import InteractionLabel, ItemKind, Phase, RuleName, TemplateId
from schema import (
    GENERATOR_VERSION,
    SPEC_VERSION,
    TEMPLATE_SET_VERSION,
    Episode,
    EpisodeItem,
)


def make_valid_episode() -> Episode:
    items = (
        EpisodeItem(
            position=1,
            phase=Phase.PRE,
            kind=ItemKind.LABELED,
            q1=1,
            q2=2,
            label=InteractionLabel.REPEL,
        ),
        EpisodeItem(
            position=2,
            phase=Phase.PRE,
            kind=ItemKind.LABELED,
            q1=-1,
            q2=-2,
            label=InteractionLabel.REPEL,
        ),
        EpisodeItem(
            position=3,
            phase=Phase.POST,
            kind=ItemKind.LABELED,
            q1=1,
            q2=-1,
            label=InteractionLabel.REPEL,
        ),
        EpisodeItem(
            position=4,
            phase=Phase.POST,
            kind=ItemKind.LABELED,
            q1=2,
            q2=-2,
            label=InteractionLabel.REPEL,
        ),
        EpisodeItem(
            position=5,
            phase=Phase.POST,
            kind=ItemKind.LABELED,
            q1=-3,
            q2=3,
            label=InteractionLabel.REPEL,
        ),
        EpisodeItem(
            position=6,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=1,
            q2=3,
        ),
        EpisodeItem(
            position=7,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=-1,
            q2=3,
        ),
        EpisodeItem(
            position=8,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=2,
            q2=3,
        ),
        EpisodeItem(
            position=9,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=-2,
            q2=-3,
        ),
    )
    return Episode(
        episode_id="ife-r2-schema",
        template_id=TemplateId.T1,
        rule_A=RuleName.R_STD,
        rule_B=RuleName.R_INV,
        pre_count=2,
        post_labeled_count=3,
        shift_after_position=2,
        items=items,
    )


class SchemaTestCase(unittest.TestCase):
    def test_schema_accepts_valid_minimal_episode(self):
        episode = make_valid_episode()

        self.assertEqual(episode.episode_id, "ife-r2-schema")
        self.assertEqual(len(episode.items), 9)

    def test_schema_fields_are_present(self):
        expected_fields = (
            "episode_id",
            "template_id",
            "rule_A",
            "rule_B",
            "pre_count",
            "post_labeled_count",
            "shift_after_position",
            "items",
            "spec_version",
            "generator_version",
            "template_set_version",
        )

        self.assertEqual(tuple(field.name for field in fields(Episode)), expected_fields)

        episode = make_valid_episode()
        self.assertEqual(episode.spec_version, SPEC_VERSION)
        self.assertEqual(episode.generator_version, GENERATOR_VERSION)
        self.assertEqual(episode.template_set_version, TEMPLATE_SET_VERSION)

    def test_schema_requires_first_five_items_to_be_labeled(self):
        episode = make_valid_episode()
        invalid_items = list(episode.items)
        invalid_items[4] = EpisodeItem(
            position=5,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=-3,
            q2=3,
        )

        with self.assertRaisesRegex(ValueError, "first 5 items"):
            replace(episode, items=tuple(invalid_items))

    def test_schema_requires_last_four_items_to_be_probes(self):
        episode = make_valid_episode()
        invalid_items = list(episode.items)
        invalid_items[5] = EpisodeItem(
            position=6,
            phase=Phase.POST,
            kind=ItemKind.LABELED,
            q1=1,
            q2=3,
            label=InteractionLabel.ATTRACT,
        )

        with self.assertRaisesRegex(ValueError, "last 4 items"):
            replace(episode, items=tuple(invalid_items))

    def test_schema_requires_shift_after_position_to_match_pre_count(self):
        episode = make_valid_episode()

        with self.assertRaisesRegex(ValueError, "shift_after_position must equal pre_count"):
            replace(episode, shift_after_position=3)

    def test_schema_rejects_duplicate_charge_pairs(self):
        episode = make_valid_episode()
        invalid_items = list(episode.items)
        invalid_items[8] = EpisodeItem(
            position=9,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=1,
            q2=2,
        )

        with self.assertRaisesRegex(ValueError, "must not repeat"):
            replace(episode, items=tuple(invalid_items))

    def test_schema_rejects_invalid_total_item_count(self):
        episode = make_valid_episode()

        with self.assertRaisesRegex(ValueError, "exactly 9"):
            replace(episode, items=episode.items[:-1])


if __name__ == "__main__":
    unittest.main()
