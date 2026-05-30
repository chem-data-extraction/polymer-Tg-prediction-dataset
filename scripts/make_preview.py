#!/usr/bin/env python3
"""
Produce a 1000-row preview of data/processed/dataset.csv so GitHub can render
it as a searchable table. The original full dataset is left untouched.

The preview is stratified, not random, so the viewer sees:
  * every row from the PDF source (Practice 3)
  * every row flagged with cross_source_disagreement
  * a random sample from Zenodo to fill the remaining slots up to 1000

Output: data/processed/dataset_preview.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data" / "processed" / "dataset.csv"
PREVIEW = ROOT / "data" / "processed" / "dataset_preview.csv"

PREVIEW_ROWS = 1000
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(FULL)
    print(f"Full dataset:   {len(df):>5d} rows")

    # 1. always keep all non-dataset (= PDF) rows
    pdf_rows = df[df["source_type"] != "dataset"]
    print(f"  forced PDF:   {len(pdf_rows):>5d} rows")

    # 2. always keep every row flagged with cross_source_disagreement
    flagged = df[
        df["notes"].fillna("").str.contains("cross_source_disagreement")
    ]
    print(f"  forced flag:  {len(flagged):>5d} rows")

    forced = pd.concat([pdf_rows, flagged]).drop_duplicates(subset=["record_id"])
    print(f"  forced total: {len(forced):>5d} rows (after dedupe)")

    # 3. fill the rest from Zenodo (random, reproducible)
    remaining = df[~df["record_id"].isin(forced["record_id"])]
    n_to_sample = max(0, PREVIEW_ROWS - len(forced))
    n_to_sample = min(n_to_sample, len(remaining))
    sampled = remaining.sample(n=n_to_sample, random_state=RANDOM_STATE)
    print(f"  sampled:      {len(sampled):>5d} rows")

    preview = pd.concat([forced, sampled])
    # stable, readable order: PDF first, then Zenodo by record_id
    preview = preview.sort_values(
        ["source_type", "record_id"], ascending=[True, True]
    )
    preview.to_csv(PREVIEW, index=False)
    print(
        f"\nWrote {len(preview)} rows × {len(preview.columns)} cols to "
        f"{PREVIEW.relative_to(ROOT)} "
        f"({PREVIEW.stat().st_size / 1024:.1f} KB)"
    )


if __name__ == "__main__":
    main()
