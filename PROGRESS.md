# Progress

## What Works

- Paper analysis is complete for the central claim: HAGeo uses CPU-only DDAR plus heuristic auxiliary constructions rather than neural inference.
- Public benchmark data from `HAGeo-IMO/HAGeo-409` is downloaded into `data/downloads/` and converted into tracked JSONL slices by `data/prepare_benchmarks.py`.
- The DDAR-only baseline runs through `scripts/baseline.sh`.
- The HAGeo-style method runner runs through `scripts/method.sh`: initial DDAR, then heuristic auxiliary candidates, then rerun DDAR.
- `scripts/evaluate.sh` reads output JSONL artifacts and writes `scoring/scores.json` without importing from `method/`.

## Results

- Local smoke result on `auxiliary_core`: DDAR baseline solved 0/1, HAGeo-style runner solved 1/1 using one auxiliary construction.
- `python validate.py --compare` passes. The local result supports `method_runs`; a CPU scheduler job is being submitted to verify the packaged environment before claiming `core_claim`.

## Remaining

- Confirm the same core run on a compute node.
- After core verification, expand to `hageo409_small` and increase attempts/rounds if CPU budget permits.
- A fuller reproduction would require either the official HAGeo solver release or a larger in-house implementation of the paper's optimized DDAR and all heuristic categories at full K.

## Issues

- The upstream HAGeo GitHub repository currently does not include runnable source code; its README states the full code is pending release.
- The paper markdown listed `https://huggingface.co/datasets/HAGeo-409`, but the verified public dataset slug is `HAGeo-IMO/HAGeo-409`.
- The login node has a very small root filesystem. A local SciPy install failed due to space, so the vendored AlphaGeometry AR traceback dependency on SciPy was made optional. Solving still uses the DDAR algebra tables; only traceback minimization falls back.
- AlphaGeometry forced the `TkAgg` plotting backend, which fails headlessly; the vendored numerical module now uses `Agg`.

## Deviations from Paper

- The paper's official HAGeo solver code is not released in the public GitHub repository as of this run. To preserve the computation pattern, this reproduction vendors the public AlphaGeometry DDAR engine and adds a CPU-only HAGeo-style heuristic auxiliary construction search wrapper.
- The full paper setting uses K=4096 on IMO-30 and K=2048/8192 on HAGeo-409 with N=6 construction rounds. The current runnable job scales this to a one-problem auxiliary core with smaller K for verification.
- The paper reports full IMO-30 and HAGeo-409 results. Current scoring includes a minimal auxiliary core experiment and a prepared small HAGeo-409 slice for later expansion.
