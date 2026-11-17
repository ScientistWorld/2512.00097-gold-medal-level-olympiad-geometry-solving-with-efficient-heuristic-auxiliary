#!/usr/bin/env python3
"""Hardening-2 job driver (audit only, never part of the gym).

Resumable: every step leaves a marker in tmp/hardening2/ and is skipped when
the marker exists.  Verification results are memoised in the evaluator's
audit cache (tmp/hardening/cache_{train,test}.jsonl, shared with the previous
hardening audit), so identical attempts are never re-proved.

Steps
  1. generate and select the synthetic problems (eval/test/derive.py)
  2. fixed baselines (DDAR alone, random auxiliaries) on the synthetic sets
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
    """Run every audit proposer on four derived problems and check its output with the gate (log only)."""
    sys.path.insert(0, str(ROOT / "eval" / "test"))
    import gate  # noqa: E402

    probs = [json.loads(l) for l in (ROOT / "eval/test/problems_synthetic.jsonl").read_text().splitlines()
             if l.strip()][:4]
    rows = [{"problem_id": p["problem_id"], "setup": p["setup"], "points": gate.setup_point_names(p["setup"]),
             "coords": p["coords"], "difficulty": None, "max_attempts": 16, "max_aux_per_attempt": 3,
             "cpu_seconds_per_problem": 3.0} for p in probs]
    inp = WORK / "selftest_in.jsonl"
    inp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    for f in sorted(REG.glob("*.sh")) + [ROOT / "proposers" / "hageo.sh", ROOT / "baseline" / "random_aux.sh"]:
        if f.stem in ("sc_cpu_hog", "sc_goal_lookup", "sc_read_hidden"):
            continue
        out = WORK / f"selftest_{f.stem}.jsonl"
        tmp_script = ROOT / "proposers" / f"_selftest_{f.stem}.sh"
        shutil.copy(f, tmp_script)
        t = time.process_time()
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


def train_rank(scores: dict, name: str, ref: str = "hageo") -> float:
    r = scores["experiments"]["synthetic_aux"]["results"]
    a, b = r.get(name), r.get(ref)
    if not a or not b:
        return float("-inf")
    return (a["solve_rate"] - b["solve_rate"]) + 0.5 * (a["pass_auc"] - b["pass_auc"])


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    uninstall_all()
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")

    # 1. synthetic problems
    # Public-base configurations proved slow and almost never productive in the first
    # 12 minutes (2 of 147), so generation continues with random configurations only.
    step("derive_generate", lambda: sh([PY, "eval/test/derive.py", "generate", "--budget-seconds", "7200",
                                        "--stop-productive", "300", "--public-every", "100000"]))
    step("derive_select", lambda: sh([PY, "eval/test/derive.py", "select", "--max-test", "240",
                                      "--max-train", "120"]))

    def sanity_select():
        summary = json.loads((ROOT / "eval" / "test" / "synthetic_summary.json").read_text())
        log(f"synthetic summary: {json.dumps(summary)}")
        if summary["test"]["problems"] < 100 or summary["train"]["problems"] < 50:
            raise SystemExit("too few synthetic problems; stopping for inspection")
    step("sanity_select", sanity_select)
    step("selftest", selftest)

    # 2. fixed baselines on the new experiment
    for s in ("test", "train"):
        step(f"baselines_{s}", lambda s=s: evaluate(s, "baselines_synth", None, ["synthetic_aux"],
                                                     ["--recompute-baselines", "--no-proposers"]))

    def sanity_baselines():
        for s, path in (("test", ROOT / "eval/test/baselines_synthetic.json"),
                        ("train", ROOT / "eval/train/baselines_synthetic.json")):
            b = json.loads(path.read_text())
            n = len(b["ddar"])
            ddar = sum(1 for v in b["ddar"].values() if v is not None)
            rnd = sum(1 for v in b["random_aux"].values() if v is not None)
            log(f"baselines {s}: n={n} ddar={ddar} random_aux={rnd}")
            if ddar:
                raise SystemExit("DDAR alone proves synthetic problems; stopping for inspection")
    step("sanity_baselines", sanity_baselines)

    # 3. reference only, through the unchanged no-argument scripts (+ audit cache)
    def ref(s):
        sh(["bash", f"scripts/evaluate_{s}.sh"], env={"EVAL_CACHE": str(CACHE[s])})
        shutil.copy(ROOT / "scoring" / f"scores_{s}.json", RES / f"reference_scores_{s}.json")
        shutil.copy(ROOT / "outputs" / f"eval_{s}_details.json", RES / f"reference_details_{s}.json")
    for s in ("test", "train"):
        step(f"reference_{s}", lambda s=s: ref(s))

    # 4a. shortcut probes that end quickly (failures or cached reference attempts)
    step("shortcuts_fast_test", lambda: run_variant("shortcuts_fast", ["sc_read_hidden", "sc_goal_lookup",
                                                                        "sc_cpu_hog"], "test", None))

    # 4b. variants on the new experiment (held-out), most informative first
    derived_test = ["hageo_seed1", "hageo_ext_hybrid", "hageo_ext", "hageo_hybrid", "hageo_unfiltered",
                    "rule_mixed3", "rule_circumcenters", "hageo_seed2", "sc_lookahead", "systematic", "hageo_n1"]
    for n in derived_test[:4]:
        step(f"synth_test_{n}", lambda n=n: run_variant(f"synth_{n}", [n], "test", ["synthetic_aux"]))

    # 4c. candidate improvements on the visible train set (selection is made on train)
    for n in ("hageo_ext_hybrid", "hageo_ext", "hageo_hybrid"):
        step(f"synth_train_{n}", lambda n=n: run_variant(f"synth_{n}", [n], "train", ["synthetic_aux"]))

    def choose():
        ref_scores = json.loads((RES / "reference_scores_train.json").read_text())
        best, best_v = None, float("-inf")
        for n in ("hageo_ext_hybrid", "hageo_ext", "hageo_hybrid"):
            sc = json.loads((RES / f"synth_{n}_scores_train.json").read_text())
            merged = {"experiments": {"synthetic_aux": {"results": {
                "hageo": ref_scores["experiments"]["synthetic_aux"]["results"]["hageo"],
                n: sc["experiments"]["synthetic_aux"]["results"].get(n)}}}}
            v = train_rank(merged, n)
            log(f"train selection {n}: {v:+.4f}")
            if v > best_v:
                best, best_v = n, v
        (WORK / "better_variant.txt").write_text(best + "\n")
    step("choose_better", choose)

    for n in derived_test[4:]:
        step(f"synth_test_{n}", lambda n=n: run_variant(f"synth_{n}", [n], "test", ["synthetic_aux"]))

    # 4d. the train-selected variant and the lookahead on the two public-problem experiments
    better = (WORK / "better_variant.txt").read_text().strip()
    step("better_old_test", lambda: run_variant(f"old_{better}", [better], "test",
                                                ["jgex231_aux", "hageo409_aux"]))
    step("lookahead_jgex_test", lambda: run_variant("old_sc_lookahead_jgex", ["sc_lookahead"], "test",
                                                    ["jgex231_aux"]))
    step("better_old_train", lambda: run_variant(f"old_{better}", [better], "train",
                                                 ["jgex231_aux", "hageo409_aux"]))
    step("lookahead_hageo_test", lambda: run_variant("old_sc_lookahead_hageo", ["sc_lookahead"], "test",
                                                     ["hageo409_aux"]))
    uninstall_all()
    log("all steps done")


if __name__ == "__main__":
    try:
        main()
    finally:
        uninstall_all()
        subprocess.run(["chmod", "u+rwx", str(ROOT / "eval" / "test")], check=False)
