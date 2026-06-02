#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# scripts/baseline.sh and scripts/method.sh to run baselines and
# the paper's method, each of which calls scripts/evaluate.sh.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user
#
# This is the "gold standard" reproduction — 
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

cd /home/user

python data/prepare_benchmarks.py --hageo-limit "${HAGEO_LIMIT:-4}"

bash scripts/baseline.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core
bash scripts/method.sh data/benchmarks/auxiliary_core.jsonl auxiliary_core

if [ -e data/benchmarks/hageo409_small.jsonl ]; then
  bash scripts/baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  ATTEMPTS=${RANDOM_ATTEMPTS:-24} ROUNDS=${ROUNDS:-1} TIMEOUT=${TIMEOUT:-3} SEED=${RANDOM_SEED:-17} \
    bash scripts/random_baseline.sh data/benchmarks/hageo409_small.jsonl hageo409_small
  ATTEMPTS=${ATTEMPTS:-24} ROUNDS=${ROUNDS:-1} TIMEOUT=${TIMEOUT:-3} SEED=${SEED:-0} \
    bash scripts/method.sh data/benchmarks/hageo409_small.jsonl hageo409_small
fi
