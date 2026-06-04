# Experiment Overview

This file describes each experiment present in `scoring/scores.json`. It is method-agnostic and intentionally avoids implementation details.

## auxiliary_core

This one-problem benchmark checks whether a submitted geometry prover can solve a controlled formal theorem that the provided base reference system does not solve. It establishes the minimum reproduced claim that a stronger CPU-only prover can turn the instance from unsolved to solved while staying inside a declared evaluation budget.

## hageo409_low_difficulty

This scaled benchmark checks whether a solver remains effective beyond the controlled sanity case on formal Olympiad geometry problems from the public HAGeo-409 benchmark. It uses a fixed low-difficulty slice so runs stay practical, and compares submitted systems against a matched non-neural reference baseline under the same declared budget.
