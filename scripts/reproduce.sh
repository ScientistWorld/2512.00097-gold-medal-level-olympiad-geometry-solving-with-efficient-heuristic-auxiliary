#!/bin/bash
# Score every registered proposer (the reference is proposers/hageo.sh) on the
# visible and held-out problems. Rebuilding the problem sets from the public
# benchmarks is optional and slow:
#   python eval/test/build_split.py screen --source hageo409 && python eval/test/build_split.py split --source hageo409
#   python eval/test/build_split.py screen --source jgex && python eval/test/build_split.py split --source jgex
#   python eval/test/build_split.py coords
set -e
cd "$(dirname "$0")/.."
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
bash scripts/evaluate_test.sh
