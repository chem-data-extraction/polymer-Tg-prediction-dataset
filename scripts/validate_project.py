#!/usr/bin/env python3
"""
Validate the repository against specs/validation_rules.json.

Returns exit code 0 if no errors (warnings allowed), 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "project.json",
    "specs/dataset_schema.json",
    "specs/source_map.json",
    "specs/pdf_extraction_manifest.json",
    "specs/web_extraction_manifest.json",
    "specs/cleaning_pipeline.json",
    "specs/validation_rules.json",
    "data/extracted/all_papers_table3_filled.csv",
    "data/extracted/ds_zenodo_lamalab_tg.csv",
    "data/processed/dataset.csv",
    "scripts/build_dataset.py",
    "scripts/clean_dataset.py",
    "scripts/validate_project.py",
    "reports/practice_01_record_and_schema.md",
    "reports/practice_02_source_map.md",
    "reports/practice_03_pdf_extraction.md",
    "reports/practice_04_web_extraction.md",
    "reports/practice_05_cleaning_publication.md",
    "reports/final_report.md",
    "dataset_card.md",
    "LICENSE",
    "CITATION.cff",
    "requirements.txt",
]


ALLOWED_TG_UNITS = {"C", "K"}

ALLOWED_POLYMER_CLASSES = {
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

ALLOWED_METHODS = {
    "DSC",
    "DMA",
    "TMA",
    "dilatometry",
    "dielectric_spectroscopy",
    "simulation_MD",
    "unknown",
}

ALLOWED_SOURCE_TYPES = {
    "paper",
    "supplementary",
    "dataset",
    "aggregator",
    "database",
    "github_repository",
}

ALLOWED_EXTRACTION_METHODS = {
    "manual_pdf",
    "pdf_table_extraction",
    "web_scraping",
    "api_query",
    "dataset_download",
    "manual_aggregator_lookup",
}

TG_MIN_K = 100.0
TG_MAX_K = 900.0


# -- helpers -------------------------------------------------------------------


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def schema_field_names(schema: dict) -> list[str]:
    return [field["name"] for field in schema["fields"]]


def source_ids_from_map(source_map: dict) -> set[str]:
    ids: set[str] = set()
    for group in source_map.get("source_groups", {}).values():
        for entry in group:
            sid = entry.get("source_id")
            if sid:
                ids.add(sid)
    return ids


def to_kelvin(value: float, unit: str) -> float | None:
    if unit == "K":
        return float(value)
    if unit == "C":
        return float(value) + 273.15
    return None


def load_dataset(root: Path = ROOT) -> pd.DataFrame:
    return pd.read_csv(root / "data" / "processed" / "dataset.csv")


# -- individual checks ---------------------------------------------------------


def check_required_files(root: Path = ROOT) -> list[str]:
    return [
        f"Missing required file: {rel}"
        for rel in REQUIRED_FILES
        if not (root / rel).is_file()
    ]


def check_json_parseable(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    for path in (root / "specs").glob("*.json"):
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            issues.append(f"Invalid JSON: {path.relative_to(root)} ({exc})")
    if (root / "project.json").is_file():
        try:
            load_json(root / "project.json")
        except json.JSONDecodeError as exc:
            issues.append(f"Invalid JSON: project.json ({exc})")
    return issues


def check_dataset_columns(df: pd.DataFrame, schema: dict) -> list[str]:
    expected = schema_field_names(schema)
    actual = list(df.columns)
    if actual != expected:
        return [
            "Dataset columns do not match schema.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}"
        ]
    return []


def check_record_id(df: pd.DataFrame) -> list[str]:
    issues = []
    s = df["record_id"].astype(str).str.strip()
    if (s == "").any() or df["record_id"].isna().any():
        issues.append("record_id contains null or empty values")
    if df["record_id"].duplicated().any():
        dupes = df.loc[df["record_id"].duplicated(), "record_id"].tolist()[:10]
        issues.append(f"Duplicate record_id values (first 10): {dupes}")
    return issues


def check_source_id(
    df: pd.DataFrame, source_map: dict
) -> list[str]:
    valid = source_ids_from_map(source_map)
    issues = []
    s = df["source_id"].astype(str).str.strip()
    if (s == "").any():
        issues.append("source_id contains empty values")
    unknown = sorted(set(s) - valid)
    if unknown:
        issues.append(f"source_id not in source_map.json: {unknown}")
    return issues


def check_tg_value(df: pd.DataFrame) -> list[str]:
    issues = []
    not_numeric: list[int] = []
    out_of_range: list[tuple[int, float, str, float]] = []
    for idx, row in df.iterrows():
        try:
            v = float(row["tg_value"])
        except (TypeError, ValueError):
            not_numeric.append(idx)
            continue
        u = str(row["tg_unit"])
        tk = to_kelvin(v, u)
        if tk is None or tk < TG_MIN_K or tk > TG_MAX_K:
            out_of_range.append((idx, v, u, tk if tk is not None else float("nan")))
    if not_numeric:
        issues.append(
            f"tg_value not numeric in {len(not_numeric)} rows "
            f"(first: {not_numeric[:5]})"
        )
    if out_of_range:
        sample = out_of_range[:5]
        issues.append(
            f"tg_value out of range in {len(out_of_range)} rows "
            f"(first: {sample})"
        )
    return issues


def check_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed: set[str],
) -> list[str]:
    if column not in df.columns:
        return [f"Column missing: {column}"]
    bad = sorted(set(df[column].dropna().astype(str)) - allowed)
    if bad:
        return [f"{column} has values outside vocabulary: {bad}"]
    return []


def check_smiles_present(df: pd.DataFrame) -> list[str]:
    s = df["repeat_unit_smiles"].astype(str).str.strip()
    n_empty = int(((s == "") | (s == "nan")).sum())
    if n_empty:
        return [f"repeat_unit_smiles empty in {n_empty} rows"]
    return []


# -- top-level validate --------------------------------------------------------


def validate(root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_required_files(root))
    errors.extend(check_json_parseable(root))

    dataset_path = root / "data" / "processed" / "dataset.csv"
    if not dataset_path.is_file():
        return errors, warnings

    schema = load_json(root / "specs" / "dataset_schema.json")
    source_map = load_json(root / "specs" / "source_map.json")
    df = load_dataset(root)

    errors.extend(check_dataset_columns(df, schema))
    errors.extend(check_record_id(df))
    errors.extend(check_source_id(df, source_map))
    errors.extend(check_tg_value(df))
    errors.extend(check_allowed_values(df, "tg_unit", ALLOWED_TG_UNITS))
    errors.extend(check_allowed_values(df, "polymer_class", ALLOWED_POLYMER_CLASSES))
    errors.extend(check_allowed_values(df, "measurement_method", ALLOWED_METHODS))
    errors.extend(check_allowed_values(df, "source_type", ALLOWED_SOURCE_TYPES))
    errors.extend(check_allowed_values(df, "extraction_method", ALLOWED_EXTRACTION_METHODS))
    errors.extend(check_smiles_present(df))

    # warnings
    if len(df) < 10:
        warnings.append(f"Dataset has only {len(df)} rows (<10).")
    if df["source_type"].nunique() < 2:
        warnings.append(
            "Dataset uses only one source_type; "
            "PDF + web integration is not visible."
        )

    return errors, warnings


def main() -> int:
    errors, warnings = validate()
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"\nValidation failed with {len(errors)} error(s).")
        return 1
    print(f"Validation passed. ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
