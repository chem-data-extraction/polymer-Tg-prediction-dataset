#!/usr/bin/env python3
"""
Practice 3 — PDF extraction script for Polymer Tg dataset.

Extracts Tg records from three open-access MDPI papers:
  - Chen et al. 2021 (DOI: 10.3390/polym13111898) — Table 1, SMILES + Tg (K)
  - Wang et al. 2023 (DOI: 10.3390/polym15173549) — Table 3, DMA, limit values
  - Polymers 2024, 16, 3188  (DOI: 10.3390/polym16223188) — Table 2, DSC

Two extraction methods per paper:
  1. pdfplumber word-coordinate table reconstruction
  2. PyMuPDF + regex for inline Tg values

Usage:
    python scripts/extract_pdf.py          # in repo root
    !python scripts/extract_pdf.py         # in Colab after cd to repo root

Requirements:
    pip install pymupdf pdfplumber pandas
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

import fitz          # PyMuPDF
import pandas as pd
import pdfplumber

ROOT     = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "specs/pdf_extraction_manifest.json"
OUT_CSV  = ROOT / "data/extracted/pdf_extracted_records.csv"
LOG_PATH = ROOT / "data/extracted/extraction_log.jsonl"

# ── Logging ───────────────────────────────────────────────────────────────────
def log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry["step"] = "pdf_extraction"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def ctx(text: str, s: int, e: int, n: int = 80) -> str:
    """Context window around a regex match."""
    return text[max(0, s-n): min(len(text), e+n)].replace("\n", " ")

def page_texts(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    texts = [page.get_text() for page in doc]
    doc.close()
    return texts

# ── Word-coordinate table reconstruction ──────────────────────────────────────
def reconstruct_rows(pdf_path: Path, page_idx: int, y_min: float) -> list[list]:
    """
    Extract words below y_min on page_idx, group into rows by y-coordinate.
    Returns list of rows, each row is a list of pdfplumber word dicts.
    """
    with pdfplumber.open(pdf_path) as pdf:
        words = pdf.pages[page_idx].extract_words()
    tw = [w for w in words if w["top"] >= y_min]
    tw.sort(key=lambda w: round(w["top"] / 8))
    rows = []
    for _, grp in groupby(tw, key=lambda w: round(w["top"] / 8)):
        rows.append(sorted(grp, key=lambda w: w["x0"]))
    return rows

def assign_cols(row: list, breaks: tuple) -> list[str]:
    """Assign words to columns by x-position boundaries."""
    buckets: list[list] = [[] for _ in range(len(breaks) + 1)]
    for w in row:
        placed = False
        for i, b in enumerate(breaks):
            if w["x0"] < b:
                buckets[i].append(w["text"])
                placed = True
                break
        if not placed:
            buckets[-1].append(w["text"])
    return [" ".join(b).strip() for b in buckets]

# ── Regex patterns ─────────────────────────────────────────────────────────────
# Inline: "polystyrene Tg = 373 K"
PAT_INLINE_K = re.compile(
    r"(?P<polymer>[\w()\-]+(?:\s+\([^)]{1,20}\))?)\s+"
    r"T[_\s]?g\s*=\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*K\b"
)
# Inline: "PI-ODA at Tg = 398 °C"
PAT_INLINE_C = re.compile(
    r"(?P<polymer>[\w()\-]+(?:\s+\([^)]{1,20}\))?)\s+"
    r"(?:at\s+)?T[_\s]?g\s*=\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*°?\s*C\b"
)
# Limit: "Tg > 450 °C"
PAT_LIMIT = re.compile(
    r"T[_\s]?g\s*(?P<rel>[><=]+)\s*(?P<value>\d{2,3}(?:\.\d+)?)\s*°?\s*(?P<unit>[CK])\b"
)
# Conditions
PAT_HEATING = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*°C/min")
PAT_ATMO    = re.compile(r"\b(?P<value>N2|nitrogen|N₂)\b", re.I)


def extract_inline(texts: list[str], source_id: str, doi: str) -> list[dict]:
    """Extract Tg values from running text using regex."""
    records = []
    for page_num, text in enumerate(texts, start=1):
        for m in PAT_INLINE_K.finditer(text):
            records.append({
                "polymer_name": m.group("polymer").strip(),
                "tg_value": float(m.group("value")),
                "tg_unit": "K",
                "tg_relation": None, "tg_limit_value": None,
                "source_id": source_id, "doi": doi,
                "extraction_method": "pdf_text_regex",
                "source_page": page_num,
                "evidence_text": ctx(text, m.start(), m.end()),
            })
        for m in PAT_INLINE_C.finditer(text):
            records.append({
                "polymer_name": m.group("polymer").strip(),
                "tg_value": float(m.group("value")),
                "tg_unit": "C",
                "tg_relation": None, "tg_limit_value": None,
                "source_id": source_id, "doi": doi,
                "extraction_method": "pdf_text_regex",
                "source_page": page_num,
                "evidence_text": ctx(text, m.start(), m.end()),
            })
        for m in PAT_LIMIT.finditer(text):
            records.append({
                "polymer_name": None,
                "tg_value": None,
                "tg_unit": m.group("unit"),
                "tg_relation": m.group("rel"),
                "tg_limit_value": float(m.group("value")),
                "source_id": source_id, "doi": doi,
                "extraction_method": "pdf_text_regex",
                "source_page": page_num,
                "evidence_text": ctx(text, m.start(), m.end()),
            })
    return records


def get_conditions(texts: list[str]) -> dict:
    """Extract measurement conditions from methods section text."""
    all_text = " ".join(texts)
    cond = {"heating_rate_K_min": None, "atmosphere": None}
    m = PAT_HEATING.search(all_text)
    if m:
        cond["heating_rate_K_min"] = float(m.group("value"))
    if PAT_ATMO.search(all_text):
        cond["atmosphere"] = "N2"
    return cond


# ── Paper-specific table extractors ───────────────────────────────────────────
def extract_chen_2021(pdf_path: Path, source_id: str, doi: str) -> list[dict]:
    """
    Table 1: polymer name | SMILES | Tg (K) | method | polymer class
    No grid lines — word-coordinate reconstruction.
    Col breaks: name <160, SMILES <370, Tg <415, method <465, class rest
    """
    records = []
    texts = page_texts(pdf_path)
    cond  = get_conditions(texts)

    for page_idx in range(len(texts)):
        rows = reconstruct_rows(pdf_path, page_idx, y_min=380)
        for row in rows:
            cols = assign_cols(row, breaks=(160, 370, 415, 465))
            if len(cols) < 3:
                continue
            name, smiles, tg_raw = cols[0], cols[1], cols[2]
            method = cols[3] if len(cols) > 3 else "DSC"
            pclass = cols[4] if len(cols) > 4 else "homopolymer"

            if not name or any(skip in name for skip in ["Polymer", "Name", "SMILES"]):
                continue
            nums = re.findall(r"\d{2,3}(?:\.\d+)?", tg_raw)
            if not nums:
                continue

            records.append({
                "polymer_name":         name,
                "repeat_unit_smiles":   smiles if smiles else None,
                "polymer_class":        pclass if pclass else "homopolymer",
                "tg_value":             float(nums[0]),
                "tg_unit":              "K",
                "tg_relation":          None,
                "tg_limit_value":       None,
                "measurement_method":   method if method else "DSC",
                "heating_rate_K_min":   cond["heating_rate_K_min"],
                "atmosphere":           cond["atmosphere"],
                "source_id":            source_id,
                "source_type":          "scientific_paper",
                "doi":                  doi,
                "extraction_method":    "pdf_table",
                "source_page":          page_idx + 1,
                "evidence_text":        " | ".join(c for c in cols if c),
                "notes":                "Table 1. Tg in K. Conditions from methods section.",
            })
    return records


def extract_wang_2023(pdf_path: Path, source_id: str, doi: str) -> list[dict]:
    """
    Table 3: polymer code | diamine | Tg (°C) DMA | ...
    Special: FDAn-ODA has Tg > 450 — stored as limit.
    """
    records = []
    texts = page_texts(pdf_path)
    cond  = get_conditions(texts)

    for page_idx in range(len(texts)):
        rows = reconstruct_rows(pdf_path, page_idx, y_min=315)
        for row in rows:
            cols = assign_cols(row, breaks=(125, 245, 325, 395, 465))
            if len(cols) < 3:
                continue
            name    = cols[0]
            tg_raw  = cols[2]   # 3rd column = Tg (°C)

            if not name or any(skip in name for skip in ["Polymer", "Code", "FDAn-b", "Table"]):
                continue
            if not tg_raw:
                continue

            # Check for limit value
            limit_m = re.match(r"([><=]+)\s*(\d+(?:\.\d+)?)", tg_raw)
            nums    = re.findall(r"\d{2,3}(?:\.\d+)?", tg_raw)

            if limit_m:
                records.append({
                    "polymer_name":       name,
                    "repeat_unit_smiles": None,
                    "polymer_class":      "polyimide",
                    "tg_value":           None,
                    "tg_unit":            "C",
                    "tg_relation":        limit_m.group(1),
                    "tg_limit_value":     float(limit_m.group(2)),
                    "measurement_method": "DMA",
                    "heating_rate_K_min": cond["heating_rate_K_min"],
                    "atmosphere":         cond["atmosphere"],
                    "source_id":          source_id,
                    "source_type":        "scientific_paper",
                    "doi":                doi,
                    "extraction_method":  "pdf_table",
                    "source_page":        page_idx + 1,
                    "evidence_text":      " | ".join(c for c in cols if c),
                    "notes":              "Limit value — Tg exceeds DMA instrument range.",
                })
            elif nums:
                records.append({
                    "polymer_name":       name,
                    "repeat_unit_smiles": None,
                    "polymer_class":      "polyimide",
                    "tg_value":           float(nums[0]),
                    "tg_unit":            "C",
                    "tg_relation":        None,
                    "tg_limit_value":     None,
                    "measurement_method": "DMA",
                    "heating_rate_K_min": cond["heating_rate_K_min"],
                    "atmosphere":         cond["atmosphere"],
                    "source_id":          source_id,
                    "source_type":        "scientific_paper",
                    "doi":                doi,
                    "extraction_method":  "pdf_table",
                    "source_page":        page_idx + 1,
                    "evidence_text":      " | ".join(c for c in cols if c),
                    "notes":              "Table 3. Tg in C by DMA.",
                })

    # Regex fallback for inline values
    inline = extract_inline(texts, source_id, doi)
    if inline:
        for r in inline:
            r["polymer_class"]      = "polyimide"
            r["measurement_method"] = r.get("measurement_method") or "DMA"
            r["heating_rate_K_min"] = cond["heating_rate_K_min"]
            r["atmosphere"]         = cond["atmosphere"]
        records.extend(inline)

    return records


def extract_new_2024(pdf_path: Path, source_id: str, doi: str) -> list[dict]:
    """
    Table 2: polymer code | diamine | Tg (°C) | Td5% | Td10% | char yield
    Also extract inline Tg from Section 3.2 for cross-validation.
    """
    records = []
    texts = page_texts(pdf_path)
    cond  = get_conditions(texts)

    # Table extraction
    for page_idx in range(len(texts)):
        rows = reconstruct_rows(pdf_path, page_idx, y_min=312)
        for row in rows:
            cols = assign_cols(row, breaks=(135, 260, 335, 410, 480))
            if len(cols) < 3:
                continue
            name   = cols[0]
            tg_raw = cols[2]   # 3rd column = Tg (°C)

            if not name or any(skip in name for skip in ["Polymer", "Code", "PI-b", "Table"]):
                continue
            nums = re.findall(r"\d{2,3}(?:\.\d+)?", tg_raw)
            if not nums:
                continue

            records.append({
                "polymer_name":       name,
                "repeat_unit_smiles": None,
                "polymer_class":      "polyimide",
                "tg_value":           float(nums[0]),
                "tg_unit":            "C",
                "tg_relation":        None,
                "tg_limit_value":     None,
                "measurement_method": "DSC",
                "heating_rate_K_min": cond["heating_rate_K_min"],
                "atmosphere":         cond["atmosphere"],
                "source_id":          source_id,
                "source_type":        "scientific_paper",
                "doi":                doi,
                "extraction_method":  "pdf_table",
                "source_page":        page_idx + 1,
                "evidence_text":      " | ".join(c for c in cols if c),
                "notes":              "Table 2. Tg in C. DSC 10 C/min N2.",
            })

    # Inline regex — cross-validation from Section 3.2
    inline = extract_inline(texts, source_id, doi)
    for r in inline:
        r["polymer_class"]      = "polyimide"
        r["measurement_method"] = "DSC"
        r["heating_rate_K_min"] = cond["heating_rate_K_min"]
        r["atmosphere"]         = cond["atmosphere"]
        r["notes"] = "Inline value from Section 3.2 — cross-check with Table 2."
    records.extend(inline)

    return records


# ── Schema columns (matches dataset_schema.json v0.2.0) ─────────────────────
SCHEMA_COLS = [
    "record_id", "polymer_name", "repeat_unit_smiles", "polymer_class",
    "tg_value", "tg_unit", "tg_relation", "tg_limit_value", "tg_std",
    "measurement_method", "heating_rate_K_min", "atmosphere",
    "molecular_weight_g_mol", "mw_type",
    "source_id", "source_type", "doi",
    "conflict_flag", "extraction_method", "notes",
    "source_page", "evidence_text",   # provenance extras
]

EXTRACTORS = {
    "paper_chen_2021": extract_chen_2021,
    "paper_wang_2023": extract_wang_2023,
    "paper_new_2024":  extract_new_2024,
}

# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    with MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    all_records: list[dict] = []

    for src in manifest["input_sources"]:
        sid      = src["source_id"]
        pdf_path = ROOT / src["pdf_path"]
        doi      = src["doi"]

        print(f"\n{'='*55}")
        print(f"Source:  {sid}")
        print(f"PDF:     {pdf_path.name}")
        print(f"DOI:     {doi}")

        if not pdf_path.exists():
            msg = f"PDF not found: {pdf_path}"
            print(f"  SKIP — {msg}")
            log({"source_id": sid, "status": "skipped", "issue": msg})
            continue

        extractor = EXTRACTORS.get(sid)
        if extractor is None:
            print(f"  SKIP — no extractor for {sid}")
            log({"source_id": sid, "status": "skipped", "issue": "no extractor"})
            continue

        try:
            records = extractor(pdf_path, sid, doi)
            print(f"  Extracted: {len(records)} records")
            all_records.extend(records)
            log({"source_id": sid, "status": "ok",
                 "records": len(records), "pdf": str(pdf_path.name)})
        except Exception as e:
            print(f"  ERROR: {e}")
            log({"source_id": sid, "status": "error", "error": repr(e)})

    if not all_records:
        print("\nNo records extracted. Check PDF paths.")
        return

    df = pd.DataFrame(all_records)
    df["conflict_flag"] = False
    df = df.reset_index(drop=True)
    df.insert(0, "record_id", [f"rec_tg_pdf_{i:04d}" for i in range(len(df))])
    for col in SCHEMA_COLS:
        if col not in df.columns:
            df[col] = None

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df[SCHEMA_COLS].to_csv(OUT_CSV, index=False)

    print(f"\n{'='*55}")
    print(f"Total records: {len(df)}")
    print(df.groupby("source_id")[["record_id"]].count().rename(
        columns={"record_id": "records"}).to_string())
    print(f"\nOutput: {OUT_CSV.relative_to(ROOT)}")
    log({"source_id": "all", "status": "done",
         "total_records": len(df), "output": str(OUT_CSV)})


if __name__ == "__main__":
    main()
