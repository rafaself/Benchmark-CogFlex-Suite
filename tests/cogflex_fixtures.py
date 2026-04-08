from __future__ import annotations

import json
from pathlib import Path

from scripts.build_cogflex_dataset import (
    PRIVATE_ANSWER_KEY_FILENAME,
    PRIVATE_BUNDLE_VERSION,
    PRIVATE_QUALITY_REPORT_FILENAME,
    PRIVATE_QUALITY_REPORT_VERSION,
    PRIVATE_RELEASE_MANIFEST_FILENAME,
    PRIVATE_ROWS_FILENAME,
    build_public_artifacts,
    compute_sha256,
)


def public_fixture() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    return build_public_artifacts()


def _private_turns(turns: list[str], marker: str) -> list[str]:
    adjusted: list[str] = []
    for turn_index, turn in enumerate(turns, start=1):
        parts = turn.split("\n\n", 2)
        if len(parts) < 2:
            adjusted.append(turn)
            continue
        header = parts[0]
        body = "\n\n".join(parts[1:])
        adjusted.append(f"{header}\n\nPrivate calibration marker {marker} turn_{turn_index}.\n\n{body}")
    return adjusted


def write_private_bundle(bundle_dir: Path) -> dict[str, Path]:
    public_rows, _public_answers, _public_report = public_fixture()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    private_rows: list[dict[str, object]] = []
    answer_episodes: list[dict[str, object]] = []
    episode_counter = 1
    for replica in range(4):
        for row in public_rows:
            episode_id = f"{episode_counter:04d}"
            marker = f"replica_{replica + 1}_{episode_id}"
            turns = _private_turns(list(row["inference"]["turns"]), marker)
            for turn_index, turn in enumerate(turns, start=1):
                old = f"Episode {row['episode_id']}. Turn {turn_index} of 3."
                new = f"Episode {episode_id}. Turn {turn_index} of 3."
                turns[turn_index - 1] = turn.replace(old, new)
            private_rows.append(
                {
                    "episode_id": episode_id,
                    "inference": {"turns": turns},
                    "analysis": dict(row["analysis"]),
                }
            )
            answer_episodes.append(
                {
                    "episode_id": episode_id,
                    "faculty_id": row["analysis"]["faculty_id"],
                    "suite_task_id": row["analysis"]["suite_task_id"],
                    "shift_mode": row["analysis"]["shift_mode"],
                    "difficulty_bin": row["analysis"]["difficulty_bin"],
                    "turns": turns,
                    "final_probe_targets": list(row["scoring"]["final_probe_targets"]),
                }
            )
            episode_counter += 1

    rows_path = bundle_dir / PRIVATE_ROWS_FILENAME
    answer_key_path = bundle_dir / PRIVATE_ANSWER_KEY_FILENAME
    quality_path = bundle_dir / PRIVATE_QUALITY_REPORT_FILENAME
    manifest_path = bundle_dir / PRIVATE_RELEASE_MANIFEST_FILENAME

    rows_path.write_text(json.dumps(private_rows, indent=2) + "\n", encoding="utf-8")
    answer_key_path.write_text(
        json.dumps(
            {
                "version": "cogflex_private_answer_key_v1",
                "split": "private",
                "episodes": answer_episodes,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    quality_path.write_text(
        json.dumps(
            {
                "version": PRIVATE_QUALITY_REPORT_VERSION,
                "split": "private",
                "row_count": 480,
                "episodes_per_task": 120,
                "difficulty_bin_counts": {"hard": 240, "medium": 240},
                "attack_suite": {
                    "dsl_search_accuracy": {
                        "micro_accuracy": 0.55,
                        "per_task_accuracy": {
                            "explicit_rule_update": 0.56,
                            "latent_rule_update": 0.54,
                            "context_binding": 0.55,
                            "trial_cued_switch": 0.55,
                        },
                    }
                },
                "calibration_summary": {
                    "models": [
                        {"name": "panel-model-a", "macro_accuracy": 0.61, "micro_accuracy": 0.60},
                        {"name": "panel-model-b", "macro_accuracy": 0.57, "micro_accuracy": 0.56},
                        {"name": "panel-model-c", "macro_accuracy": 0.52, "micro_accuracy": 0.51},
                    ]
                },
                "semantic_isolation_summary": {
                    "exact_public_overlap_count": 0,
                    "lexicon_overlap_count": 0,
                },
                "public_generator_commit_sha": "0" * 40,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "version": PRIVATE_BUNDLE_VERSION,
        "split": "private",
        "row_count": 480,
        "episodes_per_task": 120,
        "public_generator_commit_sha": "0" * 40,
        "lexicons": {
            "cue_terms": ["quartz", "sable", "lumen", "cinder"],
            "context_terms": ["mesa", "fjord", "delta", "tundra"],
        },
        "sha256": {
            PRIVATE_ROWS_FILENAME: compute_sha256(rows_path),
            PRIVATE_ANSWER_KEY_FILENAME: compute_sha256(answer_key_path),
            PRIVATE_QUALITY_REPORT_FILENAME: compute_sha256(quality_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "rows": rows_path,
        "answer_key": answer_key_path,
        "quality": quality_path,
        "manifest": manifest_path,
    }
