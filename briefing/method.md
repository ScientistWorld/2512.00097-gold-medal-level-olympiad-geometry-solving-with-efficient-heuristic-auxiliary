# Paper's Method

## Key Contribution

The paper introduces HAGeo, a CPU-only automated Euclidean geometry theorem prover that replaces neural auxiliary-construction proposal with a heuristic construction strategy guided by numerical geometry checks. It pairs this strategy with an optimized deductive database and algebraic reasoning engine, then evaluates the system on both IMO-30 and a new 409-problem benchmark with difficulty labels.

## Approach

HAGeo first parses each problem into a geometry-specific construction language containing points, lines, circles, and construction actions. The problem is encoded as a deduction graph and passed through a DDAR-style prover: a deductive database applies geometric inference rules, while an algebraic reasoning module derives angle, length, and ratio consequences through matrix-based linear reasoning.

If the initial prover run does not establish the conclusion, HAGeo performs multiple auxiliary-construction attempts. Each attempt builds a short sequence of added constructions, then reruns the prover on the augmented problem. Candidate auxiliary points are generated from geometric configurations that appear promising under numerical checks, including multi-object intersections, midpoints, reflections, perpendicular feet, identical-point opportunities, and random constructions. The numerical checks are used to select valid construction candidates, not to assume the theorem's conclusion.

The paper also modifies DDAR implementation details to improve speed while preserving deductive capacity. These changes include optimized deduction rules, support for identical points, and matrix-level algebraic reasoning optimizations that reduce redundant variables and computation.

## Main Claims

- **Primary claim:** HAGeo achieves gold-medal-level performance on IMO-30 without neural inference, solving 28/30 problems.
- **Primary benchmark claim:** HAGeo substantially outperforms AlphaGeometry and random auxiliary-construction baselines on HAGeo-409, including across human difficulty bands.
- **Constraint claim:** The system's strong solve rate is obtained using CPU-only inference rather than GPU-backed neural proposal models.
- **Efficiency claim:** The optimized DDAR engine is roughly 20x faster than AlphaGeometry's DDAR implementation in the paper's comparison.
- **Benchmark claim:** HAGeo-409 is a more informative evaluation set than IMO-30 because it is larger and includes human-assessed difficulty annotations.
