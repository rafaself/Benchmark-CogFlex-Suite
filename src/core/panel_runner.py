from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from core.audit import (
    MatchedModeComparisonSummary,
    ModeComparisonSummary,
    ReleaseAuditReport,
    ReleaseAuditSourceSummary,
)
from core.model_execution import ModelMode, ModelRunConfig
from core.model_runner import BenchmarkModeRunRow, BenchmarkRunResult
from core.parser import ParseStatus
from tasks.iron_find_electric.baselines import (
    last_evidence_baseline,
    never_update_baseline,
)
from tasks.iron_find_electric.schema import Episode

__all__ = [
    "DEFAULT_PANEL_CONFIG",
    "DEFAULT_PANEL_MODES",
    "PanelArtifacts",
    "TASK_MODE_LABELS",
    "artifact_path_for_report",
    "build_panel_artifact",
    "build_panel_progress_callback",
    "render_panel_markdown",
]

DEFAULT_PANEL_MODES: tuple[ModelMode, ...] = (ModelMode.BINARY,)
DEFAULT_PANEL_CONFIG = ModelRunConfig(
    timeout_seconds=60.0,
    temperature=0.0,
    thinking_budget=0,
)
TASK_MODE_LABELS = {
    ModelMode.BINARY: "Binary",
    ModelMode.NARRATIVE: "Narrative",
}
_BASELINE_ORDER: tuple[str, ...] = (
    "random",
    "never_update",
    "last_evidence",
    "physics_prior",
    "template_position",
)
_TRANSITION_ORDER: tuple[str, ...] = (
    "R_std_to_R_inv",
    "R_inv_to_R_std",
)


@dataclass(frozen=True, slots=True)
class PanelArtifacts:
    provider_name: str
    model_name: str
    prompt_modes: tuple[ModelMode, ...]
    release_report: ReleaseAuditReport
    report_markdown: str
    report_path: Path
    artifact_payload: dict[str, object] | None = None
    artifact_path: Path | None = None
    snapshot_report_path: Path | None = None
    snapshot_artifact_path: Path | None = None


def build_panel_progress_callback(
    split_name: str, *, panel_label: str = "panel"
):
    def _report_progress(
        mode: ModelMode, index: int, total: int, episode_id: str
    ) -> None:
        print(
            f"[{panel_label}] split={split_name} mode={mode.value} "
            f"episode={index}/{total} id={episode_id}",
            file=sys.stderr,
            flush=True,
        )

    return _report_progress


def artifact_path_for_report(report_path: Path) -> Path:
    if report_path.name == "report.md" and report_path.parent.name == "latest":
        return report_path.with_name("artifact.json")
    return report_path.with_suffix(".json")


def render_panel_markdown(
    release_report: ReleaseAuditReport,
    *,
    model_name: str,
    provider_name: str,
    prompt_modes: tuple[ModelMode, ...],
    artifact_payload: dict[str, object] | None = None,
    report_title: str = "Panel Report",
) -> str:
    model_summaries = tuple(
        summary
        for summary in release_report.model_summaries
        if summary.source_family == model_name and summary.is_real_model
    )
    if not model_summaries:
        raise ValueError(f"no real-model summaries found for {model_name!r}")

    lines = [
        f"# {report_title}",
        "",
        f"- Release: {release_report.release_id}",
        f"- Provider: {provider_name}",
        f"- Model: {model_name}",
        f"- Prompt modes run: {', '.join(mode.value for mode in prompt_modes)}",
        f"- Covered splits: {', '.join(split_name for split_name, _ in release_report.split_episode_counts)}",
        "",
    ]

    primary_summary = _pick_primary_summary(model_summaries, prompt_modes)
    binary_summary = _pick_mode_summary(model_summaries, task_mode="Binary")
    narrative_summary = _pick_mode_summary(
        model_summaries, task_mode="Narrative"
    )
    matched_mode_comparison = _pick_matched_mode_comparison(
        release_report,
        source_family=model_name,
    )
    lines.extend(
        [
            "## Headline",
            "",
            f"- Binary-only headline metric: {primary_summary.name} = {primary_summary.overall.accuracy:.6f}",
            f"- Binary parse-valid rate: {primary_summary.overall.parse_valid_rate:.6f}",
            f"- Best baseline: {release_report.baseline_comparison.best_baseline_name} "
            f"({(release_report.baseline_comparison.best_baseline_accuracy or 0.0):.6f})",
            "",
            "| Source | Accuracy | Gap vs model |",
            "| --- | ---: | ---: |",
            f"| {primary_summary.name} | {primary_summary.overall.accuracy:.6f} | 0.000000 |",
        ]
    )
    for baseline_summary in release_report.baseline_summaries:
        lines.append(
            f"| {baseline_summary.name} | {baseline_summary.overall.accuracy:.6f} | "
            f"{primary_summary.overall.accuracy - baseline_summary.overall.accuracy:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Headline By Split",
            "",
            "| Split | Model | random | never-update | last-evidence | physics-prior | template-position |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    model_by_split = dict(primary_summary.by_split)
    baselines_by_name = {
        summary.name: summary for summary in release_report.baseline_summaries
    }
    for split_name, _episode_count in release_report.split_episode_counts:
        lines.append(
            f"| {split_name} | {model_by_split[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['random'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['never_update'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['last_evidence'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['physics_prior'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['template_position'].by_split)[split_name].accuracy:.6f} |"
        )

    if (
        matched_mode_comparison is not None
        and binary_summary is not None
        and narrative_summary is not None
    ):
        lines.extend(
            [
                "",
                "## Paired Robustness",
                "",
                "| Scope | Binary accuracy | Narrative accuracy | Delta | Binary parse-valid | Narrative parse-valid |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                _render_mode_comparison_row(
                    "overall", matched_mode_comparison.overall
                ),
            ]
        )
        binary_by_split = dict(binary_summary.by_split)
        narrative_by_split = dict(narrative_summary.by_split)
        for split_name, _episode_count in release_report.split_episode_counts:
            if (
                split_name not in binary_by_split
                or split_name not in narrative_by_split
            ):
                continue
            lines.append(
                _render_mode_comparison_row(
                    split_name,
                    _build_mode_comparison_from_split_summaries(
                        binary_by_split[split_name],
                        narrative_by_split[split_name],
                    ),
                )
            )

        lines.extend(
            [
                "",
                "## Diagnostic Slices",
                "",
                "| Slice type | Label | Binary accuracy | Narrative accuracy | Delta | Binary parse-valid | Narrative parse-valid |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for label, comparison in matched_mode_comparison.by_template:
            lines.append(
                _render_mode_slice_row("template", label, comparison)
            )
        for label, comparison in matched_mode_comparison.by_difficulty:
            lines.append(
                _render_mode_slice_row("difficulty", label, comparison)
            )

        if artifact_payload is not None:
            diagnostic_summary_rows = tuple(
                artifact_payload.get("diagnostic_summary", ())
            )
            if diagnostic_summary_rows:
                lines.extend(
                    [
                        "",
                        "## Failure Decomposition (diagnostic-only)",
                        "",
                        "| Scope | Mode | Runtime | Parse/format | Parse-valid | Correct | Adaptation | Adaptation among parse-valid |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- |",
                    ]
                )
                for row in _diagnostic_rows_for_markdown(
                    diagnostic_summary_rows,
                    scope_types=("overall", "split"),
                ):
                    lines.append(
                        "| {scope} | {mode} | {runtime} | {parse_failure} | {parse_valid} | "
                        "{correct} | {adaptation} | {adaptation_among_valid} |".format(
                            scope=_format_scope_label(row),
                            mode=row["mode"],
                            runtime=_format_count_rate(
                                int(row["runtime_error_count"]),
                                int(row["episode_count"]),
                            ),
                            parse_failure=_format_count_rate(
                                int(row["parse_failure_count"]),
                                int(row["episode_count"]),
                            ),
                            parse_valid=_format_count_rate(
                                int(row["parse_valid_count"]),
                                int(row["episode_count"]),
                            ),
                            correct=_format_count_rate(
                                int(row["correct_count"]),
                                int(row["episode_count"]),
                            ),
                            adaptation=_format_count_rate(
                                int(row["adaptation_failure_count"]),
                                int(row["episode_count"]),
                            ),
                            adaptation_among_valid=_format_count_rate(
                                int(row["adaptation_failure_count"]),
                                int(row["parse_valid_count"]),
                            ),
                        )
                    )
                lines.extend(
                    [
                        "",
                        "## Direct Disagreement Diagnostics (diagnostic-only)",
                        "",
                        "| Scope | Mode | Exact global old-rule | Exact global recency | Old-rule-only episodes | Recency-only episodes | Mixed episodes | Old-rule error probes | Recency error probes |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                    ]
                )
                for row in _diagnostic_rows_for_markdown(
                    diagnostic_summary_rows,
                    scope_types=("overall", "split"),
                ):
                    lines.append(
                        "| {scope} | {mode} | {exact_old} | {exact_recency} | {old_only} | "
                        "{recency_only} | {mixed} | {old_probes} | {recency_probes} |".format(
                            scope=_format_scope_label(row),
                            mode=row["mode"],
                            exact_old=_format_count_rate(
                                int(
                                    row[
                                        "exact_global_old_rule_persistence_count"
                                    ]
                                ),
                                int(row["adaptation_failure_count"]),
                            ),
                            exact_recency=_format_count_rate(
                                int(
                                    row[
                                        "exact_global_recency_overshoot_count"
                                    ]
                                ),
                                int(row["adaptation_failure_count"]),
                            ),
                            old_only=_format_count_rate(
                                int(row["old_rule_only_count"]),
                                int(row["adaptation_failure_count"]),
                            ),
                            recency_only=_format_count_rate(
                                int(row["recency_overshoot_only_count"]),
                                int(row["adaptation_failure_count"]),
                            ),
                            mixed=_format_count_rate(
                                int(row["mixed_disagreement_count"]),
                                int(row["adaptation_failure_count"]),
                            ),
                            old_probes=_format_count_rate(
                                int(row["old_rule_error_probe_count"]),
                                int(row["error_probe_count"]),
                            ),
                            recency_probes=_format_count_rate(
                                int(
                                    row[
                                        "recency_overshoot_error_probe_count"
                                    ]
                                ),
                                int(row["error_probe_count"]),
                            ),
                        )
                    )
                lines.extend(
                    [
                        "",
                        "Episode cells in this table are normalized by adaptation-failure episodes. Probe cells are normalized by wrong probes inside parse-valid adaptation failures.",
                    ]
                )
            taxonomy_rows = tuple(
                artifact_payload.get("failure_taxonomy", ())
            )
            if taxonomy_rows:
                lines.extend(
                    [
                        "",
                        "## Failure Taxonomy (diagnostic-only)",
                        "",
                        "| Scope | Mode | Provider/runtime error rate | Parse/format failure rate | Adaptation failure rate | Possible old-rule persistence rate | Possible recency overshoot rate |",
                        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
                    ]
                )
                for row in taxonomy_rows:
                    if not isinstance(row, dict):
                        continue
                    lines.append(
                        "| {scope} | {mode} | {runtime_error_rate:.6f} | {parse_failure_rate:.6f} | "
                        "{adaptation_failure_rate:.6f} | {possible_old_rule_persistence_rate:.6f} | "
                        "{possible_recency_overshoot_rate:.6f} |".format(
                            scope=row["scope"],
                            mode=row["mode"],
                            runtime_error_rate=row["runtime_error_rate"],
                            parse_failure_rate=row["parse_failure_rate"],
                            adaptation_failure_rate=row[
                                "adaptation_failure_rate"
                            ],
                            possible_old_rule_persistence_rate=row[
                                "possible_old_rule_persistence_rate"
                            ],
                            possible_recency_overshoot_rate=row[
                                "possible_recency_overshoot_rate"
                            ],
                        )
                    )
                lines.extend(
                    [
                        "",
                        "Taxonomy rates are episode-level over scored outputs. Persistence and recency tags are diagnostic-only exact-match comparisons against `never_update` and `last_evidence`.",
                    ]
                )
            lines.extend(_build_live_execution_notes(artifact_payload))
    elif len(model_summaries) > 1:
        lines.extend(
            [
                "",
                "## Additional Prompt Modes",
                "",
                "| Source | Accuracy | Parse-valid rate | Covered splits |",
                "| --- | ---: | ---: | --- |",
            ]
        )
        for summary in model_summaries:
            if summary.name == primary_summary.name:
                continue
            lines.append(
                f"| {summary.name} | {summary.overall.accuracy:.6f} | "
                f"{summary.overall.parse_valid_rate:.6f} | {', '.join(summary.covered_splits)} |"
            )

    if artifact_payload is not None and matched_mode_comparison is None:
        diagnostic_summary_rows = tuple(
            artifact_payload.get("diagnostic_summary", ())
        )
        if diagnostic_summary_rows:
            lines.extend(
                [
                    "",
                    "## Failure Decomposition (diagnostic-only)",
                    "",
                    "| Scope | Mode | Runtime | Parse/format | Parse-valid | Correct | Adaptation | Adaptation among parse-valid |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for row in _diagnostic_rows_for_markdown(
                diagnostic_summary_rows,
                scope_types=("overall", "split"),
            ):
                lines.append(
                    "| {scope} | {mode} | {runtime} | {parse_failure} | {parse_valid} | "
                    "{correct} | {adaptation} | {adaptation_among_valid} |".format(
                        scope=_format_scope_label(row),
                        mode=row["mode"],
                        runtime=_format_count_rate(
                            int(row["runtime_error_count"]),
                            int(row["episode_count"]),
                        ),
                        parse_failure=_format_count_rate(
                            int(row["parse_failure_count"]),
                            int(row["episode_count"]),
                        ),
                        parse_valid=_format_count_rate(
                            int(row["parse_valid_count"]),
                            int(row["episode_count"]),
                        ),
                        correct=_format_count_rate(
                            int(row["correct_count"]),
                            int(row["episode_count"]),
                        ),
                        adaptation=_format_count_rate(
                            int(row["adaptation_failure_count"]),
                            int(row["episode_count"]),
                        ),
                        adaptation_among_valid=_format_count_rate(
                            int(row["adaptation_failure_count"]),
                            int(row["parse_valid_count"]),
                        ),
                    )
                )
            lines.extend(
                [
                    "",
                    "## Direct Disagreement Diagnostics (diagnostic-only)",
                    "",
                    "| Scope | Mode | Exact global old-rule | Exact global recency | Old-rule-only episodes | Recency-only episodes | Mixed episodes | Old-rule error probes | Recency error probes |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for row in _diagnostic_rows_for_markdown(
                diagnostic_summary_rows,
                scope_types=("overall", "split"),
            ):
                lines.append(
                    "| {scope} | {mode} | {exact_old} | {exact_recency} | {old_only} | "
                    "{recency_only} | {mixed} | {old_probes} | {recency_probes} |".format(
                        scope=_format_scope_label(row),
                        mode=row["mode"],
                        exact_old=_format_count_rate(
                            int(
                                row[
                                    "exact_global_old_rule_persistence_count"
                                ]
                            ),
                            int(row["adaptation_failure_count"]),
                        ),
                        exact_recency=_format_count_rate(
                            int(
                                row[
                                    "exact_global_recency_overshoot_count"
                                ]
                            ),
                            int(row["adaptation_failure_count"]),
                        ),
                        old_only=_format_count_rate(
                            int(row["old_rule_only_count"]),
                            int(row["adaptation_failure_count"]),
                        ),
                        recency_only=_format_count_rate(
                            int(row["recency_overshoot_only_count"]),
                            int(row["adaptation_failure_count"]),
                        ),
                        mixed=_format_count_rate(
                            int(row["mixed_disagreement_count"]),
                            int(row["adaptation_failure_count"]),
                        ),
                        old_probes=_format_count_rate(
                            int(row["old_rule_error_probe_count"]),
                            int(row["error_probe_count"]),
                        ),
                        recency_probes=_format_count_rate(
                            int(
                                row[
                                    "recency_overshoot_error_probe_count"
                                ]
                            ),
                            int(row["error_probe_count"]),
                        ),
                    )
                )
            lines.extend(
                [
                    "",
                    "Episode cells in this table are normalized by adaptation-failure episodes. Probe cells are normalized by wrong probes inside parse-valid adaptation failures.",
                ]
            )
        lines.extend(_build_live_execution_notes(artifact_payload))

    if artifact_payload is not None:
        diagnostic_summary_rows = tuple(
            artifact_payload.get("diagnostic_summary", ())
        )
        if diagnostic_summary_rows:
            lines.extend(
                [
                    "",
                    "## Diagnostic Failure Slices (diagnostic-only)",
                    "",
                    "| Slice type | Label | Mode | Episodes | Accuracy | Parse-valid | Adaptation among parse-valid | Old-rule error probes | Recency error probes |",
                    "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
                ]
            )
            for row in _diagnostic_rows_for_markdown(
                diagnostic_summary_rows,
                scope_types=("template", "difficulty", "transition"),
            ):
                lines.append(
                    "| {scope_type} | {label} | {mode} | {episodes} | {accuracy:.6f} | "
                    "{parse_valid:.6f} | {adaptation_among_valid} | {old_probes} | {recency_probes} |".format(
                        scope_type=row["scope_type"],
                        label=row["scope_label"],
                        mode=row["mode"],
                        episodes=int(row["episode_count"]),
                        accuracy=float(row["correct_rate"]),
                        parse_valid=float(row["parse_valid_rate"]),
                        adaptation_among_valid=_format_count_rate(
                            int(row["adaptation_failure_count"]),
                            int(row["parse_valid_count"]),
                        ),
                        old_probes=_format_count_rate(
                            int(row["old_rule_error_probe_count"]),
                            int(row["error_probe_count"]),
                        ),
                        recency_probes=_format_count_rate(
                            int(row["recency_overshoot_error_probe_count"]),
                            int(row["error_probe_count"]),
                        ),
                    )
                )
            lines.extend(
                [
                    "",
                    "All views in this section are diagnostic-only. They use the frozen probe metadata already bundled with each episode and do not replace the Binary-only headline metric.",
                ]
            )

    lines.extend(
        [
            "",
            "## Binary Diagnostic Slices",
            "",
            "| Template | Accuracy | Parse-valid rate |",
            "| --- | ---: | ---: |",
        ]
    )
    for label, slice_summary in primary_summary.by_template:
        lines.append(
            f"| {label} | {slice_summary.accuracy:.6f} | {slice_summary.parse_valid_rate:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Binary Difficulty Slices",
            "",
            "| Difficulty | Accuracy | Parse-valid rate |",
            "| --- | ---: | ---: |",
        ]
    )
    for label, slice_summary in primary_summary.by_difficulty:
        lines.append(
            f"| {label} | {slice_summary.accuracy:.6f} | {slice_summary.parse_valid_rate:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `hard` remains reserved and is not emitted in the current frozen repaired benchmark, so no hard slice is reported.",
        ]
    )
    if ModelMode.NARRATIVE not in prompt_modes:
        lines.append(
            "- Narrative mode was not run in this first real-model panel, so Binary vs Narrative comparison is unavailable."
        )
    for limitation in release_report.limitations:
        if "hard slice omitted" in limitation:
            continue
        if (
            "No matched Binary/Narrative model runs supplied" in limitation
            and ModelMode.NARRATIVE not in prompt_modes
        ):
            continue
        lines.append(f"- {limitation}")

    return "\n".join(lines) + "\n"


def build_panel_artifact(
    *,
    provider_name: str,
    model_name: str,
    prompt_modes: tuple[ModelMode, ...],
    release_report: ReleaseAuditReport,
    episodes_by_split: dict[str, tuple[Episode, ...]],
    benchmark_results_by_split: dict[str, BenchmarkRunResult],
) -> dict[str, object]:
    split_payloads = [
        _build_split_artifact(
            split_name=split_name,
            episodes=episodes_by_split[split_name],
            benchmark_result=benchmark_results_by_split[split_name],
            prompt_modes=prompt_modes,
        )
        for split_name, _episode_count in release_report.split_episode_counts
    ]
    return {
        "release_id": release_report.release_id,
        "provider_name": provider_name,
        "model_name": model_name,
        "prompt_modes": [mode.value for mode in prompt_modes],
        "splits": split_payloads,
        "failure_taxonomy": _build_failure_taxonomy(
            split_payloads, prompt_modes
        ),
        "diagnostic_summary": _build_diagnostic_summary(
            split_payloads, prompt_modes
        ),
        "diagnostic_episode_rows": _build_diagnostic_episode_rows(
            split_payloads, prompt_modes
        ),
    }


def _build_split_artifact(
    *,
    split_name: str,
    episodes: tuple[Episode, ...],
    benchmark_result: BenchmarkRunResult,
    prompt_modes: tuple[ModelMode, ...],
) -> dict[str, object]:
    mode_rows = {
        mode_result.mode: mode_result.rows
        for mode_result in benchmark_result.mode_results
    }
    for mode in prompt_modes:
        if mode not in mode_rows:
            continue
        if len(mode_rows[mode]) != len(episodes):
            raise ValueError(
                f"{mode.value} rows must contain exactly {len(episodes)} entries for split {split_name!r}"
            )

    rows: list[dict[str, object]] = []
    for index, episode in enumerate(episodes):
        mode_payloads: dict[str, object] = {}
        paired_episode_id: str | None = None
        paired_targets: tuple[object, ...] | None = None
        for mode in prompt_modes:
            if mode not in mode_rows:
                continue
            row = mode_rows[mode][index]
            if row.episode_id != episode.episode_id:
                raise ValueError(
                    f"{mode.value} row order must match frozen episode order on split {split_name!r}"
                )
            if tuple(row.target) != tuple(episode.probe_targets):
                raise ValueError(
                    f"{mode.value} targets must match frozen probe targets on split {split_name!r}"
                )
            if paired_episode_id is None:
                paired_episode_id = row.episode_id
            elif row.episode_id != paired_episode_id:
                raise ValueError(
                    f"paired Binary/Narrative rows must reference the same episode on split {split_name!r}"
                )
            if paired_targets is None:
                paired_targets = tuple(row.target)
            elif tuple(row.target) != paired_targets:
                raise ValueError(
                    f"paired Binary/Narrative rows must share the same probe targets on split {split_name!r}"
                )
            mode_payloads[mode.value] = _build_mode_row_payload(
                row=row, episode=episode
            )

        rows.append(
            {
                "episode_id": episode.episode_id,
                "template_id": episode.template_id.value,
                "difficulty": episode.difficulty.value,
                "transition": episode.transition.value,
                "probe_targets": [
                    label.value for label in episode.probe_targets
                ],
                "modes": mode_payloads,
            }
        )

    return {
        "split_name": split_name,
        "episode_count": len(episodes),
        "pairing_checks": {
            "same_episode_order": True,
            "same_probe_targets": True,
        },
        "rows": rows,
    }


def _build_mode_row_payload(
    *,
    row: BenchmarkModeRunRow,
    episode: Episode,
) -> dict[str, object]:
    predicted_labels = tuple(row.parsed_prediction.labels)
    correct_probe_count = _count_correct_labels(row=row)
    old_rule_labels = tuple(
        metadata.old_rule_label for metadata in episode.probe_metadata
    )
    new_rule_labels = tuple(
        metadata.new_rule_label for metadata in episode.probe_metadata
    )
    has_runtime_error = row.execution.raw_result.error_type is not None
    is_parse_failure = (
        not has_runtime_error
        and row.parsed_prediction.status is ParseStatus.INVALID
    )
    is_adaptation_failure = (
        row.parsed_prediction.status is ParseStatus.VALID
        and correct_probe_count < len(episode.probe_targets)
    )
    exact_global_old_rule_persistence = (
        is_adaptation_failure and predicted_labels == old_rule_labels
    )
    exact_global_recency_overshoot = (
        is_adaptation_failure and predicted_labels == new_rule_labels
    )
    possible_old_rule_persistence = (
        exact_global_old_rule_persistence
        and predicted_labels == never_update_baseline(episode)
    )
    possible_recency_overshoot = (
        exact_global_recency_overshoot
        and predicted_labels == last_evidence_baseline(episode)
    )
    (
        error_probe_count,
        old_rule_error_probe_count,
        recency_overshoot_error_probe_count,
        disagreement_profile,
    ) = _build_disagreement_diagnostics(
        predicted_labels=predicted_labels,
        target=tuple(episode.probe_targets),
        probe_metadata=episode.probe_metadata,
        is_adaptation_failure=is_adaptation_failure,
    )
    if has_runtime_error:
        failure_bucket = "runtime_error"
    elif is_parse_failure:
        failure_bucket = "parse_failure"
    elif is_adaptation_failure:
        failure_bucket = "adaptation_failure"
    else:
        failure_bucket = "correct"

    return {
        "parse_status": row.parsed_prediction.status.value,
        "predicted_labels": [label.value for label in predicted_labels],
        "correct_probe_count": correct_probe_count,
        "failure_bucket": failure_bucket,
        "possible_old_rule_persistence": possible_old_rule_persistence,
        "possible_recency_overshoot": possible_recency_overshoot,
        "exact_global_old_rule_persistence": exact_global_old_rule_persistence,
        "exact_global_recency_overshoot": exact_global_recency_overshoot,
        "error_probe_count": error_probe_count,
        "old_rule_error_probe_count": old_rule_error_probe_count,
        "recency_overshoot_error_probe_count": recency_overshoot_error_probe_count,
        "disagreement_profile": disagreement_profile,
        "error_type": row.execution.raw_result.error_type,
        "error_message": row.execution.raw_result.error_message,
        "response_text": row.execution.raw_result.response_text,
        "finish_reason": row.execution.raw_result.finish_reason,
    }


def _count_correct_labels(*, row: BenchmarkModeRunRow) -> int:
    if row.parsed_prediction.status is not ParseStatus.VALID:
        return 0
    return sum(
        predicted_label is target_label
        for predicted_label, target_label in zip(
            row.parsed_prediction.labels, row.target
        )
    )


def _build_failure_taxonomy(
    split_payloads: list[dict[str, object]],
    prompt_modes: tuple[ModelMode, ...],
) -> list[dict[str, object]]:
    taxonomy_rows = _build_failure_taxonomy_for_scope(
        scope_name="overall",
        scoped_split_payloads=split_payloads,
        prompt_modes=prompt_modes,
    )
    for split_payload in split_payloads:
        taxonomy_rows.extend(
            _build_failure_taxonomy_for_scope(
                scope_name=str(split_payload["split_name"]),
                scoped_split_payloads=[split_payload],
                prompt_modes=prompt_modes,
            )
        )
    return taxonomy_rows


def _build_failure_taxonomy_for_scope(
    *,
    scope_name: str,
    scoped_split_payloads: list[dict[str, object]],
    prompt_modes: tuple[ModelMode, ...],
) -> list[dict[str, object]]:
    scope_rows: list[dict[str, object]] = []
    for mode in prompt_modes:
        mode_name = TASK_MODE_LABELS[mode]
        mode_rows = [
            mode_payload
            for split_payload in scoped_split_payloads
            for row in split_payload["rows"]
            for mode_key, mode_payload in row["modes"].items()
            if mode_key == mode.value
        ]
        episode_count = len(mode_rows)
        if episode_count == 0:
            continue
        runtime_error_count = sum(
            mode_row["failure_bucket"] == "runtime_error"
            for mode_row in mode_rows
        )
        parse_failure_count = sum(
            mode_row["failure_bucket"] == "parse_failure"
            for mode_row in mode_rows
        )
        adaptation_failure_count = sum(
            mode_row["failure_bucket"] == "adaptation_failure"
            for mode_row in mode_rows
        )
        possible_old_rule_persistence_count = sum(
            bool(mode_row["possible_old_rule_persistence"])
            for mode_row in mode_rows
        )
        possible_recency_overshoot_count = sum(
            bool(mode_row["possible_recency_overshoot"])
            for mode_row in mode_rows
        )
        scope_rows.append(
            {
                "scope": scope_name,
                "mode": mode_name,
                "episode_count": episode_count,
                "runtime_error_rate": runtime_error_count / episode_count,
                "parse_failure_rate": parse_failure_count / episode_count,
                "adaptation_failure_rate": adaptation_failure_count
                / episode_count,
                "possible_old_rule_persistence_rate": (
                    possible_old_rule_persistence_count / episode_count
                ),
                "possible_recency_overshoot_rate": (
                    possible_recency_overshoot_count / episode_count
                ),
            }
        )
    return scope_rows


def _build_disagreement_diagnostics(
    *,
    predicted_labels: tuple[object, ...],
    target: tuple[object, ...],
    probe_metadata: tuple[object, ...],
    is_adaptation_failure: bool,
) -> tuple[int, int, int, str | None]:
    if not is_adaptation_failure:
        return 0, 0, 0, None

    error_probe_count = 0
    old_rule_error_probe_count = 0
    recency_overshoot_error_probe_count = 0
    for predicted_label, target_label, metadata in zip(
        predicted_labels,
        target,
        probe_metadata,
    ):
        if predicted_label is target_label:
            continue
        error_probe_count += 1
        if predicted_label is metadata.old_rule_label:
            old_rule_error_probe_count += 1
        elif predicted_label is metadata.new_rule_label:
            recency_overshoot_error_probe_count += 1

    disagreement_profile: str
    if (
        old_rule_error_probe_count > 0
        and recency_overshoot_error_probe_count > 0
    ):
        disagreement_profile = "mixed"
    elif old_rule_error_probe_count > 0:
        disagreement_profile = "old_rule_only"
    elif recency_overshoot_error_probe_count > 0:
        disagreement_profile = "recency_overshoot_only"
    else:
        disagreement_profile = "other"

    return (
        error_probe_count,
        old_rule_error_probe_count,
        recency_overshoot_error_probe_count,
        disagreement_profile,
    )


def _build_diagnostic_summary(
    split_payloads: list[dict[str, object]],
    prompt_modes: tuple[ModelMode, ...],
) -> list[dict[str, object]]:
    summary_rows = _build_diagnostic_summary_for_scope(
        scope_type="overall",
        scope_label="overall",
        scoped_rows=[
            {
                "split_name": split_payload["split_name"],
                **row,
            }
            for split_payload in split_payloads
            for row in split_payload["rows"]
        ],
        prompt_modes=prompt_modes,
    )

    for split_payload in split_payloads:
        split_name = str(split_payload["split_name"])
        summary_rows.extend(
            _build_diagnostic_summary_for_scope(
                scope_type="split",
                scope_label=split_name,
                scoped_rows=[
                    {
                        "split_name": split_name,
                        **row,
                    }
                    for row in split_payload["rows"]
                ],
                prompt_modes=prompt_modes,
            )
        )

    for scope_type, key_name, labels in (
        ("template", "template_id", _ordered_scope_labels(split_payloads, "template_id")),
        ("difficulty", "difficulty", _ordered_scope_labels(split_payloads, "difficulty")),
        ("transition", "transition", _ordered_scope_labels(split_payloads, "transition")),
    ):
        for label in labels:
            summary_rows.extend(
                _build_diagnostic_summary_for_scope(
                    scope_type=scope_type,
                    scope_label=label,
                    scoped_rows=[
                        {
                            "split_name": split_payload["split_name"],
                            **row,
                        }
                        for split_payload in split_payloads
                        for row in split_payload["rows"]
                        if row[key_name] == label
                    ],
                    prompt_modes=prompt_modes,
                )
            )

    return summary_rows


def _ordered_scope_labels(
    split_payloads: list[dict[str, object]],
    key_name: str,
) -> tuple[str, ...]:
    discovered_labels = tuple(
        str(row[key_name])
        for split_payload in split_payloads
        for row in split_payload["rows"]
    )
    if key_name == "template_id":
        order = ("T1", "T2")
    elif key_name == "difficulty":
        order = ("easy", "medium", "hard")
    elif key_name == "transition":
        order = _TRANSITION_ORDER
    else:
        order = ()
    return tuple(label for label in order if label in discovered_labels)


def _build_diagnostic_summary_for_scope(
    *,
    scope_type: str,
    scope_label: str,
    scoped_rows: list[dict[str, object]],
    prompt_modes: tuple[ModelMode, ...],
) -> list[dict[str, object]]:
    summary_rows: list[dict[str, object]] = []
    for mode in prompt_modes:
        mode_rows = [
            mode_payload
            for row in scoped_rows
            for mode_key, mode_payload in row["modes"].items()
            if mode_key == mode.value
        ]
        episode_count = len(mode_rows)
        if episode_count == 0:
            continue

        runtime_error_count = sum(
            mode_row["failure_bucket"] == "runtime_error"
            for mode_row in mode_rows
        )
        parse_failure_count = sum(
            mode_row["failure_bucket"] == "parse_failure"
            for mode_row in mode_rows
        )
        parse_valid_count = sum(
            mode_row["parse_status"] == ParseStatus.VALID.value
            for mode_row in mode_rows
        )
        correct_count = sum(
            mode_row["failure_bucket"] == "correct"
            for mode_row in mode_rows
        )
        adaptation_failure_count = sum(
            mode_row["failure_bucket"] == "adaptation_failure"
            for mode_row in mode_rows
        )
        parse_attempted_count = episode_count - runtime_error_count
        exact_global_old_rule_persistence_count = sum(
            bool(mode_row["exact_global_old_rule_persistence"])
            for mode_row in mode_rows
        )
        exact_global_recency_overshoot_count = sum(
            bool(mode_row["exact_global_recency_overshoot"])
            for mode_row in mode_rows
        )
        old_rule_only_count = sum(
            mode_row["disagreement_profile"] == "old_rule_only"
            for mode_row in mode_rows
        )
        recency_overshoot_only_count = sum(
            mode_row["disagreement_profile"] == "recency_overshoot_only"
            for mode_row in mode_rows
        )
        mixed_disagreement_count = sum(
            mode_row["disagreement_profile"] == "mixed"
            for mode_row in mode_rows
        )
        other_disagreement_count = sum(
            mode_row["disagreement_profile"] == "other"
            for mode_row in mode_rows
        )
        error_probe_count = sum(
            int(mode_row["error_probe_count"]) for mode_row in mode_rows
        )
        old_rule_error_probe_count = sum(
            int(mode_row["old_rule_error_probe_count"])
            for mode_row in mode_rows
        )
        recency_overshoot_error_probe_count = sum(
            int(mode_row["recency_overshoot_error_probe_count"])
            for mode_row in mode_rows
        )

        summary_rows.append(
            {
                "scope_type": scope_type,
                "scope_label": scope_label,
                "mode": TASK_MODE_LABELS[mode],
                "episode_count": episode_count,
                "runtime_error_count": runtime_error_count,
                "runtime_error_rate": runtime_error_count / episode_count,
                "parse_attempted_count": parse_attempted_count,
                "parse_attempted_rate": parse_attempted_count / episode_count,
                "parse_failure_count": parse_failure_count,
                "parse_failure_rate": parse_failure_count / episode_count,
                "parse_valid_count": parse_valid_count,
                "parse_valid_rate": parse_valid_count / episode_count,
                "correct_count": correct_count,
                "correct_rate": correct_count / episode_count,
                "adaptation_failure_count": adaptation_failure_count,
                "adaptation_failure_rate": adaptation_failure_count
                / episode_count,
                "adaptation_failure_rate_among_parse_valid": (
                    adaptation_failure_count / parse_valid_count
                    if parse_valid_count
                    else 0.0
                ),
                "exact_global_old_rule_persistence_count": (
                    exact_global_old_rule_persistence_count
                ),
                "exact_global_old_rule_persistence_rate": (
                    exact_global_old_rule_persistence_count / episode_count
                ),
                "exact_global_old_rule_persistence_rate_among_adaptation_failures": (
                    exact_global_old_rule_persistence_count
                    / adaptation_failure_count
                    if adaptation_failure_count
                    else 0.0
                ),
                "exact_global_recency_overshoot_count": (
                    exact_global_recency_overshoot_count
                ),
                "exact_global_recency_overshoot_rate": (
                    exact_global_recency_overshoot_count / episode_count
                ),
                "exact_global_recency_overshoot_rate_among_adaptation_failures": (
                    exact_global_recency_overshoot_count
                    / adaptation_failure_count
                    if adaptation_failure_count
                    else 0.0
                ),
                "old_rule_only_count": old_rule_only_count,
                "recency_overshoot_only_count": recency_overshoot_only_count,
                "mixed_disagreement_count": mixed_disagreement_count,
                "other_disagreement_count": other_disagreement_count,
                "error_probe_count": error_probe_count,
                "old_rule_error_probe_count": old_rule_error_probe_count,
                "recency_overshoot_error_probe_count": (
                    recency_overshoot_error_probe_count
                ),
                "old_rule_error_probe_rate": (
                    old_rule_error_probe_count / error_probe_count
                    if error_probe_count
                    else 0.0
                ),
                "recency_overshoot_error_probe_rate": (
                    recency_overshoot_error_probe_count / error_probe_count
                    if error_probe_count
                    else 0.0
                ),
            }
        )

    return summary_rows


def _build_diagnostic_episode_rows(
    split_payloads: list[dict[str, object]],
    prompt_modes: tuple[ModelMode, ...],
) -> list[dict[str, object]]:
    diagnostic_rows: list[dict[str, object]] = []
    for split_payload in split_payloads:
        split_name = str(split_payload["split_name"])
        for row in split_payload["rows"]:
            for mode in prompt_modes:
                mode_payload = row["modes"].get(mode.value)
                if mode_payload is None:
                    continue
                if mode_payload["failure_bucket"] == "correct":
                    continue
                diagnostic_rows.append(
                    {
                        "split_name": split_name,
                        "episode_id": row["episode_id"],
                        "template_id": row["template_id"],
                        "difficulty": row["difficulty"],
                        "transition": row["transition"],
                        "mode": TASK_MODE_LABELS[mode],
                        "parse_status": mode_payload["parse_status"],
                        "failure_bucket": mode_payload["failure_bucket"],
                        "correct_probe_count": mode_payload["correct_probe_count"],
                        "error_probe_count": mode_payload["error_probe_count"],
                        "old_rule_error_probe_count": mode_payload[
                            "old_rule_error_probe_count"
                        ],
                        "recency_overshoot_error_probe_count": mode_payload[
                            "recency_overshoot_error_probe_count"
                        ],
                        "exact_global_old_rule_persistence": mode_payload[
                            "exact_global_old_rule_persistence"
                        ],
                        "exact_global_recency_overshoot": mode_payload[
                            "exact_global_recency_overshoot"
                        ],
                        "disagreement_profile": mode_payload[
                            "disagreement_profile"
                        ],
                        "error_type": mode_payload["error_type"],
                    }
                )
    return diagnostic_rows


def _build_live_execution_notes(
    artifact_payload: dict[str, object],
) -> list[str]:
    diagnostic_rows = tuple(artifact_payload.get("diagnostic_summary", ()))
    if not diagnostic_rows:
        return []

    overall_rows = [
        row
        for row in diagnostic_rows
        if isinstance(row, dict)
        and row.get("scope_type") == "overall"
        and row.get("scope_label") == "overall"
    ]
    if not overall_rows:
        return []

    notes: list[str] = []
    if any(
        float(row.get("runtime_error_rate", 0.0)) > 0.0
        for row in overall_rows
    ):
        notes.extend(
            [
                "",
                "## Live Execution Review",
                "",
            ]
        )
        if any(
            float(row.get("runtime_error_rate", 0.0)) >= 1.0
            for row in overall_rows
        ):
            notes.append(
                "All outputs in at least one prompt mode failed at the provider/runtime stage, so this run is not interpretable as a robustness finding and requires a rerun."
            )
        else:
            notes.append(
                "Provider/runtime failures were observed in the live run. Review them separately from true parse/format failures before drawing benchmark conclusions."
            )
    if any(
        float(row.get("parse_failure_rate", 0.0)) > 0.0
        and float(row.get("parse_failure_rate", 0.0))
        >= float(row.get("adaptation_failure_rate", 0.0))
        for row in overall_rows
    ):
        if not notes:
            notes.extend(["", "## Live Execution Review", ""])
        notes.append(
            "Parse/format failures dominate at least one prompt mode in this run. Read low accuracy in that mode as a formatting/contract issue first, then inspect adaptation only within parse-valid outputs."
        )
    if any(
        int(row.get("adaptation_failure_count", 0)) > 0
        and int(row.get("parse_valid_count", 0)) > 0
        for row in overall_rows
    ):
        if not notes:
            notes.extend(["", "## Live Execution Review", ""])
        notes.append(
            "At least one prompt mode has parse-valid outputs that still miss post-shift probes. Those misses are diagnostic-only adaptation evidence, not new benchmark scoring."
        )
    return notes


def _format_count_rate(count: int, total: int) -> str:
    rate = count / total if total else 0.0
    return f"{count}/{total} ({rate:.6f})"


def _pick_primary_summary(
    model_summaries: tuple[ReleaseAuditSourceSummary, ...],
    prompt_modes: tuple[ModelMode, ...],
) -> ReleaseAuditSourceSummary:
    if ModelMode.BINARY in prompt_modes:
        for summary in model_summaries:
            if summary.task_mode == "Binary":
                return summary
    return model_summaries[0]


def _pick_mode_summary(
    model_summaries: tuple[ReleaseAuditSourceSummary, ...],
    *,
    task_mode: str,
) -> ReleaseAuditSourceSummary | None:
    for summary in model_summaries:
        if summary.task_mode == task_mode:
            return summary
    return None


def _pick_matched_mode_comparison(
    release_report: ReleaseAuditReport,
    *,
    source_family: str,
) -> MatchedModeComparisonSummary | None:
    for comparison in release_report.matched_mode_comparisons:
        if comparison.source_family == source_family:
            return comparison
    return None


def _build_mode_comparison_from_split_summaries(
    binary_split_summary,
    narrative_split_summary,
) -> ModeComparisonSummary:
    return ModeComparisonSummary(
        binary_accuracy=binary_split_summary.accuracy,
        narrative_accuracy=narrative_split_summary.accuracy,
        accuracy_gap=binary_split_summary.accuracy
        - narrative_split_summary.accuracy,
        binary_parse_valid_rate=binary_split_summary.parse_valid_rate,
        narrative_parse_valid_rate=narrative_split_summary.parse_valid_rate,
        parse_valid_rate_gap=(
            binary_split_summary.parse_valid_rate
            - narrative_split_summary.parse_valid_rate
        ),
    )


def _render_mode_comparison_row(
    scope: str,
    comparison: ModeComparisonSummary,
) -> str:
    return (
        f"| {scope} | {comparison.binary_accuracy:.6f} | "
        f"{comparison.narrative_accuracy:.6f} | {comparison.accuracy_gap:.6f} | "
        f"{comparison.binary_parse_valid_rate:.6f} | "
        f"{comparison.narrative_parse_valid_rate:.6f} |"
    )


def _render_mode_slice_row(
    slice_type: str,
    label: str,
    comparison: ModeComparisonSummary,
) -> str:
    return (
        f"| {slice_type} | {label} | {comparison.binary_accuracy:.6f} | "
        f"{comparison.narrative_accuracy:.6f} | {comparison.accuracy_gap:.6f} | "
        f"{comparison.binary_parse_valid_rate:.6f} | "
        f"{comparison.narrative_parse_valid_rate:.6f} |"
    )


def _diagnostic_rows_for_markdown(
    diagnostic_summary_rows: tuple[object, ...],
    *,
    scope_types: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    scope_rank = {
        "overall": 0,
        "split": 1,
        "template": 2,
        "difficulty": 3,
        "transition": 4,
    }
    split_rank = {
        "dev": 0,
        "public_leaderboard": 1,
        "private_leaderboard": 2,
    }
    template_rank = {"T1": 0, "T2": 1}
    difficulty_rank = {"easy": 0, "medium": 1, "hard": 2}
    transition_rank = {
        transition: index
        for index, transition in enumerate(_TRANSITION_ORDER)
    }

    def _label_rank(row: dict[str, object]) -> tuple[int, str]:
        scope_type = str(row["scope_type"])
        label = str(row["scope_label"])
        if scope_type == "split":
            return split_rank.get(label, 999), label
        if scope_type == "template":
            return template_rank.get(label, 999), label
        if scope_type == "difficulty":
            return difficulty_rank.get(label, 999), label
        if scope_type == "transition":
            return transition_rank.get(label, 999), label
        return 0, label

    filtered_rows = tuple(
        row
        for row in diagnostic_summary_rows
        if isinstance(row, dict) and row.get("scope_type") in scope_types
    )
    return tuple(
        sorted(
            filtered_rows,
            key=lambda row: (
                scope_rank.get(str(row["scope_type"]), 999),
                _label_rank(row),
                str(row["mode"]),
            ),
        )
    )


def _format_scope_label(row: dict[str, object]) -> str:
    if str(row["scope_type"]) == "overall":
        return "overall"
    return str(row["scope_label"])
