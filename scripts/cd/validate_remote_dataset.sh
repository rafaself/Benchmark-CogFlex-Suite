#!/usr/bin/env bash
set -euo pipefail
# Validate that the dataset was published to Kaggle.
# Requires env: DATASET_ID

rm -rf /tmp/kaggle-dataset-verify
mkdir -p /tmp/kaggle-dataset-verify

kaggle datasets metadata "${DATASET_ID}" -p /tmp/kaggle-dataset-verify
test -s /tmp/kaggle-dataset-verify/dataset-metadata.json \
  || { echo "ERROR: remote dataset metadata was not downloaded" >&2; exit 1; }
