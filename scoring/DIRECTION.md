# Research Direction

## Research Problem

This benchmark studies automated theorem proving for Euclidean geometry at Olympiad difficulty. The core question is how to improve exact geometry reasoning systems so they solve more formally specified problems within practical CPU budgets while producing valid proofs or proof certificates.

## Core Contribution

The paper's contribution is in CPU-only geometry theorem proving with improved auxiliary-construction search and efficient deductive-algebraic reasoning. A future scientist should work on the same kind of contribution: better ways for a non-neural geometry prover to extend, search, organize, or exploit formal geometric information under fixed benchmark and resource constraints.

## Approach Scope

In-bounds research should keep the system within automated Euclidean geometry theorem proving over the provided formal construction language. The scientist may improve symbolic deduction, algebraic reasoning, search control, auxiliary object proposal, proof-state scoring, caching, pruning, or deterministic/stochastic exploration policies, provided evaluation remains CPU-only and non-neural.

The scientist may also change implementation details that improve efficiency or reliability, such as data structures, indexing, equation handling, parallel scheduling, proof reconstruction, or evaluator integration. These changes should be judged by whether they improve valid solve rates or runtime under the same benchmark protocol.

## Out of Bounds

- Replacing the task with natural-language geometry solving or a different theorem-proving formalism that bypasses the provided benchmark representation.
- Using LLMs, neural guidance models, learned retrievers, or online services during evaluation.
- Importing external geometry datasets, proof traces, theorem libraries, or human solutions to increase coverage.
- Changing the benchmark problems, conclusions, difficulty labels, or scoring rules.
- Beating the score primarily by using more attempts, longer runtime, GPU computation, or larger external resources rather than a better reasoning method.
