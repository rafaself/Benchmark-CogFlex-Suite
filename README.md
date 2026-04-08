# CogFlex Suite Benchmark

Kaggle-oriented benchmark project for a targeted executive-functions suite:

- faculty: `executive_functions/cognitive_flexibility`
- benchmark form: multi-turn suite evaluation
- official task name: `cogflex_suite_binary`

This repository publishes the public CogFlex benchmark contract, the deterministic public split generator, the Kaggle notebook runtime, and validators for externally managed private bundles.

## Repository Layout

```text
kaggle/
  dataset/
    public/
      dataset-metadata.json
      public_leaderboard_rows.json
      public_quality_report.json
  notebook/
    cogflex_notebook_task.ipynb
    kernel-metadata.json
scripts/
  build_cogflex_dataset.py
  deploy_dataset.sh
  deploy_private_dataset.sh
  deploy_notebook.sh
  verify_cogflex.py
tests/
  test_cogflex_dataset_generation.py
  test_cogflex_notebook_runtime.py
  test_cogflex_verification.py
Makefile
```

## Suite Shape

Each scored episode contains:

1. `learn_turn`: 6 labeled examples for the current rule
2. `shift_turn`: 6 labeled examples after a task-specific shift
3. `decision_turn`: 8 probes scored only on the final turn

Each item mixes numeric and symbolic stimulus attributes:

- `r1`, `r2`
- `shape`
- `tone`

Published public and private rows share the same analysis schema:

- `analysis.faculty_id`
- `analysis.suite_task_id`
- `analysis.shift_mode`
- `analysis.difficulty_bin`

Public rows include `scoring.final_probe_targets`. Private rows are inference-only.

## Suite Tasks

- `explicit_rule_update`: turn 2 explicitly states that the rule changed
- `latent_rule_update`: turn 2 changes the rule without explicit switch language and exposes exactly 2 conflicting shift examples
- `context_binding`: turn 1 teaches one context, turn 2 teaches a second context, turn 3 mixes contexts and requires context-specific routing
- `trial_cued_switch`: turn 2 introduces a cue legend that selects either the original rule or an alternate rule

The public generator enforces:

- 120 public rows, 30 per suite task
- 15 transition families shared across the split
- 50/50 `hard` and `medium` difficulty bins, assigned after candidate selection instead of forced during generation
- attack-suite ceilings on previous-rule, majority-label, nearest-neighbor, cue/context-agnostic, and exhaustive public-DSL search
- 12 learn-turn phrasings, 12 shift-turn phrasings, 8 decision-turn phrasings, randomized attribute order, and multiple public cue/context lexicons

## Public and Private Responsibilities

The public repo intentionally does **not** contain private rule formulas or private regeneration code.

Public repo responsibilities:

- deterministic public split generation
- tracked public dataset assets
- Kaggle notebook runtime
- external private bundle validation

Maintainer-only private responsibilities:

- private rule registry and deterministic private generation
- calibration against a fixed 3-model panel
- private answer key production
- private release manifest and private quality report production

## Private Bundle Contract

`scripts/verify_cogflex.py --split private` validates an external private bundle directory exposed through `--private-bundle-dir` or `COGFLEX_PRIVATE_BUNDLE_DIR`.

Required files inside that directory:

- `private_leaderboard_rows.json`
- `private_answer_key.json`
- `private_release_manifest.json`
- `private_quality_report.json`

Validation covers:

- row and answer-key schema
- answer-key joins by `episode_id`
- file SHA256 digests declared in the manifest
- exact public/private semantic overlap
- private lexicon overlap against the public cue/context lexicons
- quality report shape, including a 3-model calibration summary

## Local Usage

Run the repo test suite:

```bash
make test
```

Rebuild the tracked public assets:

```bash
.venv/bin/python -m scripts.build_cogflex_dataset
```

Verify the tracked public split:

```bash
make verify-public
```

Verify an external private bundle:

```bash
COGFLEX_PRIVATE_BUNDLE_DIR=/abs/path/to/private-bundle make verify-private
```

Private scoring in the notebook requires:

```bash
COGFLEX_PRIVATE_ANSWER_KEY_PATH=/abs/path/to/private_answer_key.json
```

## Kaggle Assets

Public dataset:

```text
raptorengineer/cogflex-suite-runtime
```

Private dataset:

```text
raptorengineer/cogflex-suite-runtime-private
```

Notebook:

```text
raptorengineer/cogflex-suite-notebook
```

## Notes

- The notebook is the source of truth for the Kaggle runtime contract.
- The public quality report is tracked alongside the public split and must be reproducible from the public generator.
- `make verify-private` validates a private bundle but does not regenerate it.
- The public repo stays stdlib-only and avoids publishing private rule formulas.

## References

- [Kaggle Competition — Measuring Progress Toward AGI: Cognitive Abilities](https://www.kaggle.com/competitions/kaggle-measuring-agi)
- [Competition Rules](https://www.kaggle.com/competitions/kaggle-measuring-agi/rules)
- [Kaggle Benchmarks Repository](https://github.com/Kaggle/kaggle-benchmarks)
- [Kaggle Benchmarks Cookbook](https://github.com/Kaggle/kaggle-benchmarks/blob/ci/cookbook.md)
