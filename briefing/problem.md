# Problem Definition

This benchmark is about automated Euclidean geometry theorem proving with auxiliary constructions. Each problem is stated in AlphaGeometry's point-construction language: a list of premises that construct points, and a goal (collinearity, concyclicity, equal angles, equal lengths, ...). A fixed symbolic prover (deductive database + algebraic reasoning, "DDAR") closes the premises under its rules. For every problem in the scored sets, that closure does **not** contain the goal: the prover saturates without proving it. Adding well-chosen new points (auxiliary constructions) to the premises can make the goal derivable.

## Task

A submission is a *proposer*: given a problem's premises (without the goal) and a numerical drawing of the configuration, it returns up to 16 attempts, each a short list (at most 3) of auxiliary point constructions. The evaluator adds each attempt to the premises and runs its own prover. A problem counts as solved when some attempt within the budget lets the prover derive the goal.

## Research Question

Which auxiliary constructions should be tried, and in what order, so that a fixed CPU-only prover proves as many problems as possible within a small attempt budget, without neural inference and without seeing the goal?

## Why It Matters

Auxiliary constructions are the creative step in olympiad geometry: symbolic provers are complete over a fixed configuration but cannot invent new points. A proposer that finds useful constructions with few attempts makes symbolic proving both stronger and cheaper. The scored problems come from public olympiad collections with human difficulty ratings and from a classic textbook-theorem benchmark.

## Success Criteria

Prove more held-out problems within the attempt budget, prove them with fewer attempts, and do so on the harder problems too, while every construction is a legitimate definition of a new point (no extra assumptions) and the proposer stays within its compute limit.
