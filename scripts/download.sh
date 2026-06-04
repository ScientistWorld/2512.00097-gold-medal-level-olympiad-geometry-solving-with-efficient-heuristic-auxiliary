#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: <1 MB
# Estimated disk usage after extraction: <1 MB
#
# This script writes to workspace-local paths so a future user with just this
# repository can fetch the required public benchmark files.

set -e

cd "$(dirname "$0")/.."

mkdir -p data/downloads/HAGeo-409

if [ ! -e data/downloads/HAGeo-409/HAGeo-409.parquet ]; then
  curl -L --fail \
    https://huggingface.co/datasets/HAGeo-IMO/HAGeo-409/resolve/main/HAGeo-409.parquet \
    -o data/downloads/HAGeo-409/HAGeo-409.parquet
fi

if [ ! -e data/downloads/HAGeo-409/README.md ]; then
  curl -L --fail \
    https://huggingface.co/datasets/HAGeo-IMO/HAGeo-409/raw/main/README.md \
    -o data/downloads/HAGeo-409/README.md
fi

if python -c "import pyarrow" >/dev/null 2>&1; then
  python data/prepare_benchmarks.py
elif [ -s data/benchmarks/auxiliary_core.jsonl ] && [ -s data/benchmarks/hageo409_small.jsonl ]; then
  echo "pyarrow is unavailable; using tracked benchmark JSONL files."
else
  echo "pyarrow is required to generate data/benchmarks/*.jsonl from the HAGeo parquet." >&2
  echo "Run environment/setup.sh first, or install pyarrow in this Python environment." >&2
  exit 1
fi
