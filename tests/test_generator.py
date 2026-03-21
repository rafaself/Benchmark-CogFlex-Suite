from dataclasses import fields
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generator import generate_episode
from protocol import LABELED_ITEM_COUNT, ItemKind, Phase, TemplateId
from rules import label
from schema import Episode


class GeneratorTestCase(unittest.TestCase):
    def test_same_seed_regenerates_the_same_episode(self):
        self.assertEqual(generate_episode(7), generate_episode(7))

    def test_different_seeds_can_generate_different_episodes(self):
        episodes = {generate_episode(seed) for seed in range(6)}

        self.assertGreater(len(episodes), 1)

    def test_only_t1_and_t2_are_emitted(self):
        emitted_templates = {
            generate_episode(seed).template_id for seed in range(32)
        }

        self.assertEqual(emitted_templates, {TemplateId.T1, TemplateId.T2})

    def test_episode_length_is_always_nine(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                self.assertEqual(len(generate_episode(seed).items), 9)

    def test_labeled_and_probe_boundaries_are_correct(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                episode = generate_episode(seed)
                labeled_items = episode.items[:LABELED_ITEM_COUNT]
                probe_items = episode.items[LABELED_ITEM_COUNT:]

                self.assertTrue(all(item.kind is ItemKind.LABELED for item in labeled_items))
                self.assertTrue(all(item.kind is ItemKind.PROBE for item in probe_items))
                self.assertTrue(
                    all(item.phase is Phase.PRE for item in labeled_items[: episode.pre_count])
                )
                self.assertTrue(
                    all(item.phase is Phase.POST for item in labeled_items[episode.pre_count :])
                )
                self.assertTrue(all(item.phase is Phase.POST for item in probe_items))

    def test_shift_after_position_equals_pre_count(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                episode = generate_episode(seed)
                self.assertEqual(episode.shift_after_position, episode.pre_count)

    def test_rule_b_is_always_the_opposite_of_rule_a(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                episode = generate_episode(seed)
                self.assertIs(episode.rule_B, episode.rule_A.opposite)

    def test_no_duplicate_q1_q2_pairs_exist_within_an_episode(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                episode = generate_episode(seed)
                pairs = [(item.q1, item.q2) for item in episode.items]
                self.assertEqual(len(set(pairs)), len(pairs))

    def test_schema_fields_are_always_present(self):
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

        episode = generate_episode(3)

        self.assertIsInstance(episode, Episode)
        self.assertEqual(tuple(field.name for field in fields(Episode)), expected_fields)
        for field_name in expected_fields:
            with self.subTest(field_name=field_name):
                self.assertTrue(hasattr(episode, field_name))

    def test_labeled_items_use_the_active_rule_engine_label(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                episode = generate_episode(seed)
                for item in episode.items[:LABELED_ITEM_COUNT]:
                    active_rule = (
                        episode.rule_A
                        if item.position <= episode.pre_count
                        else episode.rule_B
                    )
                    self.assertEqual(item.label, label(active_rule, item.q1, item.q2))


if __name__ == "__main__":
    unittest.main()
