# Kaggle Release Preflight

Use this checklist before publishing a new Kaggle runtime dataset or notebook bundle.

## Structural Invariants

- The only leaderboard-primary task is `ruleshift_benchmark_v1_binary`.
- The final notebook selection cell is `%choose ruleshift_benchmark_v1_binary`.
- The row task remains internal-only with `store_task=False`.
- Audit views remain notebook-only display (`audit.py` is shipped in the runtime package; views are derived from `public_leaderboard`).
- Split inventory remains:
  - `public_leaderboard = 54`
  - `private_leaderboard = 270`
- `private_leaderboard` stays out of the public runtime dataset package.

## Datasource Assumptions

- Public Kaggle notebook metadata references only `raptorengineer/ruleshift-runtime`.
- Public runs evaluate `54` episodes from `public_leaderboard`.
- Private holdout runs require an attached `private_episodes.json` mount via `RULESHIFT_PRIVATE_DATASET_ROOT`.
- Public + private attached runs evaluate `324` episodes total.

## Local Release Validation

Run:

```bash
python -m scripts.deploy --skip-publish
```

This must rebuild both public Kaggle artifacts successfully from the current repo state.

## Version Coherence

Publish runtime dataset and notebook bundle from the same repo state.

Verify these stay aligned:

- `packaging/kaggle/frozen_artifacts_manifest.json`
- `packaging/kaggle/kernel-metadata.json`
- `packaging/kaggle/dataset-metadata.json`
- `src/frozen_splits/public_leaderboard.json`

Current public release identifiers:

- dataset id: `raptorengineer/ruleshift-runtime`
- notebook id: `raptorengineer/ruleshift-notebook-test`
- public seed bank version: `R14-public-5`
- benchmark manifest version: `R14`

## Publish Sequence

1. Run `python -m scripts.deploy --skip-publish`.
2. Publish with `python -m scripts.deploy --release-message "your Kaggle dataset version note"`.
3. For private validation only, build and attach the hidden private dataset separately.

## Final Kaggle Readiness Notes

- The official return contract is the 7-field payload from `build_kaggle_payload()`; the leaderboard-safe scoring tuple within it is `(numerator, denominator)`.
- Audit tables are present for episode inspection, balance review, and failure analysis without changing the official Kaggle output.
- Public is the audit surface. Private remains the hidden holdout dataset.
