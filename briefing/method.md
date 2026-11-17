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

## Reference Implementation in This Gym

`proposers/hageo.sh` → `method/hageo/propose.py` implements the paper's auxiliary-construction procedure (Section 4.5) on top of AlphaGeometry's public DD+AR prover (the paper's optimized engine is not released):

- From the evaluator's numerical drawing it computes lines through pairs of points and circles through triples of points or centred at a point, and builds the paper's candidate categories: intersections of two lines through which a further line or circle passes, line/circle and circle/circle second intersections lying on a further object, midpoints and point reflections lying on a further line or circle, and feet of perpendiculars lying on a further line, plus a share of random constructions. The favourable incidence is only the reason to pick a point; each emitted clause states just the defining construction.
- Each of the K = 16 attempts has N = 2 rounds; in every round the candidate set of the current (augmented) diagram is recomputed and one point is chosen at random (the first round walks a random permutation so attempts start from different points). The evaluator runs DDAR once per attempt.
- Scaled settings: K = 16 (paper 2048/8192), N = 2 (paper 6), per-attempt CPU limits of 6-20 s (paper 60 s). The identical-point heuristic is omitted because the public prover rejects coincident points.
- Known departure, left as is: a point reflection 2B - A always lies on the circle centred at B through A, and the implementation counts that circle as a favourable incidence, so every point reflection enters the candidate set although the paper only keeps reflections that lie on a further object non-trivially.
- Cost: the reference proposer needs about 0.9 s of CPU per HAGeo-409 problem and 0.25 s per JGEX-231 instance (single-threaded), about a fifth of the evaluator's allowance.
- `baseline/random_aux.py` is the paper's random baseline at the same budget.
