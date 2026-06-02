# Problem Definition

This benchmark is about automated Euclidean geometry theorem proving. A system receives a geometry problem expressed in a formal construction language and must determine whether the target conclusion follows from the premises by producing or internally certifying a valid proof.

## Research Question

Can an automated theorem prover solve challenging Olympiad-level Euclidean geometry problems reliably and efficiently under a fixed formal problem representation and bounded computational budget? The central gap is that existing benchmarks are small or comparatively easy, and prior high-performing systems often require expensive neural inference or very large search budgets.

## Why It Matters

Geometry theorem proving is a long-standing test of mathematical reasoning because successful solutions often require both exact deduction and useful auxiliary constructions. A strong benchmark environment should distinguish genuinely better reasoning systems from methods that only win by using more compute, richer external knowledge, or an easier problem set.

## Success Criteria

A successful system should solve a large fraction of held-out Olympiad-level geometry problems, maintain proof validity, perform well across difficulty bands rather than only on easy instances, and respect the declared resource and evaluation constraints. Efficiency matters because the paper's claim is not only about solving more problems, but doing so without neural inference and within practical CPU budgets.
