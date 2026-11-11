#!/bin/bash
set -euo pipefail
cd /home/user
REDTEAM_RERUN=1 python redteam/run_case.py shortcut_failed_impossible_costs
