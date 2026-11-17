#!/usr/bin/env python3
"""Hardening-2 job driver (audit only, never part of the gym).

Resumable: every step leaves a marker in tmp/hardening2/ and is skipped when
the marker exists.  Verification results are memoised in the evaluator's
audit cache (tmp/hardening/cache_{train,test}.jsonl, shared with the previous
hardening audit), so identical attempts are never re-proved.

Steps
  1. JGEX-231 problems as eight independent instances each (eval/test/build_split.py instances)
  2. fixed baselines (DDAR alone, random auxiliaries) on the expanded JGEX sets
  3. reference only: scripts/evaluate_test.sh and scripts/evaluate_train.sh
     -> scoring/scores_{test,train}.json
  4. variants, rules and shortcuts through the held-out evaluator
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp" / "hardening2"
RES = ROOT / "redteam" / "hardening2" / "results"
REG = ROOT / "redteam" / "hardening2" / "registry"
CACHE = {"test": ROOT / "tmp" / "hardening" / "cache_test.jsonl",
         "train": ROOT / "tmp" / "hardening" / "cache_train.jsonl"}
PY = sys.executable
START = time.time()


def log(msg: str) -> None:
    print(f"[audit2 {time.time() - START:7.0f}s] {msg}", flush=True)


def step(name: str, fn) -> None:
    marker = WORK / f"done_{name}"
    if marker.exists():
        log(f"skip {name}")
        return
    log(f"start {name}")
    t = time.time()
    fn()
    marker.write_text(f"{time.time() - t:.0f}\n")
    log(f"done {name} ({time.time() - t:.0f}s)")


def sh(cmd: list, env: dict | None = None) -> None:
    log("$ " + " ".join(map(str, cmd)))
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT, env=dict(os.environ, **(env or {})))


def install(names: list[str]) -> None:
    for n in names:
        dst = ROOT / "proposers" / f"{n}.sh"
        shutil.copy(REG / f"{n}.sh", dst)
        dst.chmod(0o755)


def uninstall_all() -> None:
    for f in REG.glob("*.sh"):
        (ROOT / "proposers" / f.name).unlink(missing_ok=True)


def evaluate(slice_: str, tag: str, only: list[str] | None, experiments: list[str] | None,
             extra: list[str] | None = None) -> None:
    cmd = [PY, f"eval/{slice_}/evaluate.py", "--out", RES / f"{tag}_scores_{slice_}.json",
           "--details", RES / f"{tag}_details_{slice_}.json", "--cache", CACHE[slice_]]
    if only:
        cmd += ["--only", *only]
    if experiments:
        cmd += ["--experiments", *experiments]
    cmd += extra or []
    if slice_ == "test":
        subprocess.run(["chmod", "u+rwx", str(ROOT / "eval" / "test")], check=False)
    sh(cmd)


def run_variant(tag: str, names: list[str], slice_: str, experiments: list[str] | None) -> None:
    install(names)
    try:
        evaluate(slice_, tag, names, experiments)
    finally:
        for n in names:
            (ROOT / "proposers" / f"{n}.sh").unlink(missing_ok=True)


def selftest() -> None:
    """Run every audit proposer on four JGEX instances and check its output with the gate (log only)."""
    sys.path.insert(0, str(ROOT / "eval" / "test"))
    import gate  # noqa: E402

    probs = [json.loads(l) for l in (ROOT / "eval/test/problems_jgex.jsonl").read_text().splitlines()
             if l.strip()][:4]
    rows = [{"problem_id": p["problem_id"], "setup": p["setup"], "points": gate.setup_point_names(p["setup"]),
             "coords": p["coords"], "difficulty": None, "max_attempts": 16, "max_aux_per_attempt": 3,
             "cpu_seconds_per_problem": 5.0} for p in probs]
    inp = WORK / "selftest_in.jsonl"
    inp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    for f in sorted(REG.glob("*.sh")) + [ROOT / "proposers" / "hageo.sh", ROOT / "baseline" / "random_aux.sh"]:
        if f.stem in ("sc_cpu_hog", "sc_goal_lookup", "sc_read_hidden"):
            continue
        out = WORK / f"selftest_{f.stem}.jsonl"
        tmp_script = ROOT / "proposers" / f"_selftest_{f.stem}.sh"
        shutil.copy(f, tmp_script)
        try:
            r = subprocess.run(["bash", str(tmp_script), str(inp), str(out)], cwd=ROOT, capture_output=True,
                               text=True, timeout=900)
            ok = r.returncode == 0
            msg = r.stderr[-600:]
            if ok:
                out_rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
                att = gate.validate_rows(out_rows, probs, 16, 3)
                msg = f"attempts={[len(a) for a in att.values()]} first={next(iter(att.values()))[:2]}"
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, f"{type(exc).__name__}: {exc}"
        finally:
            tmp_script.unlink(missing_ok=True)
        log(f"selftest {f.stem}: {'OK' if ok else 'FAIL'} {msg}")


def train_rank(ref: dict, var: dict) -> float:
    """Selection score on the visible JGEX train instances."""
    a, b = var, ref
    if not a or not b:
        return float("-inf")
    return (a["solve_rate"] - b["solve_rate"]) + 0.5 * (a["pass_auc"] - b["pass_auc"])


ALL = None  # every experiment
CHEAP_ON_HAGEO = ["hageo_seed1", "hageo_seed2", "hageo_hybrid", "hageo_unfiltered", "hageo_n1", "systematic"]
CANDIDATES = ["hageo_ext_hybrid", "hageo_ext", "hageo_hybrid"]


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    uninstall_all()
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")

    # 1. JGEX-231: eight independent instances per problem (test and train)
    step("instances", lambda: sh([PY, "eval/test/build_split.py", "instances", "--source", "jgex",
                                  "--copies", "8"]))
    step("selftest", selftest)

    # 2. fixed baselines for the expanded JGEX sets
    for s in ("test", "train"):
        step(f"baselines_{s}", lambda s=s: evaluate(s, "baselines_jgex", None, ["jgex231_aux"],
                                                     ["--recompute-baselines", "--no-proposers"]))

    def sanity_baselines():
        for s, path in (("test", ROOT / "eval/test/baselines_jgex.json"),
                        ("train", ROOT / "eval/train/baselines_jgex.json")):
            b = json.loads(path.read_text())
            n = len(b["ddar"])
            ddar = sum(1 for v in b["ddar"].values() if v is not None)
            rnd = sum(1 for v in b["random_aux"].values() if v is not None)
            log(f"baselines jgex {s}: n={n} ddar={ddar} random_aux={rnd}")
            if ddar:
                raise SystemExit("DDAR alone proves JGEX instances; stopping for inspection")
    step("sanity_baselines", sanity_baselines)

    # 3. reference only, through the unchanged no-argument scripts (+ audit cache)
    def ref(s):
        sh(["bash", f"scripts/evaluate_{s}.sh"], env={"EVAL_CACHE": str(CACHE[s])})
        shutil.copy(ROOT / "scoring" / f"scores_{s}.json", RES / f"reference_scores_{s}.json")
        shutil.copy(ROOT / "outputs" / f"eval_{s}_details.json", RES / f"reference_details_{s}.json")
        d = json.loads((RES / f"reference_details_{s}.json").read_text())
        bad = {e: d[e]["hageo"]["status"] for e in d if not d[e]["hageo"]["status"].startswith("ok")}
        if bad:
            raise SystemExit(f"reference failed: {bad}")
    for s in ("test", "train"):
        step(f"reference_{s}", lambda s=s: ref(s))

    # 4. variants whose HAGeo-409 attempts are already verified (cache): every experiment
    for n in CHEAP_ON_HAGEO:
        step(f"test_{n}", lambda n=n: run_variant(n, [n], "test", ALL))

    # 5. candidate improvements: JGEX test, JGEX train; choose on train
    for n in ("hageo_ext_hybrid", "hageo_ext"):
        step(f"test_jgex_{n}", lambda n=n: run_variant(f"jgex_{n}", [n], "test", ["jgex231_aux"]))
    for n in CANDIDATES + ["hageo_seed1"]:
        step(f"train_jgex_{n}", lambda n=n: run_variant(f"jgex_{n}", [n], "train", ["jgex231_aux"]))

    def choose():
        ref_r = json.loads((RES / "reference_scores_train.json").read_text())
        ref_r = ref_r["experiments"]["jgex231_aux"]["results"]["hageo"]
        best, best_v = None, float("-inf")
        for n in CANDIDATES:
            sc = json.loads((RES / f"jgex_{n}_scores_train.json").read_text())
            v = train_rank(ref_r, sc["experiments"]["jgex231_aux"]["results"].get(n))
            log(f"train selection {n}: {v:+.4f}")
            if v > best_v:
                best, best_v = n, v
        (WORK / "better_variant.txt").write_text(best + "\n")
    step("choose_better", choose)

    # 6. shortcut probes (fail fast or reuse verified reference attempts)
    step("shortcuts_fast", lambda: run_variant("shortcuts_fast", ["sc_read_hidden", "sc_goal_lookup",
                                                                  "sc_cpu_hog"], "test", ALL))
    # 7. short rules and private lookahead on JGEX
    for n in ("rule_mixed3", "rule_circumcenters", "sc_lookahead"):
        step(f"test_jgex_{n}", lambda n=n: run_variant(f"jgex_{n}", [n], "test", ["jgex231_aux"]))

    # 8. train-selected variant on HAGeo-409 (test, train); lookahead and rules on HAGeo-409 last
    better = (WORK / "better_variant.txt").read_text().strip()
    if better not in CHEAP_ON_HAGEO:
        step(f"test_hageo_{better}", lambda: run_variant(f"hageo409_{better}", [better], "test", ["hageo409_aux"]))
    step(f"train_all_{better}", lambda: run_variant(f"train_{better}", [better], "train", ALL))
    step("test_hageo_sc_lookahead", lambda: run_variant("hageo409_sc_lookahead", ["sc_lookahead"], "test",
                                                        ["hageo409_aux"]))
    # 9. direct-open probe of the held-out files during a proposer run (attempts = reference's, cached)
    step("probe_read_hidden", lambda: run_variant("probe_read_hidden", ["sc_read_hidden"], "test",
                                                  ["jgex231_aux"]))
    # 10. private lookahead re-measured on JGEX under the tightened CPU allowance (2 s per problem)
    step("test_jgex_sc_lookahead_v2", lambda: run_variant("jgex_sc_lookahead_v2", ["sc_lookahead"], "test",
                                                          ["jgex231_aux"]))
    # 10b. same probe with robust budget control (the v2 run overshot: AlphaGeometry's bare
    #      `except:` clauses swallowed its one-shot CPU timer)
    step("test_jgex_sc_lookahead_v3", lambda: run_variant("jgex_sc_lookahead_v3", ["sc_lookahead"], "test",
                                                          ["jgex231_aux"]))
    # 11. final configuration: fixed baselines (all experiments) and the reference, through the
    #     unchanged scripts; attempts are identical, so verification comes from the cache.
    for s in ("test", "train"):
        step(f"baselines_final_{s}", lambda s=s: evaluate(s, "baselines_final", None, ALL,
                                                           ["--recompute-baselines", "--no-proposers"]))
    for s in ("test", "train"):
        step(f"reference_final_{s}", lambda s=s: ref(s))
    sh([PY, "redteam/hardening2/summarize.py"])
    uninstall_all()
    log("all steps done")


if __name__ == "__main__":
    try:
        main()
    finally:
        uninstall_all()
        subprocess.run(["chmod", "u+rwx", str(ROOT / "eval" / "test")], check=False)
