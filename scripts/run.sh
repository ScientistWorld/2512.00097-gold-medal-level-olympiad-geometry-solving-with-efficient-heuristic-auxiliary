#!/bin/bash
# Reproduce the gym's reference numbers end to end (CPU only, no internet):
# fixed baselines for every experiment, then the reference proposer
# (proposers/hageo.sh) through the train and held-out evaluations.
set -euo pipefail
cd /home/user
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
bash scripts/baseline.sh
bash scripts/reproduce.sh
