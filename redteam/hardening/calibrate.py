#!/usr/bin/env python3
"""Job-1 calibration: run the real evaluator on a handful of screened problems."""
import json, math, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tmp" / "hardening"
OUT.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in (ROOT / "eval/test/screening.jsonl").read_text().splitlines() if l.strip()]
sat = sorted([r for r in rows if r.get("status") == "saturated" and r["seconds"] <= 4.0], key=lambda r: r["difficulty"])
print(f"[calib] screened={len(rows)} saturated<=4s={len(sat)}", flush=True)
k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
picks = [sat[int(i * (len(sat) - 1) / max(1, k - 1))] for i in range(k)] if len(sat) >= k else sat
probs = []
for i, r in enumerate(picks):
    t = int(min(20, max(6, math.ceil(5 * r["seconds"] + 4))))
    probs.append({"problem_id": f"calib_{i}", "source_id": r["source_id"], "setup": r["setup"], "goal": r["goal"],
                  "difficulty": r["difficulty"], "seed": r["seed"], "timeout": t})
(OUT / "calib_problems.jsonl").write_text("".join(json.dumps(p) + "\n" for p in probs))
t0 = time.time()
cmd = [sys.executable, str(ROOT / "eval/test/evaluate.py"), "--problems", str(OUT / "calib_problems.jsonl"),
       "--baselines", str(OUT / "calib_baselines.json"), "--recompute-baselines", "--only", "hageo",
       "--out", str(OUT / "calib_scores.json"), "--details", str(OUT / "calib_details.json"),
       "--cache", str(OUT / "calib_cache.jsonl"), "--workers", "1"]
subprocess.run(cmd, cwd=ROOT)
print(f"[calib] evaluator finished in {time.time()-t0:.0f}s", flush=True)
for f in ("calib_scores.json", "calib_baselines.json", "calib_details.json"):
    p = OUT / f
    if p.exists():
        print(f"== {f}\n" + p.read_text()[:4000], flush=True)
cache = OUT / "calib_cache.jsonl"
if cache.exists():
    vals = [json.loads(l)[1] for l in cache.read_text().splitlines() if l.strip()]
    from collections import Counter
    print("[calib] attempt statuses", Counter(v[0] for v in vals), flush=True)
    secs = sorted(v[1] for v in vals)
    if secs:
        print(f"[calib] attempt seconds: n={len(secs)} mean={sum(secs)/len(secs):.2f} median={secs[len(secs)//2]:.2f} max={secs[-1]:.2f}", flush=True)
