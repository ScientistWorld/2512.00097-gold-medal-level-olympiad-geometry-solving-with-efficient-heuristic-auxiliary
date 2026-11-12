#!/bin/bash
# Recompute the evaluator-owned fixed baselines (DDAR alone; random auxiliary
# constructions at the same attempt budget) for every experiment, train and
# held-out. Results go to eval/{train,test}/baselines*.json.
set -e
cd "$(dirname "$0")/.."
export MPLBACKEND=Agg MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"
mkdir -p outputs
python eval/train/evaluate.py --recompute-baselines --no-proposers --out outputs/baselines_train.json --details outputs/baselines_train_details.json
python eval/test/evaluate.py --recompute-baselines --no-proposers --out outputs/baselines_test.json --details outputs/baselines_test_details.json
