#!/bin/bash
# Job 1 of the hardening iteration: smoke-test the new evaluator/proposers,
# screen HAGeo-409 with DDAR alone, and calibrate per-attempt costs.
set -uo pipefail
cd /home/user
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
mkdir -p tmp/hardening
python - <<'PY'
import os, numpy, pyarrow, matplotlib, absl
print("[job] affinity cpus:", len(os.sched_getaffinity(0)), "numpy", numpy.__version__, "pyarrow", pyarrow.__version__)
PY
timeout 300 python redteam/hardening/smoke.py 2>&1 | tee tmp/hardening/smoke.log
timeout 1900 python eval/test/build_split.py screen --timeout 6 --max-points 13 --budget-seconds 1750
python - <<'PY'
import json, collections
rows = [json.loads(l) for l in open("eval/test/screening.jsonl") if l.strip()]
c = collections.Counter(r["status"].split(":")[0] for r in rows)
print("[job] screening statuses", dict(c))
sat = [r for r in rows if r["status"] == "saturated"]
print("[job] saturated by seconds", sorted(round(r["seconds"], 1) for r in sat))
print("[job] saturated by difficulty", sorted(r["difficulty"] for r in sat))
PY
timeout 780 python redteam/hardening/calibrate.py 5 2>&1 | tee tmp/hardening/calibrate.log
echo "[job] done"
