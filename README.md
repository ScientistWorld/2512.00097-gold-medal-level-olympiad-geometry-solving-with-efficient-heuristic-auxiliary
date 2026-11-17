# Gold-Medal-Level Olympiad Geometry Solving with Efficient Heuristic Auxiliary Constructions

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

<!-- hardening-note -->
> [!NOTE]
> **Red-teamed and hardened.** A red team tried to score on this environment's hidden test without doing better research, and the environment was then fixed against the shortcuts that worked: see [`REDTEAM.md`](REDTEAM.md) and [`HARDENING.md`](HARDENING.md). The environment as it was before is kept as branch [`pre-hardening`](../../tree/pre-hardening).

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2512.00097"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2512.00097-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2512.00097](https://arxiv.org/abs/2512.00097) |
|:---|:---|
| **Domain** | Automated Theorem Proving / Euclidean Geometry |
| **TL;DR** | The paper shows that a CPU-only geometry theorem prover can solve Olympiad-level geometry problems at gold-medal level by combining a fast deductive-algebraic prover with targeted auxiliary constructions. |

## Summary

This paper studies automated theorem proving for Euclidean geometry, especially International Mathematical Olympiad-level problems where auxiliary constructions are often essential. It proposes HAGeo, a non-neural system that repeatedly augments a formal geometry problem with promising auxiliary constructions and reruns a deductive-algebraic proof engine. The paper also introduces HAGeo-409, a 409-problem benchmark with human difficulty ratings intended to be larger and more discriminating than IMO-30. Reported results show HAGeo outperforming AlphaGeometry and random auxiliary construction baselines while running entirely on CPUs.

## Problem

Can an automated theorem prover solve challenging Olympiad-level Euclidean geometry problems reliably and efficiently under a fixed formal problem representation and bounded computational budget? The central gap is that existing benchmarks are small or comparatively easy, and prior high-performing systems often require expensive neural inference or very large search budgets.

## The paper's method

The paper introduces HAGeo, a CPU-only automated Euclidean geometry theorem prover that replaces neural auxiliary-construction proposal with a heuristic construction strategy guided by numerical geometry checks. It pairs this strategy with an optimized deductive database and algebraic reasoning engine, then evaluates the system on both IMO-30 and a new 409-problem benchmark with difficulty labels.

## Key results of the paper

- HAGeo solves 28 of 30 problems on IMO-30, compared with 24 for the paper's corrected AlphaGeometry count, 25 for a random auxiliary-construction baseline, and 15 for DDAR alone.
- On HAGeo-409, HAGeo solves 263/409 problems at 2,048 attempts and 287/409 at 8,192 attempts, outperforming both AlphaGeometry and random auxiliary construction across difficulty bands.
- The paper reports an optimized DDAR engine with roughly 20x faster average inference than AlphaGeometry's DDAR implementation under the compared CPU setting.

## Run it

```bash
pip install sciworld
sw research 2512.00097 --mode innovate --agent claude-code
sw evaluate 2512.00097
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

