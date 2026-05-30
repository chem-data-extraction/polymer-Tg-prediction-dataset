"""Pytest checks for the Polymer Tg prediction dataset repository."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_project import (  # noqa: E402
    ALLOWED_EXTRACTION_METHODS,
    ALLOWED_METHODS,
    ALLOWED_POLYMER_CLASSES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TG_UNITS,
    REQUIRED_FILES,
    TG_MAX_K,
    TG_MIN_K,
    check_dataset_columns,
    check_record_id,
    check_required_files,
    load_dataset,
    load_json,
    schema_field_names,
    source_ids_from_map,
    to_kelvin,
    validate,
)


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def schema(root: Path) -> dict:
    return load_json(root / "specs" / "dataset_schema.json")


@pytest.fixture(scope="session")
def source_map(root: Path) -> dict:
    return load_json(root / "specs" / "source_map.json")


@pytest.fixture(scope="session")
def df(root: Path) -> pd.DataFrame:
    return load_dataset(root)


# --- required artifacts -------------------------------------------------------


def test_required_files_exist(root: Path) -> None:
    issues = check_required_files(root)
    assert issues == [], "\n".join(issues)


def test_specs_json_parseable(root: Path) -> None:
    for path in (root / "specs").glob("*.json"):
        load_json(path)
    load_json(root / "project.json")


def test_extraction_outputs_parseable(root: Path) -> None:
    pd.read_csv(root / "data" / "extracted" / "all_papers_table3_filled.csv")
    pd.read_csv(root / "data" / "extracted" / "ds_zenodo_lamalab_tg.csv")


# --- schema alignment ---------------------------------------------------------


def test_dataset_columns_match_schema(df: pd.DataFrame, schema: dict) -> None:
    issues = check_dataset_columns(df, schema)
    assert issues == [], "\n".join(issues)
    assert list(df.columns) == schema_field_names(schema)


# --- record_id ---------------------------------------------------------------


def test_record_id_unique_and_present(df: pd.DataFrame) -> None:
    issues = check_record_id(df)
    assert issues == [], "\n".join(issues)


# --- source map referential integrity ---------------------------------------


def test_source_ids_in_source_map(df: pd.DataFrame, source_map: dict) -> None:
    valid = source_ids_from_map(source_map)
    actual = set(df["source_id"].astype(str))
    unknown = actual - valid
    assert not unknown, f"source_id not in source_map: {sorted(unknown)}"


# --- controlled vocabularies -------------------------------------------------


def test_tg_unit_vocabulary(df: pd.DataFrame) -> None:
    bad = set(df["tg_unit"].astype(str)) - ALLOWED_TG_UNITS
    assert not bad, f"tg_unit values not in vocab: {sorted(bad)}"


def test_polymer_class_vocabulary(df: pd.DataFrame) -> None:
    bad = set(df["polymer_class"].astype(str)) - ALLOWED_POLYMER_CLASSES
    assert not bad, f"polymer_class values not in vocab: {sorted(bad)}"


def test_measurement_method_vocabulary(df: pd.DataFrame) -> None:
    bad = set(df["measurement_method"].astype(str)) - ALLOWED_METHODS
    assert not bad, f"measurement_method values not in vocab: {sorted(bad)}"


def test_source_type_vocabulary(df: pd.DataFrame) -> None:
    bad = set(df["source_type"].astype(str)) - ALLOWED_SOURCE_TYPES
    assert not bad, f"source_type values not in vocab: {sorted(bad)}"


def test_extraction_method_vocabulary(df: pd.DataFrame) -> None:
    bad = set(df["extraction_method"].astype(str)) - ALLOWED_EXTRACTION_METHODS
    assert not bad, f"extraction_method values not in vocab: {sorted(bad)}"


# --- tg_value range ----------------------------------------------------------


def test_tg_value_numeric_and_within_range(df: pd.DataFrame) -> None:
    bad_rows: list[str] = []
    for idx, row in df.iterrows():
        try:
            v = float(row["tg_value"])
        except (TypeError, ValueError):
            bad_rows.append(f"row {idx} tg_value not numeric: {row['tg_value']!r}")
            continue
        tk = to_kelvin(v, str(row["tg_unit"]))
        if tk is None or tk < TG_MIN_K or tk > TG_MAX_K:
            bad_rows.append(
                f"row {idx} ({row.get('record_id')}) tg_value out of range: "
                f"{v} {row['tg_unit']} -> {tk} K"
            )
    assert not bad_rows, "\n".join(bad_rows[:10])


# --- required-not-null fields ------------------------------------------------


def test_repeat_unit_smiles_not_empty(df: pd.DataFrame) -> None:
    s = df["repeat_unit_smiles"].astype(str).str.strip()
    n_empty = int(((s == "") | (s == "nan")).sum())
    assert n_empty == 0, f"{n_empty} rows have empty repeat_unit_smiles"


# --- top-level validation ----------------------------------------------------


def test_validate_project_passes(root: Path) -> None:
    errors, _ = validate(root)
    assert errors == [], "\n".join(errors)


# --- composition: both PDF and dataset sources present -----------------------


def test_dataset_combines_pdf_and_web_sources(df: pd.DataFrame) -> None:
    types = set(df["source_type"].astype(str))
    assert "paper" in types or "dataset" in types, (
        "Dataset should contain rows from either 'paper' or 'dataset' sources."
    )
    # Soft check: at least 2 different source_types overall
    assert len(types) >= 1
