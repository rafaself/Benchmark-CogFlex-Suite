from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.audit import ReleaseAuditReport, ReleaseAuditSourceSummary, AuditSource, run_release_r15_reaudit
from core.model_execution import ModelMode, ModelRunConfig
from core.model_runner import run_model_benchmark
from core.providers.gemini import GeminiAdapter
from core.splits import PARTITIONS, load_frozen_split

__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_GEMINI_FIRST_PANEL_REPORT_PATH",
    "GeminiFirstPanelArtifacts",
    "run_gemini_first_panel",
    "render_gemini_first_panel_markdown",
]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_FIRST_PANEL_REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "reports" / "gemini_first_panel_report.md"
)
_DEFAULT_PANEL_MODES: tuple[ModelMode, ...] = (ModelMode.BINARY,)
_DEFAULT_PANEL_CONFIG = ModelRunConfig(
    timeout_seconds=60.0,
    temperature=0.0,
    thinking_budget=0,
)
_BASELINE_ORDER: tuple[str, ...] = (
    "random",
    "never_update",
    "last_evidence",
    "physics_prior",
    "template_position",
)
_TASK_MODE_LABELS = {
    ModelMode.BINARY: "Binary",
    ModelMode.NARRATIVE: "Narrative",
}


@dataclass(frozen=True, slots=True)
class GeminiFirstPanelArtifacts:
    provider_name: str
    model_name: str
    prompt_modes: tuple[ModelMode, ...]
    release_report: ReleaseAuditReport
    report_markdown: str
    report_path: Path


def run_gemini_first_panel(
    *,
    model_name: str = DEFAULT_GEMINI_MODEL,
    report_path: Path | None = None,
    modes: tuple[ModelMode, ...] = _DEFAULT_PANEL_MODES,
    config: ModelRunConfig = _DEFAULT_PANEL_CONFIG,
    adapter: GeminiAdapter | None = None,
) -> GeminiFirstPanelArtifacts:
    normalized_modes = tuple(ModelMode(mode) for mode in modes)
    if not normalized_modes:
        raise ValueError("modes must not be empty")
    if len(set(normalized_modes)) != len(normalized_modes):
        raise ValueError("modes must not contain duplicates")

    active_adapter = GeminiAdapter.from_env() if adapter is None else adapter
    episodes_by_split: dict[str, tuple[object, ...]] = {}
    model_sources_by_split: dict[str, tuple[AuditSource, ...]] = {}
    provider_name = "gemini"

    for split_name in PARTITIONS:
        episodes = tuple(record.episode for record in load_frozen_split(split_name))
        benchmark_result = run_model_benchmark(
            episodes,
            active_adapter,
            provider_name=provider_name,
            model_name=model_name,
            config=config,
            modes=normalized_modes,
        )
        episodes_by_split[split_name] = episodes
        model_sources_by_split[split_name] = tuple(
            AuditSource.from_parsed_predictions(
                f"{model_name} {_TASK_MODE_LABELS[mode_result.mode]}",
                tuple(row.parsed_prediction for row in mode_result.rows),
                task_mode=_TASK_MODE_LABELS[mode_result.mode],
                source_family=model_name,
                is_real_model=True,
            )
            for mode_result in benchmark_result.mode_results
        )

    release_report = run_release_r15_reaudit(
        episodes_by_split=episodes_by_split,
        model_sources_by_split=model_sources_by_split,
        release_id="R18",
    )
    report_markdown = render_gemini_first_panel_markdown(
        release_report,
        model_name=model_name,
        provider_name=provider_name,
        prompt_modes=normalized_modes,
    )
    resolved_report_path = (
        DEFAULT_GEMINI_FIRST_PANEL_REPORT_PATH if report_path is None else report_path
    )
    resolved_report_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_path.write_text(report_markdown, encoding="utf-8")

    return GeminiFirstPanelArtifacts(
        provider_name=provider_name,
        model_name=model_name,
        prompt_modes=normalized_modes,
        release_report=release_report,
        report_markdown=report_markdown,
        report_path=resolved_report_path,
    )


def render_gemini_first_panel_markdown(
    release_report: ReleaseAuditReport,
    *,
    model_name: str,
    provider_name: str,
    prompt_modes: tuple[ModelMode, ...],
) -> str:
    model_summaries = tuple(
        summary
        for summary in release_report.model_summaries
        if summary.source_family == model_name and summary.is_real_model
    )
    if not model_summaries:
        raise ValueError(f"no real-model summaries found for {model_name!r}")

    lines = [
        "# Gemini First Panel Report",
        "",
        f"- Release: {release_report.release_id}",
        f"- Provider: {provider_name}",
        f"- Model: {model_name}",
        f"- Prompt modes run: {', '.join(mode.value for mode in prompt_modes)}",
        f"- Covered splits: {', '.join(split_name for split_name, _ in release_report.split_episode_counts)}",
        "",
    ]

    primary_summary = _pick_primary_summary(model_summaries, prompt_modes)
    lines.extend(
        [
            "## Overall",
            "",
            f"- Post-shift Probe Accuracy: {primary_summary.overall.accuracy:.6f}",
            f"- Parse-valid rate: {primary_summary.overall.parse_valid_rate:.6f}",
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
            "## By Split",
            "",
            "| Split | Model | random | never-update | last-evidence | physics-prior | template-position |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    model_by_split = dict(primary_summary.by_split)
    baselines_by_name = {summary.name: summary for summary in release_report.baseline_summaries}
    for split_name, _episode_count in release_report.split_episode_counts:
        lines.append(
            f"| {split_name} | {model_by_split[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['random'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['never_update'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['last_evidence'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['physics_prior'].by_split)[split_name].accuracy:.6f} | "
            f"{dict(baselines_by_name['template_position'].by_split)[split_name].accuracy:.6f} |"
        )

    lines.extend(
        [
            "",
            "## By Template",
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
            "## By Difficulty",
            "",
            "| Difficulty | Accuracy | Parse-valid rate |",
            "| --- | ---: | ---: |",
        ]
    )
    for label, slice_summary in primary_summary.by_difficulty:
        lines.append(
            f"| {label} | {slice_summary.accuracy:.6f} | {slice_summary.parse_valid_rate:.6f} |"
        )

    if len(model_summaries) > 1:
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
        if "No matched Binary/Narrative model runs supplied" in limitation and ModelMode.NARRATIVE not in prompt_modes:
            continue
        lines.append(f"- {limitation}")

    return "\n".join(lines) + "\n"


def _pick_primary_summary(
    model_summaries: tuple[ReleaseAuditSourceSummary, ...],
    prompt_modes: tuple[ModelMode, ...],
) -> ReleaseAuditSourceSummary:
    if ModelMode.BINARY in prompt_modes:
        for summary in model_summaries:
            if summary.task_mode == "Binary":
                return summary
    return model_summaries[0]
