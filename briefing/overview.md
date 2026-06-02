# Overview

- **Paper ID:** 2512.00097
- **Title:** Gold-Medal-Level Olympiad Geometry Solving with Efficient Heuristic Auxiliary Constructions
- **Domain:** Automated Theorem Proving / Euclidean Geometry
- **TL;DR:** The paper shows that a CPU-only geometry theorem prover can solve Olympiad-level geometry problems at gold-medal level by combining a fast deductive-algebraic prover with targeted auxiliary constructions.

## Short Summary

This paper studies automated theorem proving for Euclidean geometry, especially International Mathematical Olympiad-level problems where auxiliary constructions are often essential. It proposes HAGeo, a non-neural system that repeatedly augments a formal geometry problem with promising auxiliary constructions and reruns a deductive-algebraic proof engine. The paper also introduces HAGeo-409, a 409-problem benchmark with human difficulty ratings intended to be larger and more discriminating than IMO-30. Reported results show HAGeo outperforming AlphaGeometry and random auxiliary construction baselines while running entirely on CPUs.

## Key Results

- HAGeo solves 28 of 30 problems on IMO-30, compared with 24 for the paper's corrected AlphaGeometry count, 25 for a random auxiliary-construction baseline, and 15 for DDAR alone.
- On HAGeo-409, HAGeo solves 263/409 problems at 2,048 attempts and 287/409 at 8,192 attempts, outperforming both AlphaGeometry and random auxiliary construction across difficulty bands.
- The paper reports an optimized DDAR engine with roughly 20x faster average inference than AlphaGeometry's DDAR implementation under the compared CPU setting.
