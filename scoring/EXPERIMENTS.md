# Experiment Overview

Both experiments ask the same question on different problem populations: given a geometry configuration that a fixed symbolic prover cannot finish on its own, can a submitted proposer supply auxiliary constructions that let the prover reach the goal within a small attempt budget? Every number is computed by the evaluator from its own proof runs.

## hageo409_aux

Held-out olympiad problems from the public HAGeo-409 benchmark, with human difficulty ratings, on which the prover alone provably stops short of the goal. It measures how many such problems a proposer turns into proofs within 16 attempts, how quickly (fewer attempts is better), and whether this extends to the problems rated difficulty 3 and above. At the benchmark's scale these problems are hard: every method proves only a few, so differences of one problem are within noise; this is why it carries the smaller weight (0.3).

## jgex231_aux

Held-out problems from JGEX-231, a classic public benchmark of textbook-to-olympiad geometry theorems, again restricted to problems on which the prover alone stops short of the goal. The configurations are smaller, so the same question can be measured with more solved problems and a clearer separation between proposers. Each of the 18 held-out problems is presented as 8 independent instances (different point names and drawing), so a proposer's own randomness averages out and two proposers are compared on the same 144 instances. It measures how many instances are proved within 16 attempts and how quickly. It carries the larger weight (0.7) because it resolves differences between proposers well above the run-to-run noise of a single proposer; `hageo409_aux` has weight 0.3.
