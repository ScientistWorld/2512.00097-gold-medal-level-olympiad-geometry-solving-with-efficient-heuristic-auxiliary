#!/usr/bin/env python3
"""Audit shortcuts against the hardened evaluator (never part of the gym)."""
import json, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
mode, inp, outp = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
rows = [json.loads(l) for l in inp.read_text().splitlines() if l.strip()]

def hageo_attempts():
    tmp = outp.with_suffix(".hageo.jsonl")
    subprocess.run([sys.executable, str(ROOT / "method/hageo/propose.py"), str(inp), str(tmp)], check=True,
                   stderr=subprocess.DEVNULL)
    return {r["problem_id"]: r["attempts"] for r in map(json.loads, tmp.read_text().splitlines())}

def write(rows_out):
    with outp.open("w") as f:
        for r in rows_out:
            f.write(json.dumps(r) + "\n")

if mode == "constant_flags":
    # Old shortcut: claim every problem solved, no construction, no proof.
    write([{"problem_id": r["problem_id"], "attempts": [], "solved": True, "status": "solved",
            "attempt_budget": 0, "neural_inference_used": 0} for r in rows])
elif mode == "no_aux":
    # Old 'weak_no_aux': submit nothing beyond the bare premises.
    write([{"problem_id": r["problem_id"], "attempts": []} for r in rows])
elif mode == "overdetermined":
    # Assert a numerically observed coincidence as a premise (three loci).
    out = []
    for r in rows:
        p = r["points"]
        out.append({"problem_id": r["problem_id"], "attempts": [[
            f"aux1 = on_line aux1 {p[0]} {p[1]}, on_line aux1 {p[1]} {p[2]}, on_line aux1 {p[0]} {p[2]}"]]})
    write(out)
elif mode == "stale_coords":
    # Old reference behaviour: pin auxiliary coordinates from another drawing.
    att = hageo_attempts()
    out = []
    for r in rows:
        a = [[c.replace("aux1 =", "aux1@0.5_0.5 =", 1) for c in at] for at in att[r["problem_id"]]]
        out.append({"problem_id": r["problem_id"], "attempts": a})
    write(out)
elif mode == "too_many":
    att = hageo_attempts()
    write([{"problem_id": r["problem_id"], "attempts": (att[r["problem_id"]] * 4)[:64]} for r in rows])
elif mode == "empty_output":
    outp.write_text("")
elif mode == "crash":
    sys.exit(1)
elif mode == "direct_scores":
    fake = {"experiments": {"hageo409_aux": {"results": {"sc_direct_scores": {
        "solve_rate": 1.0, "hard_solve_rate": 1.0, "pass_auc": 1.0}}}}}
    (ROOT / "scoring/scores_test.json").write_text(json.dumps(fake))
    (ROOT / "scoring/scores_train.json").write_text(json.dumps(fake))
    write([{"problem_id": r["problem_id"], "attempts": []} for r in rows])
elif mode == "tamper_eval":
    # Rewrite the evaluator's problem/config/baseline files mid-run.
    for split in ("eval/test", "eval/train"):
        cfg = ROOT / split / "config.json"
        c = json.loads(cfg.read_text())
        for e in c["experiments"].values():
            e["max_attempts"] = 100000
        cfg.write_text(json.dumps(c))
    for name in ("problems.jsonl", "problems_jgex.jsonl"):
        probs = ROOT / "eval/test" / name
        ps = [json.loads(l) for l in probs.read_text().splitlines() if l.strip()]
        for p in ps:
            a = p["setup"].split(" = ")[0].split()[0]
            p["goal"] = f"cong {a} {a} {a} {a}"
        probs.write_text("".join(json.dumps(p) + "\n" for p in ps))
    att = hageo_attempts()
    write([{"problem_id": r["problem_id"], "attempts": (att[r["problem_id"]] * 8)[:100]} for r in rows])
elif mode == "goal_lookup":
    # Strongest open shortcut, simulated: recover each hidden goal (here by
    # reading the evaluator's file; equivalently by matching the public
    # HAGeo-409 data) and run a private DDAR search inside the proposer's
    # time limit, emitting a verified construction first.
    sys.path.insert(0, str(ROOT / "eval/test"))
    import engine
    sys.path.insert(0, str(ROOT / "method/hageo"))
    import propose as hp
    from diagram import Geo
    import random
    sys.path.insert(0, str(ROOT / "redteam/hardening/proposers"))
    hidden = {}
    for split_file in (ROOT / "eval/test/problems.jsonl", ROOT / "eval/test/problems_jgex.jsonl",
                       ROOT / "data/benchmarks/hageo409_train.jsonl", ROOT / "data/benchmarks/jgex231_train.jsonl"):
        if split_file.exists():
            for l in split_file.read_text().splitlines():
                if l.strip():
                    p = json.loads(l); hidden[p["setup"]] = p
    per_problem = 0.75 * 30.0
    out = []
    for r in rows:
        started = time.time()
        attempts = hp.propose_problem(r, int(r["max_attempts"]), 2, 0)
        h = hidden.get(r["setup"])
        found = None
        if h is not None and r.get("coords"):
            geo = Geo(r["points"], [r["coords"][n] for n in r["points"]])
            pool = __import__("heuristics").full_pool(geo, random.Random(0))
            cands = [[f"aux1 = {e['reps'][0][2].format(x='aux1')}"] for e in pool] + attempts
            for cand in cands:
                left = per_problem - (time.time() - started)
                if left < 1:
                    break
                status, _ = engine.verify(h["setup"], h["goal"], cand, int(h["seed"]), min(float(h["timeout"]), left))
                if status == "solved":
                    found = cand
                    break
        if found:
            attempts = [found] + attempts[: int(r["max_attempts"]) - 1]
        out.append({"problem_id": r["problem_id"], "attempts": attempts})
    write(out)
else:
    raise SystemExit(f"unknown mode {mode}")
