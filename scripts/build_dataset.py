#!/usr/bin/env python3
"""
Build step of the Practice 5 pipeline.

Reads the real Practice 3 and Practice 4 extraction outputs:
    data/extracted/all_papers_table3_filled.csv   (PDF, 15 records)
    data/extracted/ds_zenodo_lamalab_tg.csv       (web/dataset, ~7000 records)

Aligns each table to the schema columns declared in specs/dataset_schema.json,
concatenates the two, and writes the merged interim table to
    data/interim/merged_records.csv.

This script is intentionally separate from clean_dataset.py: building (= column
alignment + concatenation) is independent of cleaning (= value normalization,
range checks, deduplication, conflict flagging).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PDF_CSV = ROOT / "data" / "extracted" / "all_papers_table3_filled.csv"
WEB_CSV = ROOT / "data" / "extracted" / "ds_zenodo_lamalab_tg.csv"
SCHEMA_PATH = ROOT / "specs" / "dataset_schema.json"
MERGED_PATH = ROOT / "data" / "interim" / "merged_records.csv"


def load_schema_columns() -> list[str]:
    """Return field names declared in specs/dataset_schema.json, in order."""
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)
    return [field["name"] for field in schema["fields"]]


def align_to_schema(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Keep only schema columns, in the right order; add any missing as empty."""
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    return out[columns]


def build() -> pd.DataFrame:
    """Read the two extraction CSVs, align to schema, concatenate, return."""
    if not PDF_CSV.is_file():
        raise FileNotFoundError(
            f"Expected Practice 3 output at {PDF_CSV.relative_to(ROOT)}"
        )
    if not WEB_CSV.is_file():
        raise FileNotFoundError(
            f"Expected Practice 4 output at {WEB_CSV.relative_to(ROOT)}"
        )

    columns = load_schema_columns()

    pdf_df = pd.read_csv(PDF_CSV)
    web_df = pd.read_csv(WEB_CSV)

    pdf_aligned = align_to_schema(pdf_df, columns)
    web_aligned = align_to_schema(web_df, columns)

    merged = pd.concat([pdf_aligned, web_aligned], ignore_index=True)
    return merged


def main() -> None:
    MERGED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = build()
    df.to_csv(MERGED_PATH, index=False)
    print(
        f"build_dataset: wrote {len(df)} rows "
        f"to {MERGED_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
