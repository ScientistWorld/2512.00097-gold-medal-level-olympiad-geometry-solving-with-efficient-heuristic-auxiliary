#!/usr/bin/env python3
"""Prepare small portable benchmark files for HAGeo reproduction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


ORTHOCENTER = {
    "problem_id": "orthocenter_auxiliary",
    "source": "alphageometry_examples",
    "difficulty": 2.0,
    "statement": (
        "a b c = triangle; "
        "d = on_tline d b a c, on_tline d c a b "
        "? perp a d b c"
    ),
    "note": "DDAR alone fails; adding the intersection of AC and BD solves it.",
}


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def load_hageo409(path: Path, limit: int, sort_by: str) -> list[dict]:
    table = pq.read_table(path)
    columns = table.to_pydict()
    rows = []
    for idx in range(table.num_rows):
        statement = columns["AlphaGeometry"][idx]
        if not statement or " ? " not in statement:
            continue
        rows.append(
            {
                "problem_id": columns["Problem_ID"][idx],
                "source": "HAGeo-409",
                "difficulty": float(columns["Difficulty_Score"][idx]),
                "statement": statement,
                "natural_language": columns["Natural_Language"][idx],
            }
        )
    if sort_by == "difficulty":
        rows.sort(key=lambda row: (row["difficulty"], row["problem_id"]))
    elif sort_by != "original":
        raise ValueError(f"unsupported --hageo-sort value: {sort_by}")
    return rows[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parquet",
        default="data/downloads/HAGeo-409/HAGeo-409.parquet",
        type=Path,
    )
    parser.add_argument("--out-dir", default="data/benchmarks", type=Path)
    parser.add_argument("--hageo-limit", default=12, type=int)
    parser.add_argument(
        "--hageo-sort",
        choices=["original", "difficulty"],
        default="original",
        help="Order used before slicing the portable HAGeo-409 subset.",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl([ORTHOCENTER], args.out_dir / "auxiliary_core.jsonl")
    if args.parquet.exists():
        write_jsonl(
            load_hageo409(args.parquet, args.hageo_limit, args.hageo_sort),
            args.out_dir / "hageo409_small.jsonl",
        )


if __name__ == "__main__":
    main()
