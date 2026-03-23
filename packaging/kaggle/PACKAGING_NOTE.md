# R16 Packaging Note

- Added Kaggle staging artifacts: `iron_find_electric_v1_kaggle_staging.ipynb`, `BENCHMARK_CARD.md`, `README.md`, and `frozen_artifacts_manifest.json`.
- Reproducibility is preserved by freezing explicit paths to the `R14` split manifests, carrying forward the local `R13` validity report and `R15` re-audit report, and verifying file integrity with SHA-256 hashes.
- The package claims an implemented Iron Find Electric v1 benchmark with Binary as the only leaderboard-primary path and Narrative as the required same-episode robustness companion over the same frozen episodes and probe targets.
- Post-shift Probe Accuracy is the sole headline metric. Narrative does not change the headline score, and only the final four labels are scored.
- The package explicitly does not claim physics skill, broad executive-function coverage, broad AGI capability, human-level performance, cross-provider readiness, switch cost measurement, recovery length, immediate post-shift drop, online change-detection latency, or emitted `hard` slices.
- Current v1 readiness evidence is Gemini-only. The committed anchor evidence preserves the original requested model label `gemini-2.5-flash`, the canonical paired Flash-Lite run lives under `reports/live/gemini-first-panel/binary-vs-narrative/latest/`, and the direct Flash vs Flash-Lite comparison lives under `reports/live/gemini-first-panel/comparison/latest/`.
- Anthropic and OpenAI integrations exist locally in the repository, but they are outside the current v1 readiness gate and outside the Kaggle staging path.
- `hard` remains reserved and is not emitted.
