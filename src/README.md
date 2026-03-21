# `src` Overview

## Files

- `protocol.py`: Defines the shared benchmark vocabulary, enums, frozen constants, template catalog, and parser helpers used across the codebase.
- `rules.py`: Implements the charge interaction rule engine, including sign handling and label resolution for `R_std` and `R_inv`.
- `schema.py`: Defines the canonical episode data structures and validation rules for items, probe metadata, and full episode rows.
- `generator.py`: Builds deterministic episodes from a seed, assigns template/rule metadata, derives probe targets and probe metadata, and enforces generator constraints.
