#!/bin/bash
# Reproduce the gym's reference numbers end to end (CPU only, no internet).
# 1. (optional, slow) rebuild the problem sets:  python eval/test/build_split.py screen && python eval/test/build_split.py split
# 2. (optional, slow) recompute fixed baselines:  bash scripts/baseline.sh
# 3. score every registered proposer (the reference is proposers/hageo.sh):
set -e
cd "$(dirname "$0")/.."
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
bash scripts/evaluate_test.sh
