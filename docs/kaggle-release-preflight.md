# Kaggle Release Preflight

Use this checklist before publishing a new Kaggle runtime dataset or notebook bundle.

## Structural Invariants

- The only leaderboard-primary task is `ruleshift_benchmark_v1_binary`.
- The final notebook selection cell is `%choose ruleshift_benchmark_v1_binary`.
- The row task remains internal-only with `store_task=False`.
- Audit views remain notebook-only and derived from `public_leaderboard`.
- Split inventory remains:
  - `public_leaderboard = 54`
  - `private_leaderboard = 270`
- `private_leaderboard` stays out of the public runtime dataset package.

## Datasource Assumptions

- Public Kaggle notebook metadata references only `raptorengineer/ruleshift-runtime`.
- Public runs evaluate `54` episodes from `public_leaderboard`.
- Private holdout runs require an attached `private_episodes.json` mount via `RULESHIFT_PRIVATE_DATASET_ROOT`.
- Public + private attached runs evaluate `324` episodes total.

## Local Release Gate

Run:

```bash
./scripts/pre_deploy_check.sh
```

The gate must pass all phases:

- environment sanity
- staging manifest validation
- local Kaggle preflight
- runtime contract tests
- notebook and packaging tests
- runtime dataset build validation
- kernel bundle build validation

## Version Coherence

Publish runtime dataset and notebook bundle from the same repo state.

Verify these stay aligned:

- `packaging/kaggle/frozen_artifacts_manifest.json`
- `packaging/kaggle/kernel-metadata.json`
- `packaging/kaggle/dataset-metadata.json`
- `src/frozen_splits/public_leaderboard.json`

Current public release identifiers:

- dataset id: `raptorengineer/ruleshift-runtime`
- notebook id: `raptorengineer/ruleshift-notebook`
- public seed bank version: `R14-public-5`
- benchmark manifest version: `R14`

## Publish Sequence

1. Run `./scripts/pre_deploy_check.sh`.
2. Build the runtime dataset package.
3. Build the kernel bundle.
4. Publish the runtime dataset.
5. Publish or update the notebook bundle built from the same repo state.
6. For private validation only, build and attach the hidden private dataset separately.

## Final Kaggle Readiness Notes

- The official return contract is still the leaderboard-safe tuple `(numerator, denominator)`.
- Audit tables are present for episode inspection, balance review, and failure analysis without changing the official Kaggle output.
- Public is the audit surface. Private remains the hidden holdout dataset.
