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

bash scripts/evaluate.sh
