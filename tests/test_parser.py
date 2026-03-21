from parser import ParsedPrediction, ParseStatus, parse_binary_output, parse_narrative_output
from protocol import InteractionLabel


def test_binary_output_parses_exactly_four_labels_in_order():
    parsed = parse_binary_output("attract, repel, repel, attract")

    assert parsed == ParsedPrediction(
        labels=(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        status=ParseStatus.VALID,
    )


def test_narrative_output_parses_final_labels_after_reasoning():
    parsed = parse_narrative_output(
        "\n".join(
            (
                "The later examples indicate a rule change.",
                "Final labels: attract, repel, repel, attract",
            )
        )
    )

    assert parsed == ParsedPrediction(
        labels=(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        status=ParseStatus.VALID,
    )


def test_safe_formatting_variants_normalize_to_canonical_labels():
    expected = ParsedPrediction(
        labels=(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        status=ParseStatus.VALID,
    )

    assert parse_binary_output("  ATTRACT, repel,\nREPEL,\nattract  ") == expected
    assert parse_binary_output("\nattract\nrepel\nrepel\nattract\n") == expected
    assert parse_narrative_output(
        "\n".join(
            (
                "Some reasoning here.",
                "Final labels:",
                "ATTRACT",
                "repel",
                "REPEL",
                "attract",
            )
        )
    ) == expected


def test_malformed_outputs_are_rejected_deterministically():
    invalid = ParsedPrediction(labels=(), status=ParseStatus.INVALID)

    assert parse_binary_output("attract, repel, repels, attract") == invalid
    assert parse_binary_output("attract, repel, repel, attract because of the shift") == invalid
    assert parse_narrative_output("Reasoning only without the required answer block.") == invalid
    assert parse_narrative_output(
        "\n".join(
            (
                "Reasoning.",
                "Final labels: attract, repel, repel, attract",
                "extra text",
            )
        )
    ) == invalid


def test_wrong_length_outputs_use_the_same_invalid_result():
    invalid = ParsedPrediction(labels=(), status=ParseStatus.INVALID)

    assert parse_binary_output("attract, repel, repel") == invalid
    assert parse_binary_output("attract, repel, repel, attract, attract") == invalid
    assert parse_narrative_output("Final labels: attract, repel, repel") == invalid
    assert parse_narrative_output("Final labels: attract, repel, repel, attract, repel") == invalid


def test_narrative_parser_uses_the_last_final_labels_block():
    parsed = parse_narrative_output(
        "\n".join(
            (
                "Final labels: repel, repel, repel, repel",
                "Updated reasoning after re-checking the post-shift evidence.",
                "Final labels: attract, repel, repel, attract",
            )
        )
    )

    assert parsed == ParsedPrediction(
        labels=(
            InteractionLabel.ATTRACT,
            InteractionLabel.REPEL,
            InteractionLabel.REPEL,
            InteractionLabel.ATTRACT,
        ),
        status=ParseStatus.VALID,
    )
