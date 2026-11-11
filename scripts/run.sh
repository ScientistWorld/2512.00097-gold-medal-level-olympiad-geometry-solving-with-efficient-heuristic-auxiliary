#!/bin/bash
set -euo pipefail
cd /home/user
export MPLCONFIGDIR=/home/user/redteam/matplotlib_cache
bash redteam/better_systematic/run.sh
bash redteam/shortcut_failed_impossible_costs/run.sh
bash redteam/better_fallback/run.sh
python redteam/summarize.py > redteam/results_table.tsv
