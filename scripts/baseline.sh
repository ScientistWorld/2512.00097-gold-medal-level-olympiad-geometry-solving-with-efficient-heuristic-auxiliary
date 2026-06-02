#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against. 
# Implement this only if applicable, i.e. the paper has baselines.
# You do not need to implement all baselines to begin — 
# just enough to validate that the evaluation pipeline works 
# and provide a reference point. You can decide to expand more baselines later.
# Each baseline must be actually run and scored through evaluate.sh
# so the numbers are verified, not self-reported.
# You can decide what this baseline script should do yourself.
#
# Usage:
#   bash scripts/baseline.sh <name>

set -e

cd /home/user
export MPLCONFIGDIR=/home/user/tmp/matplotlib
mkdir -p "$MPLCONFIGDIR"

BENCHMARK=${1:-data/benchmarks/auxiliary_core.jsonl}
NAME=${2:-auxiliary_core}
TIMEOUT=${TIMEOUT:-15}
EVALUATE=${EVALUATE:-1}

python baseline/run_ddar.py \
  --input "$BENCHMARK" \
  --output "outputs/baseline_${NAME}.jsonl" \
  --timeout "$TIMEOUT"

if [ "$EVALUATE" = "1" ]; then
  bash scripts/evaluate.sh
fi
