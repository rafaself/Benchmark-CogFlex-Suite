# Iron Find Electric

**Iron Find Electric** is a documentation-first benchmark project for the Executive Functions track of the Measuring Progress Toward AGI challenge. The benchmark uses short two-charge episodes to test whether a model can update an inferred binary interaction rule after contradictory evidence, without turning the task into a general physics benchmark.

## Current Status

This repository now contains:

- the benchmark specification and planning documents;
- the first implementation slice for v1: the rule engine in [`src/rules.py`](./src/rules.py);
- focused rule tests in [`tests/test_rules.py`](./tests/test_rules.py).

Not implemented yet:

- schema;
- generator;
- rendering;
- parser;
- metrics;
- baselines;
- packaging.

The next milestone remains the deterministic local prototype described in the implementation spec: valid episode generation, deterministic difficulty assignment, Binary and Narrative rendering, parsing, scoring, baseline checks, and frozen validation contracts.

## v1 Rule System

The v1 benchmark allows exactly two rules over charges from `{-3, -2, -1, +1, +2, +3}`:

- `R_std`: same-sign charges -> `repel`, opposite-sign charges -> `attract`
- `R_inv`: same-sign charges -> `attract`, opposite-sign charges -> `repel`

Labels depend only on sign pattern, not magnitude. Swapping `(q1, q2)` must not change the label.

## Repository Layout

```text
.
├── README.md
├── benchmark_design_section_cognitive_flexibility.md
├── iron_find_electric_implementation_spec.md
├── iron_find_electric_improved_plan.md
├── src/
│   └── rules.py
└── tests/
    └── test_rules.py
```

## Local Setup

Create and use the local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Run the current tests:

```bash
python3 -m unittest discover -s tests -p 'test_rules.py' -v
```

## Source of Truth

If repository documents disagree, treat [`iron_find_electric_implementation_spec.md`](./iron_find_electric_implementation_spec.md) as authoritative for v1 behavior.

Supporting documents:

- [`iron_find_electric_improved_plan.md`](./iron_find_electric_improved_plan.md): scope, roadmap, and validity strategy
- [`benchmark_design_section_cognitive_flexibility.md`](./benchmark_design_section_cognitive_flexibility.md): benchmark framing and explicit v1 limitations
