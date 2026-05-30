#!/usr/bin/env python3
"""
Cleaning step of the Practice 5 pipeline.

Reads the interim merged table produced by scripts/build_dataset.py and
applies the steps declared in specs/cleaning_pipeline.json:

  03 strip whitespace + Unicode-normalize text fields
  04 normalize polymer_class to the schema vocabulary
  05 normalize tg_unit
  06 cast tg_value/tg_std to float and drop rows with no tg_value
  07 internally convert to Kelvin and drop rows outside [100, 900] K
  08 drop rows with empty repeat_unit_smiles
  09 normalize measurement_method
  10 drop rows whose source_id is not in specs/source_map.json
  11 exact deduplication
  12 flag cross-source Tg disagreement (>20 K spread for the same SMILES)
  13 schema validation (column set & order)
  14 write data/processed/dataset.csv

Dropped rows are recorded with a reason in data/interim/cleaning_drops.csv.
A short summary is written to data/interim/cleaning_summary.txt.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "specs" / "dataset_schema.json"
SOURCE_MAP_PATH = ROOT / "specs" / "source_map.json"
MERGED_PATH = ROOT / "data" / "interim" / "merged_records.csv"
DATASET_PATH = ROOT / "data" / "processed" / "dataset.csv"
DROP_LOG_PATH = ROOT / "data" / "interim" / "cleaning_drops.csv"
SUMMARY_PATH = ROOT / "data" / "interim" / "cleaning_summary.txt"


# -- Controlled vocabularies (must match specs/dataset_schema.json) ------------

POLYMER_CLASS_VOCAB = {
    "polyimide",
    "polyamide",
    "polyester",
    "polycarbonate",
    "polyolefin",
    "polystyrene",
    "poly(meth)acrylate",
    "polyether",
    "polyurethane",
    "polysiloxane",
    "polysulfone",
    "polybenzimidazole",
    "polyphenylene_oxide",
    "polysaccharide",
    "fluoropolymer",
    "other",
}

# Free-text -> canonical mapping. Keys are lowercase, stripped of surrounding
# whitespace. The mapping below covers:
#   - the Zenodo (LamaLab) dataset labels (plural English, capitalized)
#   - the snake_case labels used by the PDF extraction (Practice 3)
POLYMER_CLASS_MAP = {
    # already-canonical
    "polyimide": "polyimide",
    "polyamide": "polyamide",
    "polyester": "polyester",
    "polycarbonate": "polycarbonate",
    "polyolefin": "polyolefin",
    "polystyrene": "polystyrene",
    "poly(meth)acrylate": "poly(meth)acrylate",
    "polyether": "polyether",
    "polyurethane": "polyurethane",
    "polysiloxane": "polysiloxane",
    "polysulfone": "polysulfone",
    "polybenzimidazole": "polybenzimidazole",
    "polyphenylene_oxide": "polyphenylene_oxide",
    "polysaccharide": "polysaccharide",
    "fluoropolymer": "fluoropolymer",
    "other": "other",
    # Zenodo plural labels
    "polyimides": "polyimide",
    "polyamides": "polyamide",
    "polyesters": "polyester",
    "polycarbonates": "polycarbonate",
    "polyolefins": "polyolefin",
    "polystyrenes": "polystyrene",
    "polyacrylics": "poly(meth)acrylate",
    "polyethers": "polyether",
    "polyurethanes": "polyurethane",
    "polysiloxanes": "polysiloxane",
    "polysulfones": "polysulfone",
    "polysaccharides": "polysaccharide",
    "fluoropolymers": "fluoropolymer",
    "polyoxides": "polyether",
    "polyhalo-olefins": "fluoropolymer",
    "other class": "other",
    "polyanhydrides": "other",
    "polydienes": "other",
    "polyimines": "other",
    "polyketones": "other",
    "polyphenylenes": "other",
    "polyphosphazenes": "other",
    "polysulfides": "other",
    "polyureas": "other",
    "polyvinyls": "other",
}

TG_UNIT_MAP = {
    "c": "C",
    "°c": "C",
    "degc": "C",
    "celsius": "C",
    "k": "K",
    "kelvin": "K",
}

MEASUREMENT_METHOD_VOCAB = {
    "DSC",
    "DMA",
    "TMA",
    "dilatometry",
    "dielectric_spectroscopy",
    "simulation_MD",
    "unknown",
}

MEASUREMENT_METHOD_MAP = {
    "dsc": "DSC",
    "dma": "DMA",
    "tma": "TMA",
    "dilatometry": "dilatometry",
    "dielectric_spectroscopy": "dielectric_spectroscopy",
    "dielectric spectroscopy": "dielectric_spectroscopy",
    "simulation_md": "simulation_MD",
    "molecular dynamics": "simulation_MD",
    "md": "simulation_MD",
    "unknown": "unknown",
    "": "unknown",
}

MISSING_TOKENS = {"", "na", "n/a", "none", "null", "-", "nan"}

TG_MIN_K = 100.0
TG_MAX_K = 900.0
CROSS_SOURCE_THRESHOLD_K = 20.0


# -- Utilities -----------------------------------------------------------------


def load_schema_columns() -> list[str]:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)
    return [field["name"] for field in schema["fields"]]


def load_source_ids() -> set[str]:
    with SOURCE_MAP_PATH.open(encoding="utf-8") as f:
        sm = json.load(f)
    ids: set[str] = set()
    for group in sm.get("source_groups", {}).values():
        for entry in group:
            sid = entry.get("source_id")
            if sid:
                ids.add(sid)
    return ids


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFC", str(value)).strip()
    text = " ".join(text.split())
    if text.lower() in MISSING_TOKENS:
        return ""
    return text


def to_kelvin(value: float, unit: str) -> float | None:
    if unit == "K":
        return float(value)
    if unit == "C":
        return float(value) + 273.15
    return None


def load_interim() -> pd.DataFrame:
    """Load merged_records.csv; if absent, call build_dataset.build()."""
    if MERGED_PATH.is_file():
        return pd.read_csv(MERGED_PATH)

    build_path = ROOT / "scripts" / "build_dataset.py"
    spec = importlib.util.spec_from_file_location("build_dataset", build_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {build_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build()


# -- Cleaning steps ------------------------------------------------------------


def step_03_text_cleanup(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = [
        "polymer_name",
        "repeat_unit_smiles",
        "polymer_class",
        "tg_unit",
        "measurement_method",
        "source_id",
        "source_type",
        "doi",
        "extraction_method",
        "notes",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].map(normalize_text)
    return df


def step_04_normalize_polymer_class(
    df: pd.DataFrame,
) -> pd.DataFrame:
    def _norm(raw: str) -> tuple[str, str | None]:
        key = raw.strip().lower()
        if key in POLYMER_CLASS_MAP:
            return POLYMER_CLASS_MAP[key], None
        return "other", f"unmapped_polymer_class={raw}"

    notes = df["notes"].fillna("").astype(str).tolist()
    new_classes = []
    for i, raw in enumerate(df["polymer_class"].fillna("").astype(str)):
        canonical, note = _norm(raw)
        new_classes.append(canonical)
        if note:
            existing = notes[i]
            sep = " | " if existing else ""
            notes[i] = f"{existing}{sep}{note}"
    df["polymer_class"] = new_classes
    df["notes"] = notes
    return df


def step_05_normalize_tg_unit(
    df: pd.DataFrame, drops: list[dict]
) -> pd.DataFrame:
    keep_mask = []
    new_units = []
    for _, row in df.iterrows():
        raw = str(row["tg_unit"]).strip().lower()
        canonical = TG_UNIT_MAP.get(raw)
        if canonical is None:
            drops.append(
                {
                    "record_id": row.get("record_id", ""),
                    "reason": "tg_unit_unrecognized",
                    "detail": f"tg_unit={row['tg_unit']!r}",
                }
            )
            keep_mask.append(False)
            new_units.append(None)
        else:
            keep_mask.append(True)
            new_units.append(canonical)
    df = df.assign(tg_unit=new_units)
    return df.loc[keep_mask].reset_index(drop=True)


def step_06_validate_tg_value_numeric(
    df: pd.DataFrame, drops: list[dict]
) -> pd.DataFrame:
    parsed: list[float | None] = []
    parsed_std: list[float | None] = []
    keep_mask: list[bool] = []
    for _, row in df.iterrows():
        try:
            v = float(row["tg_value"])
            if pd.isna(v):
                raise ValueError("nan")
        except (TypeError, ValueError):
            drops.append(
                {
                    "record_id": row.get("record_id", ""),
                    "reason": "tg_value_missing",
                    "detail": f"tg_value={row.get('tg_value')!r}",
                }
            )
            keep_mask.append(False)
            parsed.append(None)
            parsed_std.append(None)
            continue
        keep_mask.append(True)
        parsed.append(v)
        try:
            s = float(row["tg_std"])
            if pd.isna(s):
                s = None
        except (TypeError, ValueError):
            s = None
        parsed_std.append(s)
    df = df.assign(tg_value=parsed, tg_std=parsed_std)
    return df.loc[keep_mask].reset_index(drop=True)


def step_07_range_filter(
    df: pd.DataFrame, drops: list[dict]
) -> pd.DataFrame:
    keep_mask = []
    for _, row in df.iterrows():
        tk = to_kelvin(row["tg_value"], row["tg_unit"])
        if tk is None or tk < TG_MIN_K or tk > TG_MAX_K:
            drops.append(
                {
                    "record_id": row.get("record_id", ""),
                    "reason": "tg_out_of_range",
                    "detail": (
                        f"tg_value={row['tg_value']} tg_unit={row['tg_unit']}"
                        f" -> {tk} K"
                    ),
                }
            )
            keep_mask.append(False)
        else:
            keep_mask.append(True)
    return df.loc[keep_mask].reset_index(drop=True)


def step_08_smiles_present(
    df: pd.DataFrame, drops: list[dict]
) -> pd.DataFrame:
    keep_mask = []
    for _, row in df.iterrows():
        smi = str(row["repeat_unit_smiles"]).strip()
        if smi in ("", "nan"):
            drops.append(
                {
                    "record_id": row.get("record_id", ""),
                    "reason": "smiles_missing",
                    "detail": (
                        "repeat_unit_smiles empty; structure not resolved"
                        " in Practice 3 (polyimide auto-assembly skipped)"
                    ),
                }
            )
            keep_mask.append(False)
        else:
            keep_mask.append(True)
    return df.loc[keep_mask].reset_index(drop=True)


def step_09_normalize_measurement_method(df: pd.DataFrame) -> pd.DataFrame:
    new_methods = []
    notes = df["notes"].fillna("").astype(str).tolist()
    for i, raw in enumerate(df["measurement_method"].fillna("").astype(str)):
        key = raw.strip().lower()
        canonical = MEASUREMENT_METHOD_MAP.get(key)
        if canonical is None:
            canonical = "unknown"
            sep = " | " if notes[i] else ""
            notes[i] = f"{notes[i]}{sep}unmapped_method={raw}"
        new_methods.append(canonical)
    df["measurement_method"] = new_methods
    df["notes"] = notes
    return df


def step_10_check_source_id(
    df: pd.DataFrame, drops: list[dict]
) -> pd.DataFrame:
    known = load_source_ids()
    keep_mask = []
    for _, row in df.iterrows():
        sid = str(row["source_id"]).strip()
        if sid in known:
            keep_mask.append(True)
        else:
            drops.append(
                {
                    "record_id": row.get("record_id", ""),
                    "reason": "unknown_source_id",
                    "detail": f"source_id={sid!r}",
                }
            )
            keep_mask.append(False)
    return df.loc[keep_mask].reset_index(drop=True)


def step_11_deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)


def step_12_flag_cross_source_disagreement(df: pd.DataFrame) -> pd.DataFrame:
    # group by SMILES; compute spread in K; if > threshold flag every row
    df = df.copy()
    tg_k = [
        to_kelvin(v, u) for v, u in zip(df["tg_value"], df["tg_unit"])
    ]
    df["_tg_k"] = tg_k
    flagged_indices: set[int] = set()
    for _, group in df.groupby("repeat_unit_smiles"):
        if len(group) < 2:
            continue
        if (group["_tg_k"].max() - group["_tg_k"].min()) > CROSS_SOURCE_THRESHOLD_K:
            flagged_indices.update(group.index.tolist())
    notes = df["notes"].fillna("").astype(str).tolist()
    for idx in flagged_indices:
        sep = " | " if notes[idx] else ""
        if "cross_source_disagreement" not in notes[idx]:
            notes[idx] = f"{notes[idx]}{sep}cross_source_disagreement"
    df["notes"] = notes
    return df.drop(columns=["_tg_k"])


def step_13_validate_schema_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = load_schema_columns()
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    df = df[expected]
    return df


# -- Orchestration -------------------------------------------------------------


def run(verbose: bool = True) -> pd.DataFrame:
    drops: list[dict] = []
    df = load_interim()
    started = len(df)
    if verbose:
        print(f"[clean] start: {started} rows")

    df = step_03_text_cleanup(df)
    df = step_04_normalize_polymer_class(df)
    df = step_05_normalize_tg_unit(df, drops)
    if verbose:
        print(f"[clean] after step 05 (tg_unit): {len(df)} rows")
    df = step_06_validate_tg_value_numeric(df, drops)
    if verbose:
        print(f"[clean] after step 06 (tg_value): {len(df)} rows")
    df = step_07_range_filter(df, drops)
    if verbose:
        print(f"[clean] after step 07 (range): {len(df)} rows")
    df = step_08_smiles_present(df, drops)
    if verbose:
        print(f"[clean] after step 08 (smiles): {len(df)} rows")
    df = step_09_normalize_measurement_method(df)
    df = step_10_check_source_id(df, drops)
    if verbose:
        print(f"[clean] after step 10 (source_id): {len(df)} rows")
    df = step_11_deduplicate(df)
    if verbose:
        print(f"[clean] after step 11 (dedupe): {len(df)} rows")
    df = step_12_flag_cross_source_disagreement(df)
    df = step_13_validate_schema_columns(df)

    # write drop log
    DROP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(drops).to_csv(DROP_LOG_PATH, index=False)

    # summary
    n_flagged = int(
        df["notes"]
        .fillna("")
        .astype(str)
        .str.contains("cross_source_disagreement")
        .sum()
    )
    by_reason: dict[str, int] = {}
    for d in drops:
        by_reason[d["reason"]] = by_reason.get(d["reason"], 0) + 1
    lines = [
        f"start_rows: {started}",
        f"end_rows: {len(df)}",
        f"dropped_total: {len(drops)}",
    ]
    for reason, count in sorted(by_reason.items()):
        lines.append(f"dropped_{reason}: {count}")
    lines.append(f"flagged_cross_source_disagreement: {n_flagged}")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if verbose:
        print("[clean] summary:")
        for line in lines:
            print(f"  {line}")

    return df


def main() -> int:
    df = run(verbose=True)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH, index=False)
    print(
        f"clean_dataset: wrote {len(df)} rows "
        f"to {DATASET_PATH.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
