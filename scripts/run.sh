#!/bin/bash
# Example job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -e

cd /home/user
export MPLCONFIGDIR=/home/user/tmp/matplotlib
mkdir -p "$MPLCONFIGDIR"

echo "[run] preparing benchmarks"
python data/prepare_benchmarks.py

echo "[run] auxiliary_core baseline"
bash scripts/baseline.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core
echo "[run] auxiliary_core HAGeo-style method"
ATTEMPTS=64 ROUNDS=1 TIMEOUT=15 bash scripts/method.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core

if [ -f data/benchmarks/hageo409_small.jsonl ]; then
  echo "[run] hageo409_small baseline"
  TIMEOUT=5 bash scripts/baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  echo "[run] hageo409_small HAGeo-style method"
  ATTEMPTS=48 ROUNDS=1 TIMEOUT=4 bash scripts/method.sh data/benchmarks/hageo409_small.jsonl hageo409_small
fi

echo "[run] final evaluation"
bash scripts/evaluate.sh
