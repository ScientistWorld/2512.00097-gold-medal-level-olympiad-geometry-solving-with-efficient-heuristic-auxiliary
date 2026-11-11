#!/bin/bash
set -euo pipefail
cd /home/user
export MPLCONFIGDIR=/home/user/redteam/matplotlib_cache
python redteam/run_case.py --suite
python redteam/summarize.py > redteam/results_table.tsv
