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
                "attract, repel, repel, attract",
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
                "ATTRACT, repel, REPEL, attract",
            )
        )
    ) == expected
    assert parse_narrative_output("Final labels: ATTRACT, repel, REPEL, attract") == expected


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
    assert parse_narrative_output("attract, repel, repel") == invalid
    assert parse_narrative_output("attract, repel, repel, attract, repel") == invalid


def test_narrative_parser_scores_only_the_last_answer_line():
    parsed = parse_narrative_output(
        "\n".join(
            (
                "repel, repel, repel, repel",
                "Updated reasoning after re-checking the post-shift evidence.",
                "attract, repel, repel, attract",
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


def test_narrative_parser_still_accepts_legacy_final_labels_block():
    parsed = parse_narrative_output(
        "\n".join(
            (
                "Reasoning about the revised local rule.",
                "Final labels:",
                "attract",
                "repel",
                "repel",
                "attract",
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
