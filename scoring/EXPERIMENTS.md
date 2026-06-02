# Experiment Overview

This file describes what each scored experiment is trying to establish. It intentionally avoids method internals.

## hageo409_scaled

This experiment checks whether a solver improves over a random auxiliary-construction baseline on a fixed low-difficulty slice of the HAGeo-409 formal benchmark while staying within a declared CPU-only search budget. It is the current paper-claim-facing target because the paper's main benchmark comparison is HAGeo versus random auxiliary construction on HAGeo-409.

## auxiliary_core

This one-problem smoke benchmark checks that the environment can distinguish a prover that uses auxiliary constructions from a DDAR-only baseline. It is not a full benchmark reproduction; it is a quick guard that the solver output and evaluator wiring work.
