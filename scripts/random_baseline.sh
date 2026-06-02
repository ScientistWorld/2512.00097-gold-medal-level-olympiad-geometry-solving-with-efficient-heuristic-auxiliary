#!/bin/bash
# Run the paper's random auxiliary-construction baseline at a declared budget.

set -e

cd /home/user
export MPLCONFIGDIR=/home/user/tmp/matplotlib
mkdir -p "$MPLCONFIGDIR"

BENCHMARK=${1:-data/benchmarks/hageo409_small.jsonl}
NAME=${2:-hageo409_small}
ATTEMPTS=${ATTEMPTS:-48}
ROUNDS=${ROUNDS:-1}
TIMEOUT=${TIMEOUT:-15}
SEED=${SEED:-17}
EVALUATE=${EVALUATE:-1}

python baseline/run_random_aux.py \
  --input "$BENCHMARK" \
  --output "outputs/random_aux_${NAME}.jsonl" \
  --attempts "$ATTEMPTS" \
  --rounds "$ROUNDS" \
  --timeout "$TIMEOUT" \
  --seed "$SEED"

if [ "$EVALUATE" = "1" ]; then
  bash scripts/evaluate.sh
fi
