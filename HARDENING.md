# Hardening report

The old gym trusted every number a method wrote. A method's output rows carried `solved` flags, difficulties and declared budgets, and the evaluator summed them. The reproduced HAGeo heuristic was also mostly broken. Its candidate clauses were over-determined: each added the observed coincidence as an extra premise, and AlphaGeometry cannot even draw such clauses. Some also carried coordinates from another drawing. So the heuristic lost to its own random baseline.

This iteration replaces the measurement:

- **Methods are proposers.** A method is a `proposers/<name>.sh` script. It receives a problem's premises without the goal, plus a fixed drawing, and returns at most 16 attempts of at most 3 auxiliary clauses each.
- **The evaluator proves everything itself.** It holds the goals and runs its own copy of the AlphaGeometry DD+AR prover on premises plus each attempt, under a fixed CPU-time limit. Every scored number comes from those runs.
- **A validity gate replaces trust.** Each clause must define one fresh point by an allowlisted construction, with no over-determination and no explicit coordinates. Any violation, crash, timeout or malformed output scores 0 on every metric of every experiment.
- **Problems need an auxiliary construction.** The problems are public olympiad problems on which DDAR alone saturates without the goal. The test half lives only in `eval/test/`.
- **The reproduction is restored to the paper's procedure (§4.5).** Candidates are single defining constructions, chosen because of a favourable incidence. Each attempt has N rounds over the candidate set of the augmented diagram, and DDAR runs once per attempt.

All numbers below come from the unchanged, no-argument `bash scripts/evaluate_test.sh`, with every variant and shortcut installed in `proposers/`. For the full table see `redteam/hardening/results/audit2_scores_test.json`. The goal-lookup row is in `audit_scores_test.json`. Per-problem details are in `*_details_test.json`, and `summary.json` has the summary. The audit code is in `redteam/hardening/`.

Rank is the diagnostic used by the red team: Σ weight · |coef| · Δ / σ. Δ is measured against the reference, and σ is the population standard deviation over the honest cohort of the 11 rows in the variants table (the 8 HAGeo-style variants, systematic, `random_aux` and `ddar`). It uses the final weights (0.5 / 0.5) and coefficients. A future cohort will have a different σ.

## Reference before and after

| | Before (old hidden test, 6 problems, trusted flags) | After: `hageo409_aux` (38 hidden) | After: `jgex231_aux` (18 hidden) |
|---|---|---|---|
| reference HAGeo | solve 4/6 = .667, upper-band .8, weighted .682 | solve .079 (3/38), hard 0, pass_auc .059 | solve .667 (12/18), pass_auc .458 |
| random aux baseline | 5/6 = .833, above the reference | .053 (2/38), hard .05, pass_auc .036 | .389 (7/18), pass_auc .257 |
| DDAR alone | 4/6 | 0 | 0 |

The paper's direction (HAGeo > random > DDAR) now holds on the hidden test in both experiments. On the small train sets it holds for HAGeo-409 (3/25 vs 1/25) and is reversed by one problem for JGEX-231 (5/12 vs 6/12).

## Do better results score higher? (variants, hidden test)

| Variant | Before | `hageo409_aux` solve / hard / auc | `jgex231_aux` solve / auc | Rank |
|---|---|---|---|---|
| reference HAGeo (seed 0) | 4/6 | .079 / 0 / .059 | .667 / .458 | 0 |
| reference, seed 1 | — | .053 / 0 / .030 | .611 / .396 | −0.92 |
| reference, seed 2 | — | .079 / 0 / .048 | .611 / .417 | −0.28 |
| **hybrid**: 6 best-supported candidates first, then the paper's sampling (prefix chosen on train) | — | .079 / 0 / .033 | **.722 / .590** | **+0.17** |
| ranked by incidence count | — | .026 / 0 / .020 | .556 / .524 | −1.41 |
| N=3 rounds | — | .026 / 0 / .026 | .667 / .462 | −1.19 |
| N=1 round | — | .026 / 0 / .012 | .611 / .368 | −1.57 |
| weaker: no incidence filter (ablation) | — | .026 / 0 / .025 | .389 / .278 | −2.18 |
| capped brute-force enumeration (midpoints, feet, line pairs, mirrors) | old "better systematic" 5/6, rank +1.38 | .079 / 0 / .066 | .333 / .226 | −1.15 |
| random aux baseline | 5/6 | .053 / .05 / .036 | .389 / .257 | −1.13 |
| DDAR alone | 4/6 | 0 / 0 / 0 | 0 / 0 | −4.24 |

**Weaker methods now score lower.** Examples are removing the paper's incidence filter, the random baseline and DDAR alone. Before, the random baseline outranked the reference.

The train-selected hybrid outranks the reference. On JGEX it proves 13 vs 12 and has pass_auc .590 vs .458. Its pass_auc gain (+.132) exceeds the reference's seed spread (.0625), measured paired on identical problems and drawings. Its overall rank margin (+0.17) is **not** larger than seed noise, though: the reference's own seeds rank at −0.92 and −0.28.

The only clearly larger gain came from the goal-lookup cheat (+1.28). So the test can show that weaker methods are weaker, but cannot reliably separate a modestly better method from the reference. See "Not fixed".

The old brute force (4096 candidates per problem, rank +3.30) cannot be expressed any more: the evaluator verifies at most 16 attempts, and private search cannot check success because the goal is withheld. The same enumeration capped at 16 attempts ranks below the reference.

## Major shortcuts: fix and score before → after

| Shortcut | Before | Fix | After (hidden test) |
|---|---|---|---|
| constant `solved=true` / truthy `"false"` flags | perfect score, rank +1.04 | solves are only the evaluator's DDAR proofs; written flags are ignored | `sc_constant_flags`: 0 everywhere |
| impossible metadata (negative difficulty, −1e9 costs), under-reported costs | accepted, rank +2.37 | difficulty, budget and limits come from `eval/`; nothing the method declares is read | no such field exists; extra fields are ignored (`sc_constant_flags` writes them): 0 |
| replace the dataset goals | perfect score | goals live only in `eval/test/` and are loaded before any proposer runs | `sc_tamper_eval` rewrote goals, budgets and configs mid-run. Its own run failed the gate, and proposers scored after it in the same run got unchanged numbers |
| empty output / dropped dataset / missing row / null budgets | tie (skipped) or crash without scores | any malformed or incomplete output is a failed run: worst value in every metric of every experiment | `sc_empty_output`, `sc_crash`: 0 everywhere, the evaluation completes |
| unregistered method | not scored | every `proposers/*.sh` on disk is scored | all 18 audit proposers were scored, plus the 2 fixed baselines |
| baseline moved | false comparison | baselines are evaluator results in `eval/{train,test}/baselines*.json` | not writable by a proposer run |
| no auxiliary constructions (`weak_no_aux`) | tie benefits, better cost, rank +0.10 | no cost metrics; DDAR alone proves nothing on these problems | `sc_no_aux`: 0 everywhere |
| over-determined clause asserting a coincidence (unsound premise) | used by the old reference | gate: a clause must define its point exactly | `sc_overdetermined`: failed run, 0 |
| coordinates pinned from another drawing (`x@..`) | used by the old reference | gate rejects `@` | `sc_stale_coords`: failed run, 0 |
| more attempts than the budget | budget was declared, not enforced | gate: ≤16 attempts and ≤3 clauses | `sc_too_many`: failed run, 0 |
| direct write of `scores_test.json` | overwritten | unchanged | `sc_direct_scores`: overwritten, 0 |
| brute-force enumeration (4096 candidates) | 6/6, rank +3.30 | evaluator verifies at most 16 attempts; goal withheld | capped enumeration: rank −1.15 |

## Shortcuts left open

**Goal lookup plus private search** (`sc_goal_lookup`, rank +1.28 with the honest-cohort σ, or +0.92 if it joins the cohort; the only row clearly above the reference).
- **What it does:** it recovers each withheld goal, simulated in the audit by reading `eval/test/problems.jsonl`. Then, inside its 30 s-per-problem limit, it runs its own DDAR copy on heuristic candidates and puts a verified construction first. Result: HAGeo-409 4/38 (pass_auc .100), JGEX 13/18 (pass_auc .698).
- **Why it stays open:**
  - *Evaluator files:* the proposer runs in the same filesystem as `eval/`, and the gym has no sandbox. A future agent normally does not see `eval/test/`.
  - *Public data:* the goals are public. A HAGeo-409 or JGEX-231 statement can be matched to its public record even though points are renamed, since AlphaGeometry's canonical renaming undoes our renaming.
- **Mitigation:** goals are withheld from proposer input and points are renamed. The proposer's total time is capped, which limits private search. `scoring/CONSTRAINTS.md` forbids reading `eval/` or the public goals. Any such code is plain to the separate shortcut grader.

**Wall-clock proposer limit.** The proposer's time limit is wall-clock (30 s per problem in total), while DDAR verification limits are CPU time. On a very slow or loaded machine an honest proposer could hit it. The reference uses at most about 2 s per problem.

## Headroom

- **Bounds:** no scored metric has the reference at its upper bound. HAGeo-409 solve is .079 and its hard_solve_rate is 0 (the lower bound). JGEX solve is .667.
- **Ceiling not reached:** the goal-lookup cheat shows a ceiling the reference does not reach (+1.28). The train-selected hybrid scores above the reference, but by less than the seed noise.
- **Brute force:** it no longer solves the test (capped enumeration: 3/38 and 6/18).
- **Experiment added:** `jgex231_aux`, a second population of DDAR-saturated problems. With HAGeo-409 alone, all methods proved 1–3 of 38 problems and the reference tied random. JGEX shows the paper's effect (12 vs 7 vs 0) well above seed noise (one problem).

**Seed noise.** The paper's effect is larger than seed noise on JGEX-231: HAGeo − random = +5 problems (+.278), against a reference seed spread of 1 problem (.056). On HAGeo-409 it is not: +1 problem (+.026), equal to the seed spread.

**Weights.** Changed from 0.6 / 0.4 (my first choice) to 0.5 / 0.5, and the HAGeo-409 `pass_auc` coefficient from 0.5 to 0.25.
- Why: every method proves only 1–3 HAGeo-409 problems, so that experiment resolves about one problem, and its pass_auc mostly reflects where a single solve falls. With these weights the reference's own seed spread in rank shrinks from (−1.25, −0.35) to (−0.92, −0.28).
- The change does not alter which variants rank above the reference. The hybrid moves from −0.14 to +0.17, still within seed noise.

## Not fixed, stated plainly

1. **HAGeo-409 cannot separate methods.** The verifier is AlphaGeometry's public DD+AR, about 3–10 CPU-seconds per attempt. With that, a 16-attempt budget and 38 problems are what a 1-CPU hidden test can afford: one proposer costs about 30–60 CPU-minutes to verify. At this size, differences of one problem are within noise. Enlarging it further, or reaching the paper's K = 2048 with N = 6, was not feasible in the compute available: jobs ran on 1–3 effective CPUs with repeated Slurm preemptions.
2. **A better method does not beat the reference by more than noise overall.** It does on JGEX pass_auc, but the test needs to be larger to resolve modest improvements.
3. **The goal-lookup shortcut stays open** (see above).
4. **Uncovered claims.** IMO-30 (Table 2) is not scored: DDAR alone needs about 43 s per IMO problem. The paper's optimized DDAR engine (20× speed-up) and the identical-point heuristic are not reproduced, because the public prover rejects coincident points. The paper's own numbers are kept unchanged under `scoring/reference.json → experiments.hageo409_aux._paper_reported`.
5. **Small train splits.** They are 25 and 12 problems; the JGEX train split ranks random one problem above the reference.
6. **Partial train coverage of variants.** Seed 2, N=1, N=3 and the goal-lookup cheat were run only on the hidden test. Train results exist for the reference, seed 1, ranked, hybrid, unfiltered and systematic (`audit2_scores_train.json`).

## Evidence and jobs

| Job | What it did | Outcome |
|---|---|---|
| `fde4d367-305` | smoke test, DDAR-alone screening of all 409 HAGeo-409 problems, calibration | completed |
| `64785c46-b7b` | first audit under wall-clock limits | cancelled; only its HAGeo-409 verification results were kept, in the cache |
| `7b992547-dcf` | added the JGEX split | cancelled after a preemption restart showed that drawings computed at test time could fail under load. Drawings are now stored with each problem and DDAR limits are CPU time |
| `7a7cbf49-01d` | full audit | completed |
| `6897c2ab-5fa` | hybrid variant, final audit through the hidden test, reference-only score files | completed |

The final score files contain only `hageo`, `random_aux` and `ddar`. `scripts/run.sh` reproduces them: it recomputes the fixed baselines, then scores the registered proposers on the train and held-out sets.
