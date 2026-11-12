#!/bin/bash
# Download the public artifacts this environment was built from.
#
# Idempotent: skips files that already exist.  Needs internet (login node).
# Estimated total download size: <1 MB.  Disk after download: <1 MB.
#
# - HAGeo-409 (public benchmark, HuggingFace HAGeo-IMO/HAGeo-409) and
#   JGEX-231 (AlphaGeometry repository): sources of the committed train
#   problems (data/benchmarks/*.jsonl) and held-out problems (eval/test/);
#   only needed to rebuild them with eval/test/build_split.py.
# - The AlphaGeometry DD+AR engine is vendored (Apache-2.0) under
#   method/alphageometry/ and eval/{train,test}/ag/; its upstream source is
#   https://github.com/google-deepmind/alphageometry (cloned below only if
#   method/alphageometry is missing).
set -e
cd "$(dirname "$0")/.."

mkdir -p data/downloads/HAGeo-409
if [ ! -s data/downloads/HAGeo-409/HAGeo-409.parquet ]; then
  curl -L --fail \
    https://huggingface.co/datasets/HAGeo-IMO/HAGeo-409/resolve/main/HAGeo-409.parquet \
    -o data/downloads/HAGeo-409/HAGeo-409.parquet
fi
if [ ! -s data/downloads/HAGeo-409/README.md ]; then
  curl -L --fail \
    https://huggingface.co/datasets/HAGeo-IMO/HAGeo-409/raw/main/README.md \
    -o data/downloads/HAGeo-409/README.md
fi
if [ ! -s data/downloads/jgex_ag_231.txt ]; then
  curl -L --fail \
    https://raw.githubusercontent.com/google-deepmind/alphageometry/main/jgex_ag_231.txt \
    -o data/downloads/jgex_ag_231.txt
fi
if [ ! -s method/alphageometry/ddar.py ]; then
  git clone --depth 1 https://github.com/google-deepmind/alphageometry method/alphageometry
fi
