from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol import (
    CHARGES,
    EPISODE_LENGTH,
    PROBE_COUNT,
    RULES,
    TEMPLATE_IDS,
    TEMPLATES,
    InteractionLabel,
    RuleName,
    TemplateId,
    Transition,
    parse_label,
    parse_rule,
    parse_template_id,
)


class ProtocolTestCase(unittest.TestCase):
    def test_rule_parser_accepts_enums_and_canonical_strings(self):
        self.assertIs(parse_rule(RuleName.R_STD), RuleName.R_STD)
        self.assertIs(parse_rule("R_inv"), RuleName.R_INV)

    def test_rule_parser_rejects_typos_with_canonical_values(self):
        with self.assertRaisesRegex(ValueError, r"unknown rule: R-std"):
            parse_rule("R-std")

    def test_label_parser_rejects_noncanonical_values(self):
        with self.assertRaisesRegex(ValueError, r"unknown label: repells"):
            parse_label("repells")

    def test_template_parser_rejects_noncanonical_values(self):
        with self.assertRaisesRegex(ValueError, r"unknown template_id: t1"):
            parse_template_id("t1")

    def test_rules_expose_canonical_opposites_and_transitions(self):
        self.assertIs(RuleName.R_STD.opposite, RuleName.R_INV)
        self.assertIs(RuleName.R_INV.opposite, RuleName.R_STD)
        self.assertEqual(
            Transition.from_rules(RuleName.R_STD, RuleName.R_INV),
            Transition.R_STD_TO_R_INV,
        )
        self.assertEqual(
            Transition.from_rules(RuleName.R_INV, RuleName.R_STD),
            Transition.R_INV_TO_R_STD,
        )

    def test_template_specs_match_frozen_counts(self):
        self.assertEqual(RULES, frozenset(RuleName))
        self.assertEqual(TEMPLATE_IDS, frozenset(TemplateId))
        self.assertEqual(CHARGES, (-3, -2, -1, 1, 2, 3))

        for template_id, spec in TEMPLATES.items():
            with self.subTest(template_id=template_id):
                self.assertIs(spec.template_id, template_id)
                self.assertEqual(spec.probe_count, PROBE_COUNT)
                self.assertEqual(spec.total_items, EPISODE_LENGTH)
                self.assertEqual(spec.pre_count + spec.post_labeled_count, 5)

        self.assertEqual(TEMPLATES[TemplateId.T1].pre_count, 2)
        self.assertEqual(TEMPLATES[TemplateId.T1].post_labeled_count, 3)
        self.assertEqual(TEMPLATES[TemplateId.T2].pre_count, 3)
        self.assertEqual(TEMPLATES[TemplateId.T2].post_labeled_count, 2)

    def test_transition_rejects_same_rule_endpoints(self):
        with self.assertRaisesRegex(ValueError, "requires two distinct rules"):
            Transition.from_rules(RuleName.R_STD, RuleName.R_STD)


if __name__ == "__main__":
    unittest.main()
