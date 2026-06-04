#!/bin/bash
# Evaluate visible train-slice solver outputs.
#
# Mirrors scripts/evaluate.sh's standalone contract: read method-agnostic
# artifacts from outputs/ and write a scoring JSON file.

set -e

cd /home/user

mkdir -p scoring

python eval/train/evaluate_outputs.py --out scoring/scores_train.json
