#!/bin/bash
# Fixed evaluator baseline: random auxiliary constructions at the same budget.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python baseline/random_aux.py "$1" "$2" --rounds 2 --seed 17
