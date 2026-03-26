# Release 4 Notes: Private Split Operational Documentation

## What Was Added

- `packaging/kaggle/PRIVATE_SPLIT_RUNBOOK.md`: operational runbook covering offline generation of the private artifact, packaging and publication to the authorized private Kaggle dataset, public isolation verification, and a pre-evaluation checklist.
- `packaging/kaggle/BENCHMARK_CARD.md`: added "Private Evaluation" section describing held-out evaluation, the fixed-per-version private split, and the exclusion of private artifacts from the public package.
- `packaging/kaggle/README.md`: added `PRIVATE_SPLIT_RUNBOOK.md` to the layout listing.

## What Was Not Changed

Benchmark logic, frozen splits, tests, and all existing validation and evidence artifacts are unchanged. No private artifact or private seed content was added to the public repo.
