#!/bin/bash
# Standard (visible) evaluation: scores every proposer in proposers/ on the
# train problems with the evaluator's DDAR and writes scoring/scores.json
# (identical protocol to scripts/evaluate_train.sh). Method-agnostic: uses
# only eval/train/ and the proposers' outputs.
set -e
cd "$(dirname "$0")/.."
export MPLBACKEND=Agg MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"
python eval/train/evaluate.py --out scoring/scores.json --details outputs/eval_details.json ${EVAL_CACHE:+--cache "$EVAL_CACHE"}
