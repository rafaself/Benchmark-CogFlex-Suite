# Intra-Gemini Comparison: Flash vs Flash-Lite

## Scope

- This is **intra-family Gemini evidence** measuring stability within the active Gemini readiness path.
- This is **not** a cross-provider conclusion.
- This does **not** widen the benchmark claim.
- Binary remains the only leaderboard-primary path.
- Narrative remains required same-episode robustness evidence.

## Run Identification

| Field | gemini-2.5-flash | gemini-2.5-flash-lite |
| --- | --- | --- |
| Provider | gemini | gemini |
| Release | R18 | R18 |
| Requested model | gemini-2.5-flash | gemini-2.5-flash-lite |
| Served model | not recorded | gemini-2.5-flash-lite |
| Execution timestamp | 20260323_120000 | 20260323_125335 |
| Prompt modes | binary, narrative | binary, narrative |
| Provenance | Committed M1 Gemini evidence was resynced in M6 from the ori... | Full provenance |

- gemini-2.5-flash artifact: `reports/live/gemini-first-panel/binary-vs-narrative/history/artifact__20260323_120000.json`
- gemini-2.5-flash metadata: `reports/live/gemini-first-panel/binary-vs-narrative/history/metadata__20260323_120000.json`
- gemini-2.5-flash report: `reports/live/gemini-first-panel/binary-vs-narrative/history/report__20260323_120000.md`
- gemini-2.5-flash-lite artifact: `reports/live/gemini-first-panel/binary-vs-narrative/latest/artifact.json`
- gemini-2.5-flash-lite metadata: `reports/live/gemini-first-panel/binary-vs-narrative/latest/metadata.json`
- gemini-2.5-flash-lite report: `reports/live/gemini-first-panel/binary-vs-narrative/latest/report.md`

## Comparability Verification

| Version field | Value |
| --- | --- |
| schema_version | v1 |
| generator_version | R12 |
| template_family_version | v1 |
| parser_version | v1 |
| metric_version | v1 |
| difficulty_version | R12 |
| artifact_schema_version | v1.1 |

| Split | SHA-256 (shared) |
| --- | --- |
| dev | `986f750f73549b42...` |
| private_leaderboard | `5b0ae4650a509a98...` |
| public_leaderboard | `6b884cbfd706db58...` |

All benchmark versions and frozen split hashes match. Runs are directly comparable.

## Binary Headline (primary metric)

| Metric | gemini-2.5-flash | gemini-2.5-flash-lite | Delta (gemini-2.5-flash - gemini-2.5-flash-lite) |
| --- | ---: | ---: | ---: |
| Post-shift Probe Accuracy | 0.781250 | 0.687500 | +0.093750 |
| Parse-valid rate | 1.000000 | 0.958333 | +0.041667 |

## Narrative Robustness (same-episode companion)

| Metric | gemini-2.5-flash | gemini-2.5-flash-lite | Delta |
| --- | ---: | ---: | ---: |
| Post-shift Probe Accuracy | 0.458333 | 0.276042 | +0.182292 |
| Parse-valid rate | 0.937500 | 0.520833 | +0.416667 |

## Binary to Narrative Delta

| Metric | gemini-2.5-flash | gemini-2.5-flash-lite |
| --- | ---: | ---: |
| Binary accuracy | 0.781250 | 0.687500 |
| Narrative accuracy | 0.458333 | 0.276042 |
| Binary minus Narrative delta | 0.322917 | 0.411458 |
| Binary parse-valid | 1.000000 | 0.958333 |
| Narrative parse-valid | 0.937500 | 0.520833 |

## Split-Level Summary

| Split | Mode | gemini-2.5-flash acc | gemini-2.5-flash-lite acc | Gap | gemini-2.5-flash PV | gemini-2.5-flash-lite PV |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| dev | binary | 0.781250 | 0.671875 | +0.109375 | 1.000000 | 0.937500 |
| dev | narrative | 0.421875 | 0.312500 | +0.109375 | 0.937500 | 0.750000 |
| public_leaderboard | binary | 0.718750 | 0.625000 | +0.093750 | 1.000000 | 0.937500 |
| public_leaderboard | narrative | 0.484375 | 0.281250 | +0.203125 | 0.937500 | 0.500000 |
| private_leaderboard | binary | 0.843750 | 0.765625 | +0.078125 | 1.000000 | 1.000000 |
| private_leaderboard | narrative | 0.468750 | 0.234375 | +0.234375 | 0.937500 | 0.312500 |

## Template Slices

| Template | Mode | gemini-2.5-flash acc | gemini-2.5-flash-lite acc | Gap | gemini-2.5-flash PV | gemini-2.5-flash-lite PV |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| T1 | binary | 0.790000 | 0.690000 | +0.100000 | 1.000000 | 0.920000 |
| T1 | narrative | 0.490000 | 0.150000 | +0.340000 | 0.960000 | 0.360000 |
| T2 | binary | 0.771739 | 0.684783 | +0.086957 | 1.000000 | 1.000000 |
| T2 | narrative | 0.423913 | 0.413043 | +0.010870 | 0.913043 | 0.695652 |

## Difficulty Slices

| Difficulty | Mode | gemini-2.5-flash acc | gemini-2.5-flash-lite acc | Gap | gemini-2.5-flash PV | gemini-2.5-flash-lite PV |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| easy | binary | 0.790000 | 0.690000 | +0.100000 | 1.000000 | 0.920000 |
| easy | narrative | 0.490000 | 0.150000 | +0.340000 | 0.960000 | 0.360000 |
| medium | binary | 0.771739 | 0.684783 | +0.086957 | 1.000000 | 1.000000 |
| medium | narrative | 0.423913 | 0.413043 | +0.010870 | 0.913043 | 0.695652 |

## Transition-Direction Slices

| Transition | Mode | gemini-2.5-flash acc | gemini-2.5-flash-lite acc | Gap | gemini-2.5-flash PV | gemini-2.5-flash-lite PV |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| R_std_to_R_inv | binary | 0.812500 | 0.687500 | +0.125000 | 1.000000 | 0.958333 |
| R_std_to_R_inv | narrative | 0.427083 | 0.333333 | +0.093750 | 0.875000 | 0.625000 |
| R_inv_to_R_std | binary | 0.750000 | 0.687500 | +0.062500 | 1.000000 | 0.958333 |
| R_inv_to_R_std | narrative | 0.489583 | 0.218750 | +0.270833 | 1.000000 | 0.416667 |

## Failure Decomposition Comparison (diagnostic-only)

| Scope | Mode | Metric | gemini-2.5-flash | gemini-2.5-flash-lite | Delta |
| --- | --- | --- | ---: | ---: | ---: |
| overall | Binary | Runtime error rate | 0.000000 | 0.041667 | -0.041667 |
| overall | Binary | Parse/format failure rate | 0.000000 | 0.000000 | +0.000000 |
| overall | Binary | Parse-valid rate | 1.000000 | 0.958333 | +0.041667 |
| overall | Binary | Adaptation failure rate | 0.520833 | 0.729167 | -0.208333 |
| overall | Narrative | Runtime error rate | 0.041667 | 0.187500 | -0.145833 |
| overall | Narrative | Parse/format failure rate | 0.020833 | 0.291667 | -0.270833 |
| overall | Narrative | Parse-valid rate | 0.937500 | 0.520833 | +0.416667 |
| overall | Narrative | Adaptation failure rate | 0.895833 | 0.479167 | +0.416667 |

### By Split

| Split | Mode | Metric | gemini-2.5-flash | gemini-2.5-flash-lite | Delta |
| --- | --- | --- | ---: | ---: | ---: |
| dev | Binary | Runtime | 0.000000 | 0.062500 | -0.062500 |
| dev | Binary | Parse/format | 0.000000 | 0.000000 | +0.000000 |
| dev | Binary | Adaptation | 0.500000 | 0.687500 | -0.187500 |
| dev | Narrative | Runtime | 0.000000 | 0.062500 | -0.062500 |
| dev | Narrative | Parse/format | 0.062500 | 0.187500 | -0.125000 |
| dev | Narrative | Adaptation | 0.937500 | 0.750000 | +0.187500 |
| private_leaderboard | Binary | Runtime | 0.000000 | 0.000000 | +0.000000 |
| private_leaderboard | Binary | Parse/format | 0.000000 | 0.000000 | +0.000000 |
| private_leaderboard | Binary | Adaptation | 0.375000 | 0.625000 | -0.250000 |
| private_leaderboard | Narrative | Runtime | 0.062500 | 0.250000 | -0.187500 |
| private_leaderboard | Narrative | Parse/format | 0.000000 | 0.437500 | -0.437500 |
| private_leaderboard | Narrative | Adaptation | 0.875000 | 0.250000 | +0.625000 |
| public_leaderboard | Binary | Runtime | 0.000000 | 0.062500 | -0.062500 |
| public_leaderboard | Binary | Parse/format | 0.000000 | 0.000000 | +0.000000 |
| public_leaderboard | Binary | Adaptation | 0.687500 | 0.875000 | -0.187500 |
| public_leaderboard | Narrative | Runtime | 0.062500 | 0.250000 | -0.187500 |
| public_leaderboard | Narrative | Parse/format | 0.000000 | 0.250000 | -0.250000 |
| public_leaderboard | Narrative | Adaptation | 0.875000 | 0.437500 | +0.437500 |

## Rule Persistence Rate (diagnostic-only)

| Scope | Mode | Metric | gemini-2.5-flash | gemini-2.5-flash-lite | Delta |
| --- | --- | --- | ---: | ---: | ---: |
| dev | Binary | Old-rule persistence rate | 0.000000 | 0.125000 | -0.125000 |
| dev | Binary | Recency overshoot rate | 0.062500 | 0.062500 | +0.000000 |
| dev | Narrative | Old-rule persistence rate | 0.062500 | 0.125000 | -0.062500 |
| dev | Narrative | Recency overshoot rate | 0.125000 | 0.250000 | -0.125000 |
| overall | Binary | Old-rule persistence rate | 0.000000 | 0.104167 | -0.104167 |
| overall | Binary | Recency overshoot rate | 0.125000 | 0.041667 | +0.083333 |
| overall | Narrative | Old-rule persistence rate | 0.020833 | 0.104167 | -0.083333 |
| overall | Narrative | Recency overshoot rate | 0.291667 | 0.145833 | +0.145833 |
| private_leaderboard | Binary | Old-rule persistence rate | 0.000000 | 0.000000 | +0.000000 |
| private_leaderboard | Binary | Recency overshoot rate | 0.062500 | 0.000000 | +0.062500 |
| private_leaderboard | Narrative | Old-rule persistence rate | 0.000000 | 0.000000 | +0.000000 |
| private_leaderboard | Narrative | Recency overshoot rate | 0.375000 | 0.062500 | +0.312500 |
| public_leaderboard | Binary | Old-rule persistence rate | 0.000000 | 0.187500 | -0.187500 |
| public_leaderboard | Binary | Recency overshoot rate | 0.250000 | 0.062500 | +0.187500 |
| public_leaderboard | Narrative | Old-rule persistence rate | 0.000000 | 0.187500 | -0.187500 |
| public_leaderboard | Narrative | Recency overshoot rate | 0.375000 | 0.125000 | +0.250000 |

## Disagreement-Focused Diagnostics (diagnostic-only)

| Scope | Mode | Metric | gemini-2.5-flash | gemini-2.5-flash-lite |
| --- | --- | --- | --- | --- |
| overall | Binary | Adaptation failures | 25 | 35 |
| overall | Binary | Exact old-rule persistence | 0/25 (0.000000) | 5/35 (0.142857) |
| overall | Binary | Exact recency overshoot | 6/25 (0.240000) | 2/35 (0.057143) |
| overall | Binary | Old-rule error probes | 13/42 (0.309524) | 26/52 (0.500000) |
| overall | Binary | Recency error probes | 29/42 (0.690476) | 26/52 (0.500000) |
| overall | Narrative | Adaptation failures | 43 | 23 |
| overall | Narrative | Exact old-rule persistence | 1/43 (0.023256) | 5/23 (0.217391) |
| overall | Narrative | Exact recency overshoot | 14/43 (0.325581) | 7/23 (0.304348) |
| overall | Narrative | Old-rule error probes | 29/92 (0.315217) | 21/47 (0.446809) |
| overall | Narrative | Recency error probes | 63/92 (0.684783) | 26/47 (0.553191) |

## Flash-Lite Weakness Concentration

### By Failure Category (overall)

| Mode | Runtime error rate | Parse/format failure rate | Adaptation failure rate |
| --- | ---: | ---: | ---: |
| binary | 0.041667 | 0.000000 | 0.729167 |
| narrative | 0.187500 | 0.291667 | 0.479167 |

### By Split (Binary)

| Split | Accuracy | Parse-valid | Runtime errors | Adaptation failures |
| --- | ---: | ---: | ---: | ---: |
| dev | 0.250000 | 0.937500 | 1 | 11 |
| public_leaderboard | 0.062500 | 0.937500 | 1 | 14 |
| private_leaderboard | 0.375000 | 1.000000 | 0 | 10 |

### By Split (Narrative)

| Split | Accuracy | Parse-valid | Runtime errors | Parse failures | Adaptation failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 0.000000 | 0.750000 | 1 | 3 | 12 |
| public_leaderboard | 0.062500 | 0.500000 | 4 | 4 | 7 |
| private_leaderboard | 0.062500 | 0.312500 | 4 | 7 | 4 |

### By Template (Narrative)

| Template | Accuracy | Parse-valid | Runtime errors | Parse failures | Adaptation failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| T1 | 0.000000 | 0.360000 | 7 | 9 | 9 |
| T2 | 0.086957 | 0.695652 | 2 | 5 | 14 |

### By Transition (Narrative)

| Transition | Accuracy | Parse-valid | Runtime errors | Parse failures | Adaptation failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| R_std_to_R_inv | 0.041667 | 0.625000 | 5 | 4 | 14 |
| R_inv_to_R_std | 0.041667 | 0.416667 | 4 | 10 | 9 |

### Concentration Summary

- Narrative parse/format failure rate (0.2917) is the dominant non-adaptation weakness. Binary has 0.0000.
- Narrative runtime error rate (0.1875) substantially exceeds Binary (0.0417), indicating provider-level reliability issues with longer Narrative prompts.
- Narrative parse-valid rate is lowest on private_leaderboard (0.3125), with 7 parse failures and 4 runtime errors out of 16 episodes.
- Narrative weakness is most concentrated on template T1 (parse-valid 0.3600, accuracy 0.0000).
- Narrative weakness is most concentrated on transition R_inv_to_R_std (parse-valid 0.4167, accuracy 0.0417).
- Of Narrative failures, 50.0% are provider/runtime or parse/format failures, 50.0% are adaptation failures after valid parses.

## Provider/Runtime Contamination Note

- **gemini-2.5-flash**: Committed M1 Gemini evidence was resynced in M6 from the original legacy capture. The original requested model name was `gemini-2.5-flash`; provider-served model version, token usage, response IDs, and durations were not captured in that legacy artifact, so execution provenance in this resynced report is partial.
- **gemini-2.5-flash-lite**: No provider/runtime contamination noted.

## Episode-Level Cross-Model Agreement

### Binary mode

| Agreement category | Count | Rate |
| --- | ---: | ---: |
| Both correct (all 4 probes) | 7 | 0.145833 |
| gemini-2.5-flash correct, gemini-2.5-flash-lite wrong | 16 | 0.333333 |
| gemini-2.5-flash-lite correct, gemini-2.5-flash wrong | 4 | 0.083333 |
| Both wrong | 21 | 0.437500 |
| Total episodes | 48 | |

### Narrative mode

| Agreement category | Count | Rate |
| --- | ---: | ---: |
| Both correct (all 4 probes) | 0 | 0.000000 |
| gemini-2.5-flash correct, gemini-2.5-flash-lite wrong | 2 | 0.041667 |
| gemini-2.5-flash-lite correct, gemini-2.5-flash wrong | 2 | 0.041667 |
| Both wrong | 44 | 0.916667 |
| Total episodes | 48 | |

## Interpretation

- This comparison is **intra-Gemini only**. It measures stability within the active v1 readiness evidence path.
- Binary is the **only** headline interpretation metric.
- Narrative is required same-episode robustness evidence; it does not replace Binary.
- gemini-2.5-flash Binary (0.781250) outperforms gemini-2.5-flash-lite Binary (0.687500) by +0.093750.
- gemini-2.5-flash-lite shows higher runtime error rates and substantially lower Narrative parse-valid rates, indicating the Flash-Lite model's weakness is concentrated in Narrative formatting/parsing and provider reliability, not solely in adaptation logic.
- This comparison does not widen the benchmark claim beyond the Gemini evidence path.

