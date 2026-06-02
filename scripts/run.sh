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

python data/prepare_benchmarks.py

bash scripts/baseline.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core
ATTEMPTS=64 ROUNDS=1 TIMEOUT=15 bash scripts/method.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core

if [ -f data/benchmarks/hageo409_small.jsonl ]; then
  bash scripts/baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  ATTEMPTS=128 ROUNDS=2 TIMEOUT=20 bash scripts/method.sh data/benchmarks/hageo409_small.jsonl hageo409_small
fi

bash scripts/evaluate.sh
