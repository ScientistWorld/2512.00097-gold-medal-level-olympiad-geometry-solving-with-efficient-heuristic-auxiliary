#!/bin/bash
# Hidden test. No arguments.
#
# Runs every proposer registered as proposers/<name>.sh on the held-out
# problems kept in eval/test/, checks each returned auxiliary construction
# against the validity gate, verifies every attempt with the evaluator's own
# DDAR engine, and writes each method's numbers to scoring/scores_test.json.
# The fixed baselines (DDAR alone, random auxiliary constructions) are added
# from eval/test/baselines.json.
set -e
cd "$(dirname "$0")/.."
export MPLBACKEND=Agg MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"
python eval/test/evaluate.py --out scoring/scores_test.json ${EVAL_CACHE:+--cache "$EVAL_CACHE"}
