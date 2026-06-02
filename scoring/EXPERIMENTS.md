# Experiment Overview

This file describes what each scored experiment is trying to establish. It intentionally avoids method internals.

## auxiliary_core

This one-problem smoke benchmark checks that the environment can distinguish a prover that uses auxiliary constructions from a DDAR-only baseline. It is the minimum core-claim experiment: the baseline fails, while the proposed run must solve the same formal problem and report its construction budget.
