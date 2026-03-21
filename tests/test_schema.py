from dataclasses import fields, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol import (
    Difficulty,
    InteractionLabel,
    ItemKind,
    Phase,
    RuleName,
    Split,
    TemplateId,
    Transition,
)
from schema import (
    GENERATOR_VERSION,
    SPEC_VERSION,
    TEMPLATE_SET_VERSION,
    Episode,
    EpisodeItem,
    ProbeMetadata,
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
        split=Split.DEV,
        difficulty=Difficulty.EASY,
        template_id=TemplateId.T1,
        rule_A=RuleName.R_STD,
        rule_B=RuleName.R_INV,
        transition=Transition.R_STD_TO_R_INV,
        pre_count=2,
        post_labeled_count=3,
        shift_after_position=2,
        items=items,
        probe_targets=(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
            InteractionLabel.ATTRACT,
        ),
        probe_metadata=(
            ProbeMetadata(
                position=6,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
            ProbeMetadata(
                position=7,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.ATTRACT,
                new_rule_label=InteractionLabel.REPEL,
            ),
            ProbeMetadata(
                position=8,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
            ProbeMetadata(
                position=9,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
        ),
    )


class SchemaTestCase(unittest.TestCase):
    def test_schema_accepts_valid_minimal_episode(self):
        episode = make_valid_episode()

        self.assertEqual(episode.episode_id, "ife-r2-schema")
        self.assertEqual(len(episode.items), 9)

    def test_schema_fields_are_present(self):
        expected_fields = (
            "episode_id",
            "split",
            "difficulty",
            "template_id",
            "rule_A",
            "rule_B",
            "transition",
            "pre_count",
            "post_labeled_count",
            "shift_after_position",
            "items",
            "probe_targets",
            "probe_metadata",
            "spec_version",
            "generator_version",
            "template_set_version",
        )

        self.assertEqual(tuple(field.name for field in fields(Episode)), expected_fields)

        episode = make_valid_episode()
        self.assertEqual(episode.spec_version, SPEC_VERSION)
        self.assertEqual(episode.generator_version, GENERATOR_VERSION)
        self.assertEqual(episode.template_set_version, TEMPLATE_SET_VERSION)
        self.assertIs(episode.split, Split.DEV)
        self.assertIs(episode.difficulty, Difficulty.EASY)
        self.assertIs(episode.transition, Transition.R_STD_TO_R_INV)

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

    def test_schema_requires_probe_targets_to_match_probe_items(self):
        episode = make_valid_episode()

        with self.assertRaisesRegex(ValueError, "probe_targets must match rule_B labels"):
            replace(
                episode,
                probe_targets=(
                    InteractionLabel.REPEL,
                    InteractionLabel.REPEL,
                    InteractionLabel.ATTRACT,
                    InteractionLabel.ATTRACT,
                ),
            )

    def test_schema_requires_probe_metadata_to_match_probe_items(self):
        episode = make_valid_episode()
        invalid_probe_metadata = list(episode.probe_metadata)
        invalid_probe_metadata[0] = ProbeMetadata(
            position=6,
            is_disagreement_probe=True,
            old_rule_label=InteractionLabel.ATTRACT,
            new_rule_label=InteractionLabel.ATTRACT,
        )

        with self.assertRaisesRegex(ValueError, "probe_metadata must match"):
            replace(episode, probe_metadata=tuple(invalid_probe_metadata))

    def test_schema_rejects_homogeneous_probe_targets(self):
        episode = make_valid_episode()
        invalid_items = list(episode.items)
        invalid_items[5] = EpisodeItem(
            position=6,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=1,
            q2=3,
        )
        invalid_items[6] = EpisodeItem(
            position=7,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=2,
            q2=3,
        )
        invalid_items[7] = EpisodeItem(
            position=8,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=-1,
            q2=-3,
        )
        invalid_items[8] = EpisodeItem(
            position=9,
            phase=Phase.POST,
            kind=ItemKind.PROBE,
            q1=-2,
            q2=-3,
        )
        invalid_probe_metadata = (
            ProbeMetadata(
                position=6,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
            ProbeMetadata(
                position=7,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
            ProbeMetadata(
                position=8,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
            ProbeMetadata(
                position=9,
                is_disagreement_probe=True,
                old_rule_label=InteractionLabel.REPEL,
                new_rule_label=InteractionLabel.ATTRACT,
            ),
        )

        with self.assertRaisesRegex(ValueError, "at least two distinct labels"):
            replace(
                episode,
                items=tuple(invalid_items),
                probe_targets=(
                    InteractionLabel.ATTRACT,
                    InteractionLabel.ATTRACT,
                    InteractionLabel.ATTRACT,
                    InteractionLabel.ATTRACT,
                ),
                probe_metadata=invalid_probe_metadata,
            )


if __name__ == "__main__":
    unittest.main()
