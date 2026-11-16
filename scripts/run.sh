#!/bin/bash
# Hardening-2 job (temporary; restored to the reference reproduction at the end):
# build the derived held-out/train problems, recompute their fixed baselines,
# score the reference through the unchanged evaluation scripts, then run the
# audit variants, rules and shortcuts through the held-out evaluator.
# Resumable: steps leave markers in tmp/hardening2/.
set -euo pipefail
cd /home/user
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
python -c "import os; print('[job] affinity cpus:', len(os.sched_getaffinity(0)), 'cpu_count:', os.cpu_count())"
cat /sys/fs/cgroup/cpu.max 2>/dev/null || true
python redteam/hardening2/audit.py
