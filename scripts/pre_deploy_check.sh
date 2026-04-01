#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi
RUNTIME_BUILD_DIR="${RUNTIME_BUILD_DIR:-/tmp/ruleshift-runtime-package-predeploy}"
KERNEL_BUILD_DIR="${KERNEL_BUILD_DIR:-/tmp/ruleshift-kernel-bundle-predeploy}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"

echo "=== RuleShift pre-deploy gate ==="

echo "[gate] phase-1 environment sanity..."
"$PYTHON_BIN" --version
"$PYTHON_BIN" -c "from pathlib import Path; import core.kaggle.runner; print(f'cwd={Path.cwd()}'); print(f'core.kaggle.runner={core.kaggle.runner.__file__}')"
echo "[gate] phase-1 environment sanity: ok"

echo "[gate] phase-2 staging manifest validation..."
"$PYTHON_BIN" -c "from core.kaggle.manifest import validate_kaggle_staging_manifest; validate_kaggle_staging_manifest()"
echo "[gate] phase-2 staging manifest validation: ok"

echo "[gate] phase-3 preflight..."
"$PYTHON_BIN" scripts/preflight_kaggle.py
echo "[gate] phase-3 preflight: ok"

echo "[gate] phase-4 runtime contract tests..."
"$PYTHON_BIN" -m pytest \
  tests/test_kaggle_execution.py \
  tests/test_kaggle_payload.py \
  tests/test_preflight_kaggle.py \
  tests/test_run_manifest.py \
  tests/test_private_split.py \
  tests/test_private_builder.py -v
echo "[gate] phase-4 runtime contract tests: ok"

echo "[gate] phase-5 notebook and packaging tests..."
"$PYTHON_BIN" -m pytest \
  tests/test_cd_build.py \
  tests/test_kbench_notebook.py \
  tests/test_packaging.py -v
echo "[gate] phase-5 notebook and packaging tests: ok"

echo "[gate] phase-6 runtime dataset artifact consistency..."
rm -rf "$RUNTIME_BUILD_DIR"
"$PYTHON_BIN" scripts/build_runtime_dataset_package.py --output-dir "$RUNTIME_BUILD_DIR"
test -f "$RUNTIME_BUILD_DIR/dataset-metadata.json"
test -f "$RUNTIME_BUILD_DIR/packaging/kaggle/frozen_artifacts_manifest.json"
test -f "$RUNTIME_BUILD_DIR/src/frozen_splits/public_leaderboard.json"
test ! -e "$RUNTIME_BUILD_DIR/src/frozen_splits/private_leaderboard.json"
echo "[gate] phase-6 runtime dataset artifact consistency: ok"

echo "[gate] phase-7 kernel bundle consistency..."
rm -rf "$KERNEL_BUILD_DIR"
"$PYTHON_BIN" scripts/build_kernel_package.py --output-dir "$KERNEL_BUILD_DIR"
test -f "$KERNEL_BUILD_DIR/kernel-metadata.json"
test -f "$KERNEL_BUILD_DIR/ruleshift_notebook_task.ipynb"
grep -q "%choose ruleshift_benchmark_v1_binary" "$KERNEL_BUILD_DIR/ruleshift_notebook_task.ipynb"
echo "[gate] phase-7 kernel bundle consistency: ok"

echo "=== Pre-deploy gate passed ==="
