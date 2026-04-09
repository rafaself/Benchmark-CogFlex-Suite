# CogFlex Suite Benchmark

Kaggle-oriented benchmark project for a flexible executive-functions suite:

- faculty: `executive_functions/cognitive_flexibility`
- benchmark form: multi-turn suite evaluation
- official task name: `cogflex_suite_flexible`

This repository publishes the public CogFlex contract, the deterministic public split generator, the Kaggle notebook runtime, and validators for externally managed private bundles.

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
  cogflex_fixtures.py
  test_cogflex_dataset_generation.py
  test_cogflex_notebook_runtime.py
  test_cogflex_verification.py
Makefile
```

## Flexible Episode Contract

Each scored row exposes:

- `inference.turns`: ordered textual turns with variable length
- `inference.turn_specs`: one entry per turn with `{kind, item_count}`
- `inference.response_spec`: `{format, probe_count, label_vocab}`
- `analysis.faculty_id`
- `analysis.suite_task_id`
- `analysis.shift_mode`
- `analysis.difficulty_bin`
- `analysis.structure_family_id`

Public rows also include `scoring.final_probe_targets`. Private rows are inference-only and must be paired with an external answer key.

The current public split exercises two structural families:

- `two_step_focus`: 2 evidence turns followed by a decision turn
- `three_step_bridge`: 3 evidence turns followed by a decision turn

The public rows intentionally vary:

- number of turns: `3` or `4`
- decision probes: `5` or `6`
- label vocabulary size: `2` or `3`
- routing metadata: some tasks attach `context`, others attach `cue`

## Suite Tasks

- `explicit_rule_update`: a later evidence turn explicitly announces the replacement rule
- `latent_rule_update`: the sequence changes behavior without explicit switch language
- `context_binding`: labels depend on the context token attached to an item
- `trial_cued_switch`: labels depend on a cue that selects between competing rules

Each public suite task appears in at least two structural formats so the runtime and verifier validate the flexible contract end to end.

## Private Bundle Contract

`scripts/verify_cogflex.py --split private` validates an external private bundle directory exposed through `--private-bundle-dir` or `COGFLEX_PRIVATE_BUNDLE_DIR`.

Required files inside that directory:

- `private_leaderboard_rows.json`
- `private_answer_key.json`
- `private_release_manifest.json`
- `private_quality_report.json`

Validation covers:

- inference row schema with `turn_specs` and `response_spec`
- answer-key joins by `episode_id`
- file SHA256 digests declared in the manifest
- exact, structural, and near-duplicate isolation from the public split
- required private structure families:
  - `delayed_reversal`
  - `irrelevant_feature_interference`
  - `competitive_rule_switch`
  - `latent_rebinding`
  - `variable_evidence_budget`
- private quality report coverage:
  - `structure_family_counts`
  - `turn_count_distribution`
  - `probe_count_distribution`
  - `label_vocab_size_distribution`
  - `stimulus_space_summary`
  - `calibration_summary`
  - `semantic_isolation_summary`

The public repo does not ship private formulas or a private production generator.

## Local Usage

Run the repo test suite:

```bash
make test
```

Rebuild the tracked public assets:

```bash
python3 -m scripts.build_cogflex_dataset
```

Verify the tracked public split:

```bash
make verify-public
```

Verify an external private bundle:

```bash
COGFLEX_PRIVATE_BUNDLE_DIR=/abs/path/to/private-bundle make verify-private
```
