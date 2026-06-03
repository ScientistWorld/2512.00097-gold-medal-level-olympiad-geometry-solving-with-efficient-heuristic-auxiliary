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
mkdir -p outputs scoring

rm -f \
  outputs/baseline_auxiliary_core.jsonl \
  outputs/hageo_auxiliary_core.jsonl \
  outputs/baseline_hageo409_small.jsonl \
  outputs/random_aux_hageo409_small.jsonl \
  outputs/hageo_hageo409_small.jsonl \
  scoring/scores.json

echo "[run] preparing benchmarks"
HAGEO_LIMIT=${HAGEO_LIMIT:-12}
HAGEO_SORT=${HAGEO_SORT:-difficulty}
HAGEO_ATTEMPTS=${HAGEO_ATTEMPTS:-64}
HAGEO_RANDOM_ATTEMPTS=${HAGEO_RANDOM_ATTEMPTS:-64}
HAGEO_ROUNDS=${HAGEO_ROUNDS:-2}
HAGEO_TIMEOUT=${HAGEO_TIMEOUT:-5}
python data/prepare_benchmarks.py --hageo-limit "$HAGEO_LIMIT" --hageo-sort "$HAGEO_SORT"
echo "[run] hageo409_small config: limit=$HAGEO_LIMIT sort=$HAGEO_SORT attempts=$HAGEO_ATTEMPTS random_attempts=$HAGEO_RANDOM_ATTEMPTS rounds=$HAGEO_ROUNDS timeout=$HAGEO_TIMEOUT"

echo "[run] auxiliary_core baseline"
EVALUATE=0 bash scripts/baseline.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core
echo "[run] auxiliary_core HAGeo-style method"
ATTEMPTS=64 ROUNDS=1 TIMEOUT=15 EVALUATE=0 \
  bash scripts/method.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core

if [ -f data/benchmarks/hageo409_small.jsonl ]; then
  echo "[run] hageo409_small baseline"
  TIMEOUT="$HAGEO_TIMEOUT" EVALUATE=0 bash scripts/baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  echo "[run] hageo409_small random auxiliary baseline"
  ATTEMPTS="$HAGEO_RANDOM_ATTEMPTS" ROUNDS="$HAGEO_ROUNDS" TIMEOUT="$HAGEO_TIMEOUT" SEED=17 EVALUATE=0 \
    bash scripts/random_baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  echo "[run] hageo409_small HAGeo-style method"
  ATTEMPTS="$HAGEO_ATTEMPTS" ROUNDS="$HAGEO_ROUNDS" TIMEOUT="$HAGEO_TIMEOUT" SEED=0 EVALUATE=0 \
    bash scripts/method.sh data/benchmarks/hageo409_small.jsonl hageo409_small
fi

echo "[run] final evaluation"
bash scripts/evaluate.sh
