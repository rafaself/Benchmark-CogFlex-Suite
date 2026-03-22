## Design implications from Braem & Egner (2018)

### Benchmark framing
This benchmark should be framed narrowly as an Executive Functions benchmark for cognitive flexibility. Electrostatics is only the controlled substrate, and the v1 goal is final post-shift rule application after sparse contradictory evidence, not abstract reasoning in general.

### Construct definition
The target construct should be defined narrowly as:

**Cognitive flexibility under hidden rule shift**

More specifically, the benchmark should measure whether a model can:

- maintain a currently active rule,
- detect evidence that the rule is no longer valid,
- disengage from the previous rule,
- and adapt to the new rule with minimal perseveration.

This wording is preferable to broader claims such as "general flexibility" or "pure reasoning", because the literature suggests that flexibility is strongly shaped by contextual learning and control-state adaptation.

### Design requirements
1. **Use controlled latent shifts.** Rule changes should be generated and tracked by the evaluator, but never explicitly announced to the model.
2. **Avoid structural shortcut cues.** Template design must not let the model recover the shift boundary solely by counting from the end of the episode.
3. **Eliminate superficial contextual cues.** Layout, ordering, surface form, token patterns, and presentation details must not reveal when a shift has occurred.
4. **Keep reasoning demands bounded.** The task should require some inference, but the dominant challenge must remain adaptation after a regime change, not solving a deeply complex rule.
5. **Test robustness across surface forms.** At least one semantically equivalent alternate rendering should be included so success is not tied to one prompt template.

### What v1 can support
The current v1 protocol supports a narrow claim:

- performance on final post-shift probes after sparse contradictory evidence;
- comparison against shortcut baselines such as physics-prior, never-update, the recency shortcut baseline `last_evidence`, and majority-label behavior;
- robustness checks across a canonical Binary rendering and a Narrative rendering built from the same frozen episodes and probe targets.

### What v1 cannot support directly
The current v1 protocol does **not** directly measure:

- switch cost at the item level,
- immediate post-shift drop,
- recovery length,
- adaptation efficiency as a time series.

Those claims require a later protocol variant that captures intermediate predictions or stepwise responses rather than only the final probe outputs.

### Core evaluation policy
Binary-only Post-shift Probe Accuracy over the final post-shift probes is the sole headline metric for v1. The benchmark should still retain disagreement metadata internally for audit, shortcut analysis, and diagnostic-only sliced reporting.

### Validity risks to document
The benchmark specification should explicitly acknowledge the following threats to construct validity:

- exploitation of structural or positional cues,
- reliance on contextual or formatting cues,
- memorization of surface associations rather than policy adaptation,
- strong final probe accuracy without genuine rule revision,
- benchmark behavior dominated by reasoning complexity instead of switching behavior.

### Recommended interpretation policy
A high v1 score should not be interpreted as evidence of broad cognitive flexibility. It should be interpreted only as evidence that the model successfully applied an updated latent rule to final post-shift probes in a controlled binary environment, and that this performance was not well explained by the documented shortcut baselines.

### Bottom line
The benchmark should be designed and described as a narrow test of final post-shift rule application after sparse contradictory evidence, with v1 evaluation centered on Binary-only Post-shift Probe Accuracy and Narrative used only as same-episode robustness evidence. Richer switch-cost and recovery claims belong to a later stepwise protocol, not the current MVP.
