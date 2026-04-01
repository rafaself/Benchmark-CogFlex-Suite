# Kaggle Benchmark Runtime Snapshot

Date: 2026-04-01

Scope: record the current Kaggle benchmark state for the simplified public/private split layout.

Observed repo state:

- Git commit: `8032bcac82cfbadc71a29bb8a4407953efd4bd73`
- Worktree note: there was a pre-existing modification in `.gitignore` during this audit.
- The public Kaggle path is built around one checked-in public leaderboard manifest plus an optional mounted private leaderboard artifact.
- The notebook evaluates the leaderboard path only.

## Current Split Inventory

| Partition | Source of truth | In repo | Current count | Manifest version | Seed bank version | Current role |
| --- | --- | --- | ---: | --- | --- | --- |
| `public_leaderboard` | `src/frozen_splits/public_leaderboard.json` | yes | 54 | `R14` | `R14-public-5` | public audit/eval split currently loaded by notebook |
| `private_leaderboard` | mounted `private_episodes.json` | no | 270 via attached artifact | `R14` | checksum-derived | optional attached private evaluation split |

Current split facts:

- `src/core/splits.py` declares `PARTITIONS = ("public_leaderboard", "private_leaderboard")`.
- `src/core/splits.py` declares `PUBLIC_PARTITIONS = ("public_leaderboard",)`.
- `packaging/kaggle/frozen_artifacts_manifest.json` contains only `public_leaderboard` under `frozen_split_manifests`.
- `src/core/kaggle/payload.py` accepts only leaderboard rows in the official payload path.
- `src/core/kaggle/runner.py` loads `public_leaderboard` always and adds `private_leaderboard` only when an authorized private dataset is attached.

## Current Notebook Contract

Notebook entry point:

- File: `packaging/kaggle/ruleshift_notebook_task.ipynb`
- Current file hash: `aa84a4f7b0d5238f6c280514461868e8066d243c3f0fea875ea219ad07b476fb`
- Kaggle kernel metadata points at `raptorengineer/ruleshift-notebook`
- Runtime dataset source is `raptorengineer/ruleshift-runtime`
- Notebook bootstrap expects runtime code at `/kaggle/input/datasets/raptorengineer/ruleshift-runtime/src`

Chosen main task:

- Official aggregate task: `ruleshift_benchmark_v1_binary`
- Row task exists as `_ruleshift_benchmark_v1_binary_row` with `store_task=False`
- Final selection cell is `%choose ruleshift_benchmark_v1_binary`
- Current benchmark remains Binary-first; there is no separate primary Narrative path

Current official payload contract:

- `score`
- `numerator`
- `denominator`
- `total_episodes`
- `benchmark_version`
- `split`
- `manifest_version`

Current payload behavior:

- Public-only local preflight currently produces `split = "public_leaderboard"` and `total_episodes = 1` for the sample row exercise.
- Full notebook execution with only public data produces `split = "public_leaderboard"` and currently evaluates 54 episodes.
- Full notebook execution with an attached private split produces `split = "frozen_leaderboard"` and currently evaluates 324 episodes in tests (`54 public + 270 private attached`).

## Packaging, Manifest, and Test Snapshot

Current Kaggle packaging files:

- `packaging/kaggle/ruleshift_notebook_task.ipynb`
- `packaging/kaggle/kernel-metadata.json`
- `packaging/kaggle/dataset-metadata.json`
- `packaging/kaggle/frozen_artifacts_manifest.json`

Current checked hashes:

- `packaging/kaggle/ruleshift_notebook_task.ipynb`: `bbcb0511399e68969216033fef570dba4683821afde675ec52a7bb8a0b3f3fec`
- `packaging/kaggle/dataset-metadata.json`: dataset id `raptorengineer/ruleshift-runtime`
- `packaging/kaggle/kernel-metadata.json`: `6432ccb5e3485bc3ab51a12f2348a86b9a40f191ce536fe44319525c9ee721da`
- `packaging/kaggle/frozen_artifacts_manifest.json`: public-only staging manifest for `public_leaderboard`
- `src/frozen_splits/public_leaderboard.json`: `685ae14767d9a0e6dafb24ca4bcfcd332469a8286402d7e8bd2ac9c68508df4a`

Current packaging behavior:

- `scripts/build_runtime_dataset_package.py` copies a runtime subset that includes only `src/frozen_splits/public_leaderboard.json` from the public split inventory.
- `scripts/build_runtime_dataset_package.py` excludes all private artifacts from the public runtime package and tolerates only the canonical ignored local `src/frozen_splits/private_leaderboard.json` in the workspace.
- `scripts/build_kernel_package.py` copies the notebook verbatim and verifies its hash against `packaging/kaggle/frozen_artifacts_manifest.json`.
- `src/core/kaggle/manifest.py` validates only `("public_leaderboard",)` as the staging manifest partitions.

Current validation status observed in this audit:

- `PYTHONPATH=src .venv/bin/python scripts/preflight_kaggle.py`: passed
- `.venv/bin/python -m pytest`: passed
- Result: 112 tests passed in the prepared `.venv` after the current public/private freeze updates.

## Current Known Risks

- Private evaluation is not reproducible from public repo contents alone because the authoritative private artifact is external and mount-based.
- The authoritative private seed manifest remains local/ignored, so public CI can validate only the attachment contract and isolation rules, not the hidden manifest contents.
- The notebook/runtime contract is tightly coupled to the current Kaggle dataset slug and mount path.

## Current Failing or Fragile Areas

- No functional failures were observed in the prepared project environment.
- `pytest` is not available directly on PATH in this shell.
- `python` is not available directly on PATH in this shell; `python3` is available.
- `python3 scripts/preflight_kaggle.py` fails in a bare shell because `core` is not importable unless the package is installed or `PYTHONPATH=src` is set.
- The private path is optional by design, so public-only runs and public+private runs exercise different evaluation scopes.
- Private attachment operations depend on a locally materialized `private_episodes.json`; see `docs/private-dataset-attachment.md`.

## Risks And Assumptions

- Assumption: the checked-in manifests and notebook are the canonical public/private split baseline to preserve.
- Assumption: Kaggle Benchmarks still expects the selected task to remain `%choose ruleshift_benchmark_v1_binary`.
- Risk: moving the public split to an audit-only surface changes operational expectations for preflight, notebook summaries, and packaging resources even if benchmark semantics stay fixed.

## Acceptance Criteria For The Full Implementation Cycle

- [ ] Set `public` to 54 episodes.
- [ ] Set `private` to 270 episodes.
- [ ] Make `public` the audit surface.
- [ ] Preserve Binary as the only leaderboard-primary task.
- [ ] Preserve the canonical Kaggle payload contract exactly.
- [ ] Keep private artifacts out of the public repo paths and public package outputs.
- [ ] Keep notebook, manifests, packaging scripts, and tests aligned to the same split inventory.
- [ ] Keep the baseline reproducible with explicit validation commands.

## Intended Target State

This snapshot records the current state only. The intended target state is:

- `public = 54`
- `private = 270`
- public becomes the audit surface
