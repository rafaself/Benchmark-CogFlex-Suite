# RuleShift Benchmark v1 Frozen Benchmark Specification

> **Status: NORMATIVE FROZEN SPECIFICATION**
> This document is the single benchmark-definition authority for the current RuleShift Benchmark v1 release.
> Supporting documents must mirror this methodology exactly and must not widen scope beyond the current cognitive flexibility benchmark.

## Benchmark Identity

- Benchmark name: `RuleShift Benchmark v1`
- Benchmark scope: cognitive flexibility
- Task ID: `ruleshift_benchmark_v1`
- Frozen semantic versions:
  - `spec_version = v1`
  - `manifest/benchmark_version = R14`
  - `generator_version = R13`
  - `template_set_version = v2`
  - `difficulty_version = R13`

RuleShift Benchmark v1 is a narrow Executive Functions benchmark for cognitive flexibility. It uses electrostatics only as a controlled substrate for evaluating final post-shift rule application after sparse contradictory evidence. It does not define any broader ability scope.

## Leaderboard And Audit Contract

- Binary (`ruleshift_benchmark_v1_binary`) is the only leaderboard-facing and leaderboard-scored task.
- Narrative is structured audit output and same-episode robustness evidence only.
- Narrative uses the same frozen episodes, same episode order, and same probe targets as Binary.
- Only the final four labels are scored in both modes.
- Narrative does not contribute to the leaderboard score.
- Aggregate accuracy remains available through Binary `primary_result` / Post-shift Probe Accuracy.

## Episode And Rule Contract

Each frozen episode contains:

- 5 labeled items
- 4 unlabeled probes
- a pre-shift segment governed by `rule_A`
- a post-shift segment governed by `rule_B`

The frozen rule family is:

- `R_std`: same-sign charges repel, opposite-sign charges attract
- `R_inv`: same-sign charges attract, opposite-sign charges repel

Charge values come from `{-3, -2, -1, +1, +2, +3}`. Labels depend on charge sign, not magnitude, and pair order does not change the correct label.

## Frozen Methodology Axes

- Template IDs: `T1`, `T2`
- Template-family axis: `canonical`, `observation_log`
- Transition types: `R_std_to_R_inv`, `R_inv_to_R_std`
- Difficulty labels currently emitted: `easy`, `medium`, `hard`
- Reserved difficulty labels currently emitted by manifest: none

Difficulty is generation-defined under `R13` difficulty derivation and is reported diagnostically. Difficulty does not create a separate leaderboard task and does not change the Binary headline metric.

Required benchmark-facing slice/report dimensions are:

- `template`
- `template_family`
- `difficulty`
- `shift_position`
- `transition_type`
- `error_type`

Invariance reporting is diagnostic-only. When emitted, it must be reproducible and versioned, and it must not change the Binary leaderboard score or create a new leaderboard-facing ability claim.

## Structural Holdout Policy

Frozen split names are exactly:

- `dev`
- `public_leaderboard`
- `private_leaderboard`

Policy:

- `dev` is local-only and never part of official leaderboard scoring.
- Official leaderboard scoring uses Binary over `public_leaderboard` and `private_leaderboard`.
- `private_leaderboard` is structurally held out.
- The public repository and public Kaggle runtime package must never contain `private_episodes.json` or any repo-local private fallback.
- Private evaluation data must come only from an authorized private dataset mount.
- Public frozen artifacts are `src/frozen_splits/dev.json` and `src/frozen_splits/public_leaderboard.json`.
- Private artifact handling must remain offline/publicly isolated and follow `PRIVATE_SPLIT_RUNBOOK.md`.

## Reproducibility And Artifacts

- `src/` and the frozen split manifests under `src/frozen_splits/` are the executable source of truth.
- `packaging/kaggle/frozen_artifacts_manifest.json` is the Kaggle runtime-contract manifest for the frozen public runtime package.
- Required local benchmark validity/audit surfaces remain reproducible from committed code and frozen assets.
- Historical evidence under `reports/.../history/` is immutable record material, not a surface for silent methodology rewrites.
- Canonical current `latest/` artifacts and report expectations must reflect the frozen versions above.

## Non-Claims

This frozen benchmark specification does **not** claim to measure:

- physics skill as the primary ability
- broad adaptation ability
- broad AGI capability
- full executive-function decomposition
- online detection latency
- switch cost
- recovery length
- immediate post-shift drop
- any ability outside the current cognitive flexibility benchmark
