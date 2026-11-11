#!/usr/bin/env python3
"""Job-1 smoke test: engine, gate, proposers on a few problems (audit only)."""
import json, sys, time, traceback, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "test"))
sys.path.insert(0, str(ROOT / "method" / "hageo"))
import engine, gate, build_split  # noqa
import propose  # noqa  (method/hageo)

def step(name, fn):
    t = time.time()
    try:
        out = fn()
        print(f"[smoke] {name}: OK {time.time()-t:.1f}s -> {out}", flush=True)
        return out
    except Exception:
        print(f"[smoke] {name}: FAIL {time.time()-t:.1f}s", flush=True)
        traceback.print_exc()
        return None

ORTHO = ("a b c = triangle a b c; d = on_tline d b a c, on_tline d c a b", "perp a d b c")
step("ddar alone orthocenter", lambda: engine.verify(ORTHO[0], ORTHO[1], [], 7, 15))
step("ddar + foot", lambda: engine.verify(ORTHO[0], ORTHO[1], ["e = foot e a b c"], 7, 15))
step("ddar + midpoint", lambda: engine.verify(ORTHO[0], ORTHO[1], ["e = midpoint e b c"], 7, 15))
step("unbuildable identical point", lambda: engine.verify(ORTHO[0], ORTHO[1], ["e = on_tline e b a c, on_tline e c a b"], 7, 15))
coords = step("draw", lambda: engine.draw_coordinates(ORTHO[0], ORTHO[1], 7))

def run_props(pid, setup, goal, seed, timeout, n_verify=3):
    row = {"problem_id": pid, "setup": setup, "points": gate.setup_point_names(setup),
           "coords": engine.draw_coordinates(setup, goal, seed), "difficulty": 1.0,
           "max_attempts": 16, "max_aux_per_attempt": 3}
    t = time.time()
    hag = propose.propose_problem(row, 16, 2, 0)
    t_h = time.time() - t
    sys.path.insert(0, str(ROOT / "baseline"))
    import random_aux
    t = time.time()
    ran = random_aux.propose_problem(row, 16, 2, 17)
    t_r = time.time() - t
    out = {"hageo_attempts": len(hag), "hageo_s": round(t_h, 2), "random_attempts": len(ran), "random_s": round(t_r, 2),
           "hageo_first": hag[:3], "random_first": ran[:2]}
    for name, props in (("hageo", hag), ("random", ran)):
        canon = gate.validate_rows([{"problem_id": pid, "attempts": props}], [{"problem_id": pid, "setup": setup}], 16, 3)[pid]
        res = []
        for att in canon[:n_verify]:
            res.append(engine.verify(setup, goal, att, seed, timeout))
        out[name + "_verify"] = [(s, round(x, 2)) for s, x in res]
    return out

step("proposers on orthocenter", lambda: run_props("ortho", ORTHO[0], ORTHO[1], 7, 15))

try:
    rows = build_split.load_hageo409()
    picks = [r for r in rows if r["source_id"] in ("2012CGMOp5", "2013ARMOg9p2", "2019G1")]
    for r in picks:
        setup, goal, _ = build_split.rename_statement(r["statement"], r["source_id"])
        seed = build_split.stable_int(build_split.SALT, "seed", r["source_id"])
        step(f"ddar alone {r['source_id']}", lambda: engine.verify(setup, goal, [], seed, 6))
        step(f"proposers {r['source_id']}", lambda: run_props(r["source_id"], setup, goal, seed, 10, 2))
except Exception:
    traceback.print_exc()
