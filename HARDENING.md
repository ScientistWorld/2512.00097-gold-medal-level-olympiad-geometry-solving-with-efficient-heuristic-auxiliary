# Hardening report (second hardening)

This gym was hardened once before. That pass made methods into goal-free *proposers*. The evaluator proves every attempt itself with its own DD+AR prover, and a validity gate rejects illegal constructions; see "First hardening" at the end. `REVIEW.md` then found one remaining weakness. The test was tiny (38 HAGeo-409 + 18 JGEX-231 problems), and the better (hybrid) proposer gained less than the reference's seed noise: rank +0.17 against a seed range of −0.92 to −0.28. The review asked to enlarge the test until a better proposer separates from the reference beyond noise.

All numbers below come from the held-out evaluator (`eval/test/evaluate.py`, the code behind the no-argument `scripts/evaluate_test.sh`), run with every variant installed under `proposers/`. The audit driver is `redteam/hardening2/audit.py` and the variants are in `redteam/hardening2/registry/`. Raw scores and per-problem details are in `redteam/hardening2/results/*_{scores,details}_{test,train}.json`, merged in `results/summary.json` by `summarize.py`.

**Rank** is the red team's diagnostic, Σ weight · |coef| · Δ/σ, with Δ taken against the reference. σ is the population standard deviation of each metric over this audit's honest cohort of 13 methods: the reference's three seeds, the HAGeo variants, the two rules, capped enumeration, `random_aux` and `ddar`. A future cohort will have a different σ.

## What changed

1. **JGEX-231 is scored on 8 independent instances per problem.**
   - **What:** `eval/test/build_split.py instances`. Instance 1 is the problem as before. Instances 2–8 use a fresh point renaming and a fresh drawing seed, and each is re-checked: DDAR alone still saturates without the goal under the problem's CPU limit.
   - **Size:** 144 hidden test instances (18 problems) and 96 train instances (12 problems).
   - **Why:** a seeded proposer makes independent draws on each instance, so its own randomness averages out. All methods are compared paired, on the same instances.
   - **Limit:** the number of *distinct* problems does not change.
2. **Weights changed from 0.5/0.5 to 0.3 (`hageo409_aux`) / 0.7 (`jgex231_aux`).**
   - **Why:** at the gym's scale every method proves 1–3 of the 38 HAGeo-409 problems. The reference's seed spread in rank came almost entirely from one HAGeo-409 problem: seed 1 proves 2/38, seeds 0 and 2 prove 3/38.
   - **Paper's benchmark:** HAGeo-409 is the paper's benchmark and stays scored, but it cannot resolve more than about one problem here.
3. **Proposer limit is CPU time, not wall-clock.**
   - **What:** it is measured over the proposer's whole process tree (`RUSAGE_CHILDREN`, plus `RLIMIT_CPU` as an early stop). The allowance is 6 s per problem for `hageo409_aux` and 2 s for `jgex231_aux`, at least 120 s per experiment.
   - **Backstop:** only a far wall-clock backstop remains, 10× the CPU allowance plus 300 s, against hangs. The verification wall backstop was raised from 4×+60 s to 10×+120 s.
   - **Threads:** numerical libraries are forced single-threaded (`OMP_NUM_THREADS=1` etc.) in the evaluator and every proposer. Before this, idle BLAS threads inflated measured CPU time: the reference was charged 255 s of CPU for 42 s of wall time.
   - **Reference use:** single-threaded, the reference needs 31.9 / 228 s (HAGeo-409 test), 30.7 / 288 s (JGEX test), 18.8 / 150 s and 39.2 / 192 s (train), i.e. at most about a fifth of the allowance.
4. **Held-out files are unreadable while a proposer runs.** `eval/test` is chmod 000 for the duration of each proposer run and restored afterwards; the evaluator has already loaded everything into memory. `scripts/evaluate_test.sh` restores the permission first in case an earlier run was killed.
5. **Docs updated:** `briefing/evaluation.md`, `briefing/method.md`, `proposers/README.md`, `scoring/{TARGETS,EXPERIMENTS,CONSTRAINTS,DIRECTION}.md` and `scoring/reference.json`.
   - `reference.json` has new weights and new JGEX reference values. The paper's numbers are unchanged under `hageo409_aux._paper_reported`.

### Tried and dropped: a generator of new aux-requiring problems

Two generators were built, run and rejected. The code and numbers are in `redteam/hardening2/synthetic_attempt/`.

- **Hidden extra point on a real configuration.** Real HAGeo-409/JGEX-231 configurations plus a secret random point, keeping facts about the original points that DDAR derives only with that point. It produced almost nothing: 5 of 920 samples, because olympiad configurations are closed under DDAR apart from their own goal.
- **AlphaGeometry-style "dependency difference" on secret random configurations.** These were triangles plus 4–7 constructions weighted like the benchmarks' statements. It produced 188 test and 101 train problems, every one re-verified (DDAR alone saturates, the known construction proves it).
  - **Too easy:** the random baseline proved 169/188 test problems, 76 of them on its first attempt.
  - **No hard subset:** 125/141 one-point and 44/47 two-point problems were solved.
  - **Why:** on these small configurations (5.7 points on average) most such "theorems" are gaps in DDAR's deduction that almost any extra point fills, not genuine construction problems. The experiment would have been saturated by its own simple baseline, so it was not added.

## Do better results score higher? (hidden test)

| Method | JGEX solve / pass_auc (144 instances) | HAGeo-409 solve / hard / auc | Rank (0.3/0.7) | Rank at old weights 0.5/0.5 | Before (previous gym) |
|---|---|---|---|---|---|
| **reference** HAGeo, seed 0 | .618 / .453 | .079 / 0 / .059 | 0 | 0 | 0 |
| reference, seed 1 | .632 / .473 | .053 / 0 / .030 | −0.315 | −0.609 | −0.92 |
| reference, seed 2 | .611 / .455 | .079 / 0 / .048 | −0.065 | −0.089 | −0.28 |
| **hybrid**: 6 best-supported candidates first, then the paper's sampling | **.764 / .694** | .079 / 0 / .033 | **+0.881** | +0.532 | +0.17 |
| **extended hybrid**: hybrid + triangle centres, reflections in lines, perpendicular/parallel lines cut by a line, all under the incidence filter, and the trivial-circle fix for point reflections. Selected on train (train rank +2.21: JGEX .750/.661, HAGeo-409 7/25) | **.736 / .660** | .079 / 0 / .044 | **+0.762** | +0.490 | — |
| extended candidates, paper's random order | .646 / .459 | — | +0.108 | +0.077 | — |
| weaker: one auxiliary point per attempt (N = 1) | .500 / .354 | .026 / 0 / .012 | −1.366 | | −1.57 |
| weaker: no incidence filter (ablation) | .313 / .222 | .026 / 0 / .025 | −2.226 | | −2.18 |
| capped enumeration (midpoints, feet, line pairs, mirrors) | .333 / .226 | .079 / 0 / .066 | −1.411 | | −1.15 |
| random aux (fixed baseline) | .479 / .337 | .053 / .05 / .036 | −0.788 | −0.636 | −1.13 |
| DDAR alone | 0 / 0 | 0 / 0 / 0 | −4.132 | | −4.24 |

**Better methods now score higher, beyond the reference's seed noise.**
- **Seed range:** the reference's three seeds span rank [−0.315, 0], width 0.315. The hybrid (+0.881) and the train-selected extended hybrid (+0.762) both clear it by more than twice its width.
- **Paired evidence:** on the same 144 JGEX instances the hybrid proves 22 instances the reference misses and misses 1 the reference proves. The extended hybrid's count is 21 vs 4. The reference's seeds are 13 vs 11 and 13 vs 14.
- **Weaker methods** (one round, no incidence filter, enumeration, random, DDAR alone) all score below the reference.
- **The weight change matters.** At the old 0.5/0.5 weights the JGEX instances alone narrow the seed range to [−0.61, 0], and the hybrid's +0.53 still sits inside it. The residual noise there is the single HAGeo-409 problem.

## Major shortcuts: fix and score before → after (hidden test)

| Shortcut | Before | Fix | After |
|---|---|---|---|
| **Read the hidden goals while the proposer runs** (`sc_goal_lookup`: imports the evaluator's engine and reads `eval/test/problems*.jsonl`, then runs private DDAR to put a verified construction first) | rank +1.28 (previous audit), the only cheat clearly above the reference | `eval/test` is unreadable during every proposer run | proposer crashes on import, failed run, rank −4.13. A direct-open probe (`sc_read_hidden`) gets `PermissionError` and falls back to the reference's attempts: ties at 0, nothing read (`tmp/hardening2/read_hidden_status.txt`: `status=denied (PermissionError)`) |
| **Wall-clock proposer limit** (scores depend on machine load; a multi-process proposer can use many CPUs inside the wall limit) | 30 s per problem of wall time | CPU time over the process tree; numerical libraries single-threaded | `sc_cpu_hog` (4 processes, 1.3× the allowance, finishes far inside the old wall limit): "used 774 s of CPU time, above its limit of 570 s", failed run, rank −4.13 |
| **Private prover search inside the proposer** (`sc_lookahead`: saturates DDAR on the premises and on premises + each HAGeo candidate, puts candidates that unlock new facts first; never sees the goal) | (not measured) | per-problem CPU allowance tightened from 30 s wall to 6 s / 2 s CPU (the reference needs ~0.9 s / ~0.25 s) | at 5 s per problem on JGEX: .667 / .560, rank +0.381. At the final 2 s and 6 s: JGEX .639 / .511, HAGeo-409 = reference, rank **+0.187**, inside the reference's seed spread (0.315) and far below the honest hybrid. It wins 3 instances and loses 0, so it buys little |
| **Hand-written rules** (attempt *i* = *i*-th midpoint + *i*-th circumcentre + *i*-th foot; or 3 circumcentres per attempt) | (not measured) | none needed | JGEX .438 / .410 and .340 / .318; ranks −0.711 and −1.230. Not run on HAGeo-409 (3-point attempts there cost hours); a missing value is skipped, so these ranks count JGEX only |

Still closed from the first hardening and not re-run this time: constant or truthy `solved` flags, impossible metadata, replaced dataset goals, empty or partial output, unregistered methods, moved baselines, no auxiliary constructions, over-determined clauses, stale coordinates and more attempts than the budget. Every scored number is still the evaluator's own DDAR proof on its own premises, goals and budget, and any gate violation, crash, CPU overrun or malformed output scores 0 in every metric of every experiment.

## Shortcuts left open

- **Recovering goals from the public benchmark files.**
  - **What:** a proposer could ship HAGeo-409 or JGEX-231 statements, match a held-out problem to its public record (AlphaGeometry's canonical renaming undoes our renaming), and then search privately for a construction that proves the known goal.
  - **Why it stays open:** the goals are public, so no evaluator change can hide them. Private search is now bounded by the CPU allowance, which limits what such a cheat can do with the goal. It is forbidden in `scoring/CONSTRAINTS.md`, and the code would be plain to the separate shortcut grader.
- **Tampering with permissions.** A proposer runs as the same user and could `chmod` `eval/test` back. That is deliberate tampering, forbidden in `CONSTRAINTS.md` and obvious to the grader.
- **Git history.** The workspace's history contains earlier versions of `eval/test`. Hiding it is up to the infrastructure that prepares a scientist's workspace.
- **Private DDAR lookahead within the allowance.** This is a goal-agnostic method that `DIRECTION.md` allows. At the final allowance it gains +0.187, which is inside seed noise.

## Reference score before and after

| | Before (previous hardened gym) | After |
|---|---|---|
| `hageo409_aux` (38 hidden) | solve .079 (3/38), hard 0, pass_auc .059 | unchanged: .079, 0, .059 (same problems and attempts; recomputed under the final configuration) |
| `jgex231_aux` | 18 problems: solve .667 (12/18), pass_auc .458 | 144 instances: solve .618 (89/144), pass_auc .453. Instance 1 of each problem reproduces the old 12/18 |
| random aux | .053 / .389 | .053 / .479 (69/144) |
| DDAR alone | 0 / 0 | 0 / 0 |

Train: HAGeo-409 .12 (3/25) unchanged; JGEX 96 instances .469 / .321 (random .385). The final `scoring/scores_test.json` and `scores_train.json` hold only `hageo`, `random_aux` and `ddar`. They come from the reference runs under the final code and configuration; baselines were recomputed for every experiment.

## Headroom

- **Bounds:** the reference sits at the lower bound of only `hageo409_aux.hard_solve_rate` (0 on the hidden test; 0.077 on train). Every other scored metric is far from its bound: JGEX .618 / .453, HAGeo-409 .079 / .059.
- **A better method scores higher:** the hybrid (+0.881) and the extended hybrid (+0.762) do. The extended hybrid also proves 7/25 HAGeo-409 train problems against the reference's 3/25, though on the hidden 38 it ties at 3. The JGEX ceiling (1.0) is far above the best variant (.764).
- **Brute force does not solve the test.** The evaluator verifies at most 16 attempts and the goal is withheld. Capped enumeration ranks −1.41, and private search is bounded by the CPU allowance (above).
- **No simple rule reaches the reference.** Random, enumeration and both hand-written rules all rank below it.
- **No new experiment was added:** the synthetic generator's problems were saturated by the random baseline (see "Tried and dropped").

## Not fixed, stated plainly

1. **Few distinct problems.** The hidden test still has only 38 + 18 distinct problems. The JGEX instances remove the proposer's own randomness from paired comparisons, but not problem-sampling noise. A method tuned to these 18 problem *types* could look better than it would on new problems. Larger real sources were not affordable:
   - the 121 HAGeo-409 problems where DDAR alone needs more than 6 s;
   - the 107 HAGeo-409 problems with more than 13 points;
   - the 16 IMO-30 problems needing auxiliary points (about 43 s of DDAR each);
   - the generator route produced problems that were too easy.
2. **HAGeo-409 resolves about one problem.** That is why its weight dropped to 0.3. The paper's K = 2048, N = 6 and its optimized prover remain out of reach. The paper's IMO-30 result, the 20× engine speed-up and the identical-point heuristic are still not reproduced.
3. **Known reference departure left as is.** The reference counts the trivial circle (centred at B through A) as a favourable incidence for point reflections 2B − A, so every point reflection is a candidate. Fixing it would change the reference's attempts and require re-verifying HAGeo-409 for every seed (about an hour of CPU each on this cluster). The extended variant includes the fix. It is documented in `briefing/method.md`.
4. **One verification timer weakness.** The evaluator's DDAR CPU timer can be swallowed by bare `except:` clauses inside AlphaGeometry (`dd.py`, `ar.py`). The verdict stays correct: a proof found after the limit is not counted. But such an attempt can run until DDAR finishes or the wall backstop fires. It was not changed, because a periodic timer could flip borderline solves and break reproduction of the stored scores.
5. **Small train splits.** 25 HAGeo-409 problems, and 12 JGEX problems (96 instances). On train JGEX the hybrid gains less than on test (.490 vs .469), while the extended hybrid gains more (.750).

## Evidence and jobs (this iteration)

| Job | What it did | Outcome |
|---|---|---|
| `95eb8b21-e21` | hidden extra point on real configurations | cancelled: 5 of 920 samples productive |
| `943e6683-95a`, `43a53661-fa3` | AlphaGeometry-style synthetic generator, baselines, reference | cancelled. Random proved 169/188 synthetic problems, and the reference exceeded the then 3 s per problem CPU limit (multithreaded BLAS) |
| `d2303c91-e17` | JGEX instances, baselines, reference | cancelled after the reference was charged 255 s of CPU for 42 s of wall time; led to the single-threaded fix |
| `395b1f2c-1e9` | full audit: seeds, variants, rules, shortcuts, lookahead, final baselines and reference | completed (through several Slurm preemptions, resumed from markers) |
| `4f335967-835` | lookahead re-measured at the final allowance (budget-control fix) | completed |

`scripts/run.sh` again reproduces the reference end to end: `scripts/baseline.sh`, then `scripts/reproduce.sh`.

---

## First hardening (summary, unchanged)

- Methods became `proposers/<name>.sh` scripts that see premises and a drawing but not the goal.
- The evaluator holds the goals and proves every attempt with its own DD+AR copy under per-problem CPU limits, so written success flags, costs and difficulties are ignored.
- A gate requires each clause to define one fresh point exactly (no over-determination, no `@` coordinates, at most 16 attempts of at most 3 clauses). Any violation or malformed output is a failed run with the worst value in every metric of every experiment.
- Every `proposers/*.sh` on disk is scored, and baselines live in `eval/`.
- The reproduction follows the paper's §4.5: single defining constructions chosen for a favourable incidence, N rounds, and one DDAR call per attempt.
- The previous audit's code and results remain in `redteam/hardening/`.
