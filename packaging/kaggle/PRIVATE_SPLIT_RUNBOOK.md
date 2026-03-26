# Private Split Runbook

> **Status: OPERATIONAL RUNBOOK**
> Minimum operational steps for the RuleShift v1 private split: generation, publication, and public isolation verification.
> For Kaggle packaging governance, see [`README.md`](./README.md).

## 1. Generate the Private Split Offline

Run `scripts/generate_private_split_artifact.py` from outside the public repository tree. The script enforces that the output path resolves outside the repo root.

```bash
python scripts/generate_private_split_artifact.py \
  --benchmark-version R14 \
  --seeds-file /path/to/private_seeds.json \
  --output /external/path/private_episodes.json
```

- `--benchmark-version` must be `R14` (the current `MANIFEST_VERSION`).
- `--seeds-file` is a JSON array of unique integers; keep this file outside the public repo.
- `--output` must resolve outside the repo root; the script rejects repo-internal paths.
- The artifact includes `artifact_checksum` (SHA-256 over the payload) for integrity verification.

## 2. Package and Publish the Private Artifact

Use `scripts/cd/build_private_dataset_package.py` to produce the private dataset package:

```bash
python scripts/cd/build_private_dataset_package.py \
  --artifact /external/path/private_episodes.json \
  --output-dir /external/path/private_dataset_package \
  --dataset-id <authorized-kaggle-dataset-id>
```

- `--output-dir` must be outside the public repo tree; the script enforces this.
- The output directory contains only `private_episodes.json` and `dataset-metadata.json`.
- Upload the output directory to the authorized private Kaggle dataset.
- Do not add `private_episodes.json` or the package directory to the public repo or public runtime package.

**To update an existing private artifact**: regenerate (step 1), repackage (this step), re-upload. The benchmark version `R14` is fixed for v1; do not change it without a corresponding benchmark version bump.

## 3. Verify the Public Runtime Has No Private Artifact

Run the isolation check before any public deploy:

```bash
python scripts/check_public_private_isolation.py
```

This check fails if any of the following are true:

- `private_episodes.json` exists anywhere inside the public repo tree
- `src/frozen_splits/private_leaderboard.json` exists
- `private_leaderboard` appears in `packaging/kaggle/frozen_artifacts_manifest.json`
- Any packaged notebook contains a repo-local private dataset fallback path

Also confirm the deploy build output is clean:

```bash
python scripts/build_deploy.py
python scripts/check_public_private_isolation.py
```

The `deploy/kaggle-runtime/` tree must contain only `dev.json` and `public_leaderboard.json` under `src/frozen_splits/`; it must not contain `private_episodes.json`.

## Verification Checklist

Before running private evaluation on Kaggle:

- [ ] `private_episodes.json` was generated with `--benchmark-version R14`
- [ ] `private_episodes.json` is stored exclusively outside the public repo tree
- [ ] `python scripts/check_public_private_isolation.py` exits with no errors
- [ ] `make integrity` passes
- [ ] `make test` passes
- [ ] The private dataset is attached as a separate Kaggle dataset mount, not bundled in the public runtime package
- [ ] `deploy/kaggle-runtime/` contains no `private_episodes.json` and no `private_leaderboard` entry
