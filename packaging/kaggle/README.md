# Kaggle Staging Usage

This directory stages the implemented benchmark for Kaggle packaging. It does not create the benchmark from scratch and does not redefine benchmark semantics locally.

## Included Artifacts

- `iron_find_electric_v1_kaggle_staging.ipynb`: staging notebook entry point
- `BENCHMARK_CARD.md`: benchmark description and current evidence summary
- `PACKAGING_NOTE.md`: short release note for this staging bundle
- `frozen_artifacts_manifest.json`: explicit frozen paths, versions, and integrity hashes

## Intended Kaggle Flow

1. Upload the repository contents needed by the notebook, keeping `src/`, `tests/fixtures/`, `reports/`, and `packaging/kaggle/` together.
2. Open `iron_find_electric_v1_kaggle_staging.ipynb`.
3. Run the notebook cells that validate the frozen artifact manifest, inspect the packaged benchmark resources, and load the frozen split manifests.
4. Run the notebook staging dry run over the packaged frozen episodes in both Binary and Narrative modes.
5. Keep Binary as the only leaderboard-primary path and treat Narrative as the required same-episode robustness companion on the same episode order and probe targets.
6. Confirm that parsing, scoring, and report rendering complete end to end, with Post-shift Probe Accuracy as the headline metric.

## Reproducibility Notes

- Resource paths are explicit and relative to the repo root.
- The notebook relies on the local `src/` modules and the frozen JSON artifacts already present in the repository.
- The manifest records integrity hashes for the notebook, docs, frozen split manifests, and bundled evidence reports.
- The local validation and audit outputs remain the source of truth; Kaggle staging is a clean replay layer over those artifacts.
- Current live readiness evidence remains Gemini-only and is preserved under `reports/`. Kaggle staging does not rerun or reinterpret that live evidence.

## Environment Assumptions

- The notebook only requires Python and the files bundled in this repository.
- No production dependency installation is needed for the staging notebook itself, and Kaggle staging stays independent of optional local-only provider SDKs.
- The staging notebook dry run validates packaged assets, parsing, scoring, and reporting without live external inference.
- Anthropic and OpenAI integrations exist locally in the repo, but they are outside the current v1 readiness gate and outside the Kaggle staging path.
