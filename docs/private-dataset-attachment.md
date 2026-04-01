# Private Dataset Attachment

Date: 2026-04-01

Scope: operational note for the hidden `private_leaderboard` attachment used by local private validation and Kaggle runs with a mounted private datasource.

## Current Contract

- `public_leaderboard` stays checked in and public at `54` episodes.
- `private_leaderboard` stays external and attached at runtime at `270` episodes.
- The intended ratio is `5:1` (`270 private / 54 public`).
- The notebook logic is unchanged: it always evaluates public, and it appends private only when an authorized private dataset is attached.

## Build The Private Attachment

The private seed manifest is kept local and ignored at:

- `src/frozen_splits/private_leaderboard.json`

Build the mounted dataset artifact:

```bash
python3 scripts/build_private_dataset_artifact.py --output-dir /tmp/ruleshift-private-dataset
```

That command writes:

- `/tmp/ruleshift-private-dataset/private_episodes.json`

## Attach Locally

```bash
export RULESHIFT_PRIVATE_DATASET_ROOT=/tmp/ruleshift-private-dataset
```

## Expected Notebook Modes

Public only:

- `PRIVATE_DATASET_ROOT is None`
- split inventory: `public_leaderboard`
- evaluated episodes: `54`

Public + private attached:

- `PRIVATE_DATASET_ROOT` resolves to the mounted dataset root
- split inventory: `public_leaderboard`, `private_leaderboard`
- evaluated episodes: `324`

## Isolation Rules

- `scripts/build_runtime_dataset_package.py` may tolerate the canonical ignored local `src/frozen_splits/private_leaderboard.json`, but it must never copy that file or any `private_episodes.json` into the public runtime package.
- `packaging/kaggle/frozen_artifacts_manifest.json` must remain public-only.
- The notebook may discover private data, but the public runtime package must never contain it.
