#!/usr/bin/env python3
"""Summarise the hardening audit: per-method hidden-test numbers, seed spread,
paired comparisons and a transparent diagnostic rank (audit only)."""
import json, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "redteam/hardening/results"
ref = json.loads((ROOT / "scoring/reference.json").read_text())["experiments"]
test = json.loads((R / "audit2_scores_test.json").read_text())["experiments"]
goal = json.loads((R / "audit_scores_test.json").read_text())["experiments"]
for e in test:  # the goal-lookup shortcut ran in the first audit pass only
    test[e]["results"]["sc_goal_lookup"] = goal[e]["results"]["sc_goal_lookup"]
    test[e]["_status"]["sc_goal_lookup"] = goal[e]["_status"]["sc_goal_lookup"]
train = json.loads((R / "audit2_scores_train.json").read_text())["experiments"]
honest = ["hageo", "hageo_seed1", "hageo_seed2", "hageo_n1", "hageo_n3", "hageo_ranked", "hageo_hybrid",
          "hageo_unfiltered", "systematic", "random_aux", "ddar"]

def rank(cohort, scores):
    out = {}
    for m in cohort:
        total = 0.0
        for e, spec in ref.items():
            w = spec["weight"]
            for metric, md in spec["metrics"].items():
                vals = [scores[e]["results"][c][metric] for c in cohort]
                sd = statistics.pstdev(vals)
                if sd == 0:
                    continue
                sign = 1 if md["higher_is_better"] else -1
                total += w * abs(md["coefficient"]) * sign * (scores[e]["results"][m][metric]
                                                               - scores[e]["results"]["hageo"][metric]) / sd
        out[m] = round(total, 3)
    return out

summary = {
    "test": {e: {m: {k: round(v, 4) for k, v in r.items()} for m, r in test[e]["results"].items()} for e in test},
    "test_status": {e: test[e]["_status"] for e in test},
    "train": {e: {m: {k: round(v, 4) for k, v in r.items()} for m, r in train[e]["results"].items()} for e in train},
    "seed_spread_test": {e: {k: round(max(test[e]["results"][s][k] for s in ("hageo", "hageo_seed1", "hageo_seed2"))
                                      - min(test[e]["results"][s][k] for s in ("hageo", "hageo_seed1", "hageo_seed2")), 4)
                             for k in test[e]["results"]["hageo"]} for e in test},
    "diagnostic_rank_honest_cohort": rank(honest, test),
    "diagnostic_rank_with_shortcuts": rank(list(test["hageo409_aux"]["results"]), test),
}
det = json.loads((R / "audit2_details_test.json").read_text())
summary["first_success_test"] = {e: {m: {p: k for p, k in det[e][m].get("first_success", {}).items() if k}
                                     for m in ("hageo", "hageo_hybrid", "systematic")} for e in det}
(R / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: summary[k] for k in ("seed_spread_test", "diagnostic_rank_honest_cohort",
                                          "diagnostic_rank_with_shortcuts")}, indent=1))
