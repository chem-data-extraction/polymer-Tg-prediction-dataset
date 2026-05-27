"""
Practice 3 — PDF Extraction Pipeline
Polymer Tg Dataset

Extracts text, tables, and regex-matched values from three source PDFs:
  1. polym13111898_chen2021.pdf  — ML/SMILES approach (Table 1: polymer + Tg)
  2. polym15173549_ren2023.pdf   — Polyimide synthesis (Table 4: Tg by DSC)
  3. polym16223188_yeste2024.pdf — Alicyclic PI synthesis (Table 3: Tg by DSC)

Outputs:
  data/extracted/extracted_records_raw.csv
  data/extracted/extraction_log.jsonl
"""

import re
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import fitz           # PyMuPDF
import pdfplumber
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
RAW_DIR  = ROOT / "data" / "raw"
EXT_DIR  = ROOT / "data" / "extracted"
EXT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = EXT_DIR / "extraction_log.jsonl"
OUT_CSV  = EXT_DIR / "extracted_records_raw.csv"

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("extract_pdf")

extraction_log: list[dict] = []

def log_event(event_type: str, pdf: str, detail: str, n_records: int = 0):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "source_pdf": pdf,
        "detail": detail,
        "n_records": n_records,
    }
    extraction_log.append(entry)
    log.info("[%s] %s — %s (n=%d)", event_type, pdf, detail, n_records)


# ── Regex patterns ─────────────────────────────────────────────────────────
RE_TG_C = re.compile(
    r"T\s*g\s*[=:≈]?\s*(?P<value>[-−]?\d{1,3}(?:\.\d)?)\s*°?\s*C",
    re.IGNORECASE,
)
RE_TG_K = re.compile(
    r"T\s*g\s*[=:≈]?\s*(?P<value>\d{2,3}(?:\.\d)?)\s*K\b",
    re.IGNORECASE,
)
RE_SMILES = re.compile(r"\*[A-Za-z0-9@\[\]()\-=#\\\/+\.%*]{6,}\*")
RE_RMSE   = re.compile(r"RMSE\s*[=:≈]?\s*(?P<value>\d{1,3}(?:\.\d)?)\s*°?C", re.IGNORECASE)
RE_MAE    = re.compile(r"MAE\s*[=:≈]?\s*(?P<value>\d{1,3}(?:\.\d)?)\s*°?C", re.IGNORECASE)
RE_R2     = re.compile(r"R[²2]\s*[=:≈]?\s*(?P<value>0\.\d{2,4})", re.IGNORECASE)
RE_TD5    = re.compile(
    r"T\s*d\s*5\s*%?\s*[=:≈]?\s*(?P<value>\d{3,4})\s*°?\s*C",
    re.IGNORECASE,
)


def celsius_to_kelvin(c_str: str) -> float | None:
    """Convert Celsius string to Kelvin, handle minus/minus-sign variants."""
    try:
        val = float(c_str.replace("−", "-").replace("–", "-"))
        return round(val + 273.15, 2)
    except ValueError:
        return None


# ── Text extraction helpers ────────────────────────────────────────────────

def extract_text_fitz(pdf_path: Path) -> dict[int, str]:
    """Return {page_index: text} using PyMuPDF."""
    pages = {}
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc):
            pages[i] = page.get_text("text")
    return pages


def extract_text_pdfplumber(pdf_path: Path) -> dict[int, str]:
    """Return {page_index: text} using pdfplumber."""
    pages = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            pages[i] = page.extract_text() or ""
    return pages


def extract_tables_pdfplumber(pdf_path: Path) -> list[dict]:
    """Return list of {page, table_index, rows} dicts."""
    tables = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for pi, page in enumerate(pdf.pages):
            for ti, table in enumerate(page.extract_tables()):
                if table and len(table) >= 2:
                    tables.append({
                        "page": pi,
                        "table_index": ti,
                        "rows": table,
                    })
    return tables


# ── Record builders ────────────────────────────────────────────────────────

def records_from_regex(
    text: str,
    page: int,
    source_pdf: str,
    doi: str,
) -> list[dict]:
    """Mine Tg values, SMILES, RMSE, MAE, R² from raw text."""
    records = []
    base = dict(source_pdf=source_pdf, doi=doi, source_page=page + 1,
                source_type="text_regex", table_id=None, figure_id=None,
                confidence="regex")

    for m in RE_TG_C.finditer(text):
        v = m.group("value")
        tg_k = celsius_to_kelvin(v)
        records.append({**base,
            "entity_or_material": "polymer (unspecified)",
            "property": "Tg",
            "value_raw": v,
            "unit_raw": "°C",
            "value_celsius": float(v.replace("−", "-").replace("–", "-")),
            "value_kelvin": tg_k,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    for m in RE_TG_K.finditer(text):
        v = m.group("value")
        tg_k = float(v)
        records.append({**base,
            "entity_or_material": "polymer (unspecified)",
            "property": "Tg",
            "value_raw": v,
            "unit_raw": "K",
            "value_celsius": round(tg_k - 273.15, 2),
            "value_kelvin": tg_k,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    for m in RE_RMSE.finditer(text):
        records.append({**base,
            "entity_or_material": "ML_model",
            "property": "RMSE",
            "value_raw": m.group("value"),
            "unit_raw": "°C",
            "value_celsius": float(m.group("value")),
            "value_kelvin": None,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    for m in RE_MAE.finditer(text):
        records.append({**base,
            "entity_or_material": "ML_model",
            "property": "MAE",
            "value_raw": m.group("value"),
            "unit_raw": "°C",
            "value_celsius": float(m.group("value")),
            "value_kelvin": None,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    for m in RE_R2.finditer(text):
        records.append({**base,
            "entity_or_material": "ML_model",
            "property": "R2",
            "value_raw": m.group("value"),
            "unit_raw": "dimensionless",
            "value_celsius": None,
            "value_kelvin": None,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    for m in RE_TD5.finditer(text):
        records.append({**base,
            "entity_or_material": "polymer (unspecified)",
            "property": "Td5%",
            "value_raw": m.group("value"),
            "unit_raw": "°C",
            "value_celsius": float(m.group("value")),
            "value_kelvin": None,
            "evidence_text": text[max(0, m.start()-60):m.end()+60].replace("\n", " "),
        })

    return records


def parse_table_paper1(rows: list[list], page: int, source_pdf: str, doi: str) -> list[dict]:
    """Parse Table 1 of Chen 2021: polymer name | SMILES | Tg."""
    records = []
    if not rows or len(rows[0]) < 4:
        return records
    header = [str(c).lower() if c else "" for c in rows[0]]
    # Detect column positions
    name_col = smiles_col = tg_col = None
    for i, h in enumerate(header):
        if "polymer" in h or "name" in h:
            name_col = i
        if "smiles" in h or "repeat" in h:
            smiles_col = i
        if "tg" in h:
            tg_col = i
    if tg_col is None:
        # fallback: last numeric-looking column
        tg_col = len(header) - 2
    if name_col is None:
        name_col = 1
    if smiles_col is None:
        smiles_col = 2

    for row in rows[1:]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        name   = str(row[name_col]).strip()  if row[name_col] else ""
        smiles = str(row[smiles_col]).strip() if len(row) > smiles_col and row[smiles_col] else ""
        tg_raw = str(row[tg_col]).strip()    if len(row) > tg_col and row[tg_col] else ""

        tg_raw = tg_raw.replace("−", "-").replace("–", "-")
        try:
            tg_c = float(tg_raw)
            tg_k = round(tg_c + 273.15, 2)
        except ValueError:
            tg_c = tg_k = None

        records.append(dict(
            source_pdf=source_pdf, doi=doi,
            source_page=page + 1, source_type="table",
            table_id="Table_1", figure_id=None,
            entity_or_material=name,
            property="Tg",
            value_raw=tg_raw,
            unit_raw="°C",
            value_celsius=tg_c,
            value_kelvin=tg_k,
            smiles=smiles,
            measurement_method="experimental_literature",
            confidence="table_parsed",
            evidence_text=f"Table 1, row: {name} | {smiles} | Tg={tg_raw}",
        ))
    return records


def parse_table_paper2(rows: list[list], page: int, source_pdf: str, doi: str) -> list[dict]:
    """Parse Table 4 of Ren 2023: sample | dianhydride | diamine | Tg(DSC) | Td5% N2 | Td5% air."""
    records = []
    if not rows or len(rows[0]) < 4:
        return records
    header = [str(c).lower().replace("\n", " ") if c else "" for c in rows[0]]

    sample_col = 0
    tg_col     = next((i for i, h in enumerate(header) if "tg" in h), 3)
    td5n_col   = next((i for i, h in enumerate(header) if "td5" in h and "n" in h), 4)
    td5a_col   = next((i for i, h in enumerate(header) if "td5" in h and "air" in h), 5)

    diamine_map = {
        "FLPI-1": "FDAADA",  "FLPI-2": "ABTFMB",  "FLPI-3": "TFMB",
        "6FDA-PI-1": "FDAADA", "6FDA-PI-2": "ABTFMB", "6FDA-PI-3": "TFMB",
    }
    dianhydride_map = {
        "FLPI-1": "FDAn", "FLPI-2": "FDAn", "FLPI-3": "FDAn",
        "6FDA-PI-1": "6FDA", "6FDA-PI-2": "6FDA", "6FDA-PI-3": "6FDA",
    }

    for row in rows[1:]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        sample = str(row[sample_col]).strip() if row[sample_col] else ""
        tg_raw = str(row[tg_col]).strip()     if len(row) > tg_col and row[tg_col] else ""
        td5_n  = str(row[td5n_col]).strip()   if len(row) > td5n_col and row[td5n_col] else ""

        tg_raw = tg_raw.replace("−", "-").replace("–", "-")
        try:
            tg_c = float(tg_raw)
            tg_k = round(tg_c + 273.15, 2)
        except ValueError:
            tg_c = tg_k = None

        records.append(dict(
            source_pdf=source_pdf, doi=doi,
            source_page=page + 1, source_type="table",
            table_id="Table_4", figure_id=None,
            entity_or_material=sample,
            property="Tg",
            value_raw=tg_raw,
            unit_raw="°C",
            value_celsius=tg_c,
            value_kelvin=tg_k,
            smiles=None,
            dianhydride=dianhydride_map.get(sample, ""),
            diamine=diamine_map.get(sample, ""),
            measurement_method="DSC_10Cmin_N2_2nd_heating",
            condition="heating_rate=10°C/min; atmosphere=N2; scan=2nd_heating",
            confidence="table_parsed",
            evidence_text=f"Table 4, {sample}: Tg={tg_raw}°C, Td5%(N2)={td5_n}°C",
        ))
    return records


def parse_table_paper3(rows: list[list], page: int, source_pdf: str, doi: str) -> list[dict]:
    """Parse Table 3 of Yeste 2024: sample | diamine | Mn | Mw | PDI | Tg | Td5%."""
    records = []
    if not rows or len(rows[0]) < 4:
        return records
    header = [str(c).lower().replace("\n", " ") if c else "" for c in rows[0]]

    sample_col = 0
    tg_col     = next((i for i, h in enumerate(header) if "tg" in h), 5)
    td5_col    = next((i for i, h in enumerate(header) if "td5" in h), 6)

    diamine_map = {
        "BTD-MIMA": "MIMA (4,4'-methylenedianiline)",
        "BTD-HFA":  "HFA (4,4'-(hexafluoroisopropylidene)dianiline)",
        "BTD-FND":  "FND (9,9-bis(4-aminophenyl)fluorene)",
        "BTD-TPM":  "TPM (1,1,1-tris(4-aminophenyl)ethane)",
    }

    for row in rows[1:]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        sample = str(row[sample_col]).strip() if row[sample_col] else ""
        tg_raw = str(row[tg_col]).strip()     if len(row) > tg_col and row[tg_col] else ""
        td5_raw= str(row[td5_col]).strip()    if len(row) > td5_col and row[td5_col] else ""

        tg_raw = tg_raw.replace("−", "-").replace("–", "-")
        try:
            tg_c = float(tg_raw)
            tg_k = round(tg_c + 273.15, 2)
        except ValueError:
            tg_c = tg_k = None

        records.append(dict(
            source_pdf=source_pdf, doi=doi,
            source_page=page + 1, source_type="table",
            table_id="Table_3", figure_id=None,
            entity_or_material=sample,
            property="Tg",
            value_raw=tg_raw,
            unit_raw="°C",
            value_celsius=tg_c,
            value_kelvin=tg_k,
            smiles=None,
            dianhydride="BTD (bicyclo[2.2.2]oct-7-ene-2,3,5,6-tetracarboxylic dianhydride)",
            diamine=diamine_map.get(sample, ""),
            measurement_method="DSC_10Cmin_N2_2nd_heating",
            condition="heating_rate=10°C/min; atmosphere=N2; scan=2nd_heating",
            confidence="table_parsed",
            evidence_text=f"Table 3, {sample}: Tg={tg_raw}°C, Td5%(N2)={td5_raw}°C",
        ))
    return records


# ── Source definitions ─────────────────────────────────────────────────────
SOURCES = [
    {
        "pdf":       "polym13111898_chen2021.pdf",
        "doi":       "10.3390/polym13111898",
        "table_parser": parse_table_paper1,
        "table_label":  "Table_1",
    },
    {
        "pdf":       "polym15173549_ren2023.pdf",
        "doi":       "10.3390/polym15173549",
        "table_parser": parse_table_paper2,
        "table_label":  "Table_4",
    },
    {
        "pdf":       "polym16223188_yeste2024.pdf",
        "doi":       "10.3390/polym16223188",
        "table_parser": parse_table_paper3,
        "table_label":  "Table_3",
    },
]


# ── Main extraction loop ───────────────────────────────────────────────────

def run():
    all_records: list[dict] = []

    for src in SOURCES:
        pdf_path = RAW_DIR / src["pdf"]
        if not pdf_path.exists():
            log.error("PDF not found: %s", pdf_path)
            log_event("ERROR", src["pdf"], "file not found")
            continue

        log.info("─── Processing: %s ───", src["pdf"])
        doi = src["doi"]

        # 1. Text extraction (two engines, cross-validate)
        pages_fitz = extract_text_fitz(pdf_path)
        pages_plumb = extract_text_pdfplumber(pdf_path)
        log_event("TEXT_EXTRACT", src["pdf"],
                  f"fitz: {len(pages_fitz)} pages; pdfplumber: {len(pages_plumb)} pages",
                  n_records=len(pages_fitz))

        # 2. Regex mining over full text
        full_text = "\n".join(pages_fitz.values())
        regex_records = []
        for page_i, text in pages_fitz.items():
            regex_records.extend(records_from_regex(text, page_i, src["pdf"], doi))
        log_event("REGEX_EXTRACT", src["pdf"],
                  "Tg/RMSE/MAE/R2/Td5% patterns", n_records=len(regex_records))
        all_records.extend(regex_records)

        # 3. Table extraction
        tables = extract_tables_pdfplumber(pdf_path)
        log_event("TABLE_DETECT", src["pdf"],
                  f"{len(tables)} table(s) found by pdfplumber", n_records=len(tables))

        table_records = []
        for tbl in tables:
            parsed = src["table_parser"](
                tbl["rows"], tbl["page"], src["pdf"], doi
            )
            table_records.extend(parsed)
        log_event("TABLE_PARSE", src["pdf"],
                  f"parsed with {src['table_parser'].__name__}", n_records=len(table_records))
        all_records.extend(table_records)

    # 4. Build DataFrame and save
    df = pd.DataFrame(all_records)

    # Ensure required columns exist
    for col in ["smiles", "dianhydride", "diamine", "measurement_method", "condition"]:
        if col not in df.columns:
            df[col] = None

    col_order = [
        "source_pdf", "doi", "source_page", "source_type", "table_id", "figure_id",
        "entity_or_material", "property",
        "value_raw", "unit_raw", "value_celsius", "value_kelvin",
        "smiles", "dianhydride", "diamine",
        "measurement_method", "condition",
        "confidence", "evidence_text",
    ]
    df = df.reindex(columns=[c for c in col_order if c in df.columns])
    df.to_csv(OUT_CSV, index=False)

    # 5. Write log
    with open(LOG_PATH, "w") as f:
        for entry in extraction_log:
            f.write(json.dumps(entry) + "\n")

    log.info("Saved %d records → %s", len(df), OUT_CSV)
    log.info("Extraction log → %s", LOG_PATH)
    return df


if __name__ == "__main__":
    df = run()
    print("\nExtracted records preview:")
    print(df[["source_pdf", "source_type", "entity_or_material",
              "property", "value_raw", "unit_raw", "value_celsius"]].to_string(index=False))
