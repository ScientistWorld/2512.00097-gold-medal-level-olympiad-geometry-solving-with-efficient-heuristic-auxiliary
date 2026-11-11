#!/bin/bash
# Run the paper's method (HAGeo heuristic proposer) on an input file of
# goal-free problems and write its auxiliary-construction attempts.
# Usage: bash scripts/method.sh <input.jsonl> <output.jsonl>
# The input format is the one the evaluator writes (see proposers/README.md);
# scoring happens only through scripts/evaluate*.sh.
set -e
cd "$(dirname "$0")/.."
exec bash proposers/hageo.sh "$1" "$2"
