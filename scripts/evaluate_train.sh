#!/bin/bash
# Visible train evaluation. No arguments.
#
# Same protocol as the hidden test on the visible train problems in
# data/benchmarks/hageo409_train.jsonl; writes scoring/scores_train.json.
set -e
cd "$(dirname "$0")/.."
export MPLBACKEND=Agg MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"
python eval/train/evaluate.py --out scoring/scores_train.json ${EVAL_CACHE:+--cache "$EVAL_CACHE"}
