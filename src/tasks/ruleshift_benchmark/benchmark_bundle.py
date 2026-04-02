from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

from tasks.ruleshift_benchmark.protocol import (
    LABELED_ITEM_COUNT,
    TemplateFamily,
    format_public_label,
    format_public_state,
)
from tasks.ruleshift_benchmark.schema import Episode, EpisodeItem
from tasks.ruleshift_benchmark.splits import (
    MANIFEST_VERSION,
    discover_private_dataset_root,
    load_frozen_split,
    load_split_manifest,
    resolve_private_dataset_root,
)

__all__ = [
    "TASK_NAME",
    "build_benchmark_bundle",
    "build_leaderboard_rows",
]

TASK_NAME: Final[str] = "ruleshift_benchmark"


@dataclass(frozen=True, slots=True)
class BinaryPresentation:
    intro: str
    labeled_heading: str
    probe_heading: str
    outro: str
    line_renderer: Callable[[EpisodeItem], str]


def _render_binary_line(item: EpisodeItem) -> str:
    return (
        f"{item.position}. r1={_format_marker_value(item.q1)}, "
        f"r2={_format_marker_value(item.q2)} -> {_render_outcome(item)}"
    )


def _render_binary_log_line(item: EpisodeItem) -> str:
    return (
        f"[{item.position:02d}] r1={_format_marker_value(item.q1)} | "
        f"r2={_format_marker_value(item.q2)} | observed={_render_outcome(item)}"
    )


def _render_binary_ledger_line(item: EpisodeItem) -> str:
    return (
        f"row {item.position:02d} | r1={_format_marker_value(item.q1)} | "
        f"r2={_format_marker_value(item.q2)} | state={_render_outcome(item)}"
    )


def _render_outcome(item: EpisodeItem) -> str:
    return format_public_state(item.label) if item.label is not None else "?"


def _format_marker_value(marker_value: int) -> str:
    return f"{marker_value:+d}"


_BINARY_OUTRO: Final[str] = (
    "Return exactly 4 outputs in order, one per probe. "
    "Use only type_a or type_b. Map zark to type_a and blim to type_b."
)

_BINARY_PRESENTATIONS: Final[dict[TemplateFamily, BinaryPresentation]] = {
    TemplateFamily.CANONICAL: BinaryPresentation(
        intro=(
            "You are given labeled records for two markers.\n"
            "Each labeled line shows r1, r2, and the observed state.\n"
            "Use the full sequence to infer which sign combinations were revised by the later evidence, "
            "then answer the final unlabeled cases."
        ),
        labeled_heading="Labeled examples:",
        probe_heading="Probes:",
        outro=_BINARY_OUTRO,
        line_renderer=_render_binary_line,
    ),
    TemplateFamily.OBSERVATION_LOG: BinaryPresentation(
        intro=(
            "Review the observation log for two markers.\n"
            "Each entry records r1, r2, and the observed state.\n"
            "Use the full log to infer which sign combinations were revised later, then answer the unlabeled probe entries."
        ),
        labeled_heading="Resolved log entries:",
        probe_heading="Unresolved probe entries:",
        outro=_BINARY_OUTRO,
        line_renderer=_render_binary_log_line,
    ),
    TemplateFamily.CASE_LEDGER: BinaryPresentation(
        intro=(
            "Review the case ledger for two markers.\n"
            "Each row records r1, r2, and the observed state.\n"
            "Use the full ledger to infer which sign combinations were revised by the later evidence, "
            "then complete the pending rows."
        ),
        labeled_heading="Confirmed ledger rows:",
        probe_heading="Pending ledger rows:",
        outro=_BINARY_OUTRO,
        line_renderer=_render_binary_ledger_line,
    ),
}


def build_benchmark_bundle(
    *,
    include_private: bool = True,
    private_dataset_root: Path | str | None = None,
) -> dict[str, object]:
    partitions = [_build_partition_bundle("public_leaderboard")]

    if include_private:
        resolved_private_root = _resolve_optional_private_dataset_root(private_dataset_root)
        if resolved_private_root is not None:
            partitions.append(
                _build_partition_bundle(
                    "private_leaderboard",
                    private_dataset_root=resolved_private_root,
                )
            )

    return {
        "task": TASK_NAME,
        "benchmark_version": MANIFEST_VERSION,
        "partitions": partitions,
    }


def _build_partition_bundle(
    partition: str,
    *,
    private_dataset_root: Path | str | None = None,
) -> dict[str, object]:
    manifest = load_split_manifest(partition, private_dataset_root=private_dataset_root)
    records = load_frozen_split(partition, private_dataset_root=private_dataset_root)

    return {
        "partition": manifest.partition,
        "episode_split": manifest.episode_split.value,
        "manifest_version": manifest.manifest_version,
        "seed_bank_version": manifest.seed_bank_version,
        "episode_count": len(records),
        "episodes": [
            {
                "seed": record.seed,
                "episode_id": record.episode.episode_id,
                "prompt_binary": render_binary_prompt(record.episode),
                "probe_targets": [
                    format_public_label(label) for label in record.episode.probe_targets
                ],
            }
            for record in records
        ],
    }


def build_leaderboard_rows(bundle: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for partition in bundle["partitions"]:
        split_name = partition["partition"]
        for episode in partition["episodes"]:
            rows.append(
                {
                    "episode_id": episode["episode_id"],
                    "split": split_name,
                    "prompt_binary": episode["prompt_binary"],
                    "probe_targets": tuple(episode["probe_targets"]),
                }
            )
    return rows


def _resolve_optional_private_dataset_root(
    private_dataset_root: Path | str | None,
) -> Path | None:
    if private_dataset_root is not None:
        return resolve_private_dataset_root(private_dataset_root)
    return discover_private_dataset_root()


def render_binary_prompt(episode: Episode) -> str:
    labeled_items = episode.items[:LABELED_ITEM_COUNT]
    probe_items = episode.items[LABELED_ITEM_COUNT:]
    presentation = _BINARY_PRESENTATIONS[episode.template_family]
    return "\n".join(
        (
            presentation.intro,
            "",
            presentation.labeled_heading,
            *(presentation.line_renderer(item) for item in labeled_items),
            "",
            presentation.probe_heading,
            *(presentation.line_renderer(item) for item in probe_items),
            "",
            presentation.outro,
        )
    )
