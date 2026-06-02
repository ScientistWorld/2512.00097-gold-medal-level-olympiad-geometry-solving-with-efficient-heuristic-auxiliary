#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user
export MPLCONFIGDIR=/home/user/tmp/matplotlib
mkdir -p "$MPLCONFIGDIR"

BENCHMARK=${1:-data/benchmarks/auxiliary_core.jsonl}
NAME=${2:-auxiliary_core}
ATTEMPTS=${ATTEMPTS:-48}
ROUNDS=${ROUNDS:-1}
TIMEOUT=${TIMEOUT:-15}
SEED=${SEED:-0}
EVALUATE=${EVALUATE:-1}

python method/hageo/run_hageo.py \
  --input "$BENCHMARK" \
  --output "outputs/hageo_${NAME}.jsonl" \
  --attempts "$ATTEMPTS" \
  --rounds "$ROUNDS" \
  --timeout "$TIMEOUT" \
  --seed "$SEED"

if [ "$EVALUATE" = "1" ]; then
  bash scripts/evaluate.sh
fi
