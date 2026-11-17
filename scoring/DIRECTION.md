# Research Direction

The benchmark studies CPU-only auxiliary-construction proposal for a fixed symbolic geometry prover (DD+AR) under a small attempt budget.

In scope: which candidate points to generate (intersections, midpoints, reflections, feet, circle constructions, multi-point compositions), how to filter and rank them from the numerical drawing, how to spend the 16 attempts (ordering, diversity, how many points per attempt), and any goal-agnostic analysis of the configuration, including running your own copy of the prover on the premises within the proposer's CPU allowance (which is a small multiple of what the reference needs, so the attempt budget, not private search, is what a better method has to use well).

Out of scope: recovering the goals (from the evaluator's files or from the public benchmark statements), neural or LLM proposal models, external problem/proof databases, changing the prover, the problem sets, the CPU allowance or the budget.
