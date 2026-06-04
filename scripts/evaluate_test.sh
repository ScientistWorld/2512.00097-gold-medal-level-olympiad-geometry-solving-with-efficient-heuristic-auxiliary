#!/bin/bash
# Evaluate held-out test-slice solver outputs.
#
# Mirrors scripts/evaluate.sh's standalone contract: read method-agnostic
# artifacts from outputs/ and write a scoring JSON file. The test evaluator
# scores every method entry present in scoring/scores_train.json when that
# file exists, so improve-mode variants are carried through automatically.

set -e

cd /home/user

mkdir -p scoring

python eval/test/evaluate_outputs.py \
  --train-scores scoring/scores_train.json \
  --out scoring/scores_test.json
