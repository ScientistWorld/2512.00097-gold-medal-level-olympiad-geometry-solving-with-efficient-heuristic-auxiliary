# Experiment Overview

This file describes each experiment present in `scoring/scores.json`. It is method-agnostic and intentionally avoids implementation details.

## auxiliary_core

This one-problem benchmark checks whether a solver can prove a geometry theorem that the DDAR-only baseline does not solve. It establishes the minimum reproduced claim: adding a valid auxiliary construction can change the theorem from unsolved to solved while staying inside a declared CPU-only evaluation budget.

## hageo409_low_difficulty

This scaled benchmark checks whether a solver remains effective beyond the controlled sanity case on formal Olympiad geometry problems from the public HAGeo-409 benchmark. It uses a fixed low-difficulty slice so runs stay practical, and compares the submitted solver against a matched random auxiliary-construction baseline under the same declared budget.
