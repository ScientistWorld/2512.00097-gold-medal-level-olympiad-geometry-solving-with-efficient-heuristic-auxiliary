#!/usr/bin/env python3
"""Summarise the hardening-2 audit (audit only, never part of the gym).

Merges every redteam/hardening2/results/*_scores_{test,train}.json and the
reference/baseline score files, then computes the diagnostic rank used by
the red team for each method:

    rank = sum_e weight_e * sum_m |coef_m| * dir_m * (x_m - ref_m) / sigma_m

with sigma_m the population standard deviation of metric m over the honest
cohort (reference seeds, HAGeo variants, simple rules, fixed baselines).
A missing metric contributes 0.  Writes results/summary.json.
"""
from __future__ import annotations

import glob
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "redteam" / "hardening2" / "results"
REF = json.loads((ROOT / "scoring" / "reference.json").read_text())

HONEST = ["hageo", "hageo_seed1", "hageo_seed2", "hageo_hybrid", "hageo_ext", "hageo_ext_hybrid",
          "hageo_unfiltered", "hageo_n1", "systematic", "rule_mixed3", "rule_circumcenters",
          "random_aux", "ddar"]
WEIGHTINGS = {"final": None, "old_0.5_0.5": {"hageo409_aux": 0.5, "jgex231_aux": 0.5}}


def load(slice_: str) -> dict:
    merged: dict = {}
    files = sorted(glob.glob(str(RES / f"*_scores_{slice_}.json")))
    files.sort(key=lambda f: 0 if Path(f).name.startswith("reference_") else 1)
    for f in files:
        d = json.loads(Path(f).read_text())
        for e, v in d["experiments"].items():
            for name, m in v["results"].items():
                if m is None:
                    continue
                merged.setdefault(e, {}).setdefault(name, m)
    return merged


def ranks(scores: dict, weights: dict, cohort: list[str]) -> dict:
    out = {}
    names = sorted({n for e in scores.values() for n in e})
    sig = {}
    for e, spec in REF["experiments"].items():
        if e not in scores:
            continue
        for m in spec["metrics"]:
            vals = [scores[e][n][m] for n in cohort if n in scores[e] and m in scores[e][n]]
            sig[(e, m)] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    for n in names:
        total, parts = 0.0, {}
        for e, spec in REF["experiments"].items():
            if e not in scores or n not in scores[e] or "hageo" not in scores[e]:
                continue
            w = weights[e]
            for m, ms in spec["metrics"].items():
                s = sig.get((e, m), 0.0)
                if s == 0 or m not in scores[e][n]:
                    continue
                d = 1 if ms["higher_is_better"] else -1
                term = w * abs(ms["coefficient"]) * d * (scores[e][n][m] - scores[e]["hageo"][m]) / s
                parts[f"{e}.{m}"] = round(term, 4)
                total += term
        out[n] = {"rank": round(total, 4), "parts": parts,
                  "experiments_present": sorted(e for e in scores if n in scores[e])}
    return out


def main() -> None:
    summary = {}
    for slice_ in ("test", "train"):
        scores = load(slice_)
        summary[slice_] = {"metrics": scores, "ranks": {}}
        for wname, weights in WEIGHTINGS.items():
            weights = weights or {e: REF["experiments"][e]["weight"] for e in REF["experiments"]}
            summary[slice_]["ranks"][wname] = ranks(scores, weights, [n for n in HONEST])
        seeds = ["hageo", "hageo_seed1", "hageo_seed2"]
        r = summary[slice_]["ranks"]["final"]
        have = [r[s]["rank"] for s in seeds if s in r]
        if have:
            summary[slice_]["seed_rank_range"] = [min(have), max(have)]
    (RES / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    for slice_ in ("test", "train"):
        print(f"== {slice_}")
        r = summary[slice_]["ranks"]["final"]
        for n in sorted(r, key=lambda k: -r[k]["rank"]):
            m = {e: {k: round(v, 3) for k, v in summary[slice_]["metrics"][e][n].items()}
                 for e in summary[slice_]["metrics"] if n in summary[slice_]["metrics"][e]}
            print(f"{n:22s} {r[n]['rank']:+8.3f}  {m}")
        print("seed range", summary[slice_].get("seed_rank_range"))


if __name__ == "__main__":
    main()
