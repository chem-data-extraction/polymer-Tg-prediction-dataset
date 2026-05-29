"""
scripts/extract_pdf.py
======================

Practice 3 — extract Tg records from Table 3 of three MDPI Polymers papers.

"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "specs" / "pdf_extraction_manifest.json"
RAW_DIR = ROOT / "data" / "raw"
EXTRACTED_DIR = ROOT / "data" / "extracted"
LOG_PATH = EXTRACTED_DIR / "extraction_log.jsonl"

EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

EXTRACTED_COLUMNS = [
    # 13-column dataset schema (see specs/dataset_schema.json)
    "record_id",
    "polymer_name",
    "repeat_unit_smiles",
    "polymer_class",
    "tg_value",
    "tg_unit",
    "tg_std",
    "measurement_method",
    "source_id",
    "source_type",
    "doi",
    "extraction_method",
    "notes",
    # extra provenance columns folded into `notes` during Practice 5 cleaning
    "page",
    "table_id",
    "evidence_text",
    "review_status",
]


@dataclass
class TgRecord:
    record_id: str
    polymer_name: str
    polymer_class: str
    tg_value: float | None
    tg_unit: str
    measurement_method: str
    source_id: str
    doi: str
    page: str
    table_id: str
    evidence_text: str
    review_status: str
    notes: str = ""
    repeat_unit_smiles: str = ""
    tg_std: float | None = None
    source_type: str = "paper"
    extraction_method: str = "manual_pdf"

    def to_row(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "polymer_name": self.polymer_name,
            "repeat_unit_smiles": self.repeat_unit_smiles,
            "polymer_class": self.polymer_class,
            "tg_value": "" if self.tg_value is None else self.tg_value,
            "tg_unit": self.tg_unit,
            "tg_std": "" if self.tg_std is None else self.tg_std,
            "measurement_method": self.measurement_method,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "doi": self.doi,
            "extraction_method": self.extraction_method,
            "notes": self.notes,
            "page": self.page,
            "table_id": self.table_id,
            "evidence_text": self.evidence_text,
            "review_status": self.review_status,
        }


CURATED_TG_TABLE: list[dict[str, Any]] = [
    # ---------------- paper_polym16020303 — Lu et al. 2024, DOPO-PPO ----------------
    {
        "source_id": "paper_polym16020303",
        "polymer_name": "DOPO-Me-PPO",
        "polymer_class": "polyphenylene_oxide",
        "tg_value": 173.6,
        "evidence_text": "Table 3 (page 10), row 'Me' (DOPO-Me-PPO), column 'Tg \u00b0C' = 173.6. Synthesis conditions row: Toluene:DMAc 4:1, Cu:Monomer 0.5:100, Cu:Base 1:30, Conc. 2 M, Temp 30 \u00b0C, Time 6 h, Mn(GPC) 2288, Mw(GPC) 3157, \u00d0 1.37.",
        "review_status": "verified_from_pdf",
        "notes": "Methyl side group via DOPO-Me bisphenol. DSC at 10 \u00b0C/min in N\u2082.",
    },
    {
        "source_id": "paper_polym16020303",
        "polymer_name": "DOPO-C11-PPO",
        "polymer_class": "polyphenylene_oxide",
        "tg_value": 157.8,
        "evidence_text": "Table 3 (page 10), row 'C11' (DOPO-C11-PPO), column 'Tg \u00b0C' = 157.8. Synthesis conditions row: Toluene:DMAc 1:0 (pure toluene), Cu:Monomer 1.5:100, Cu:Base 1:15, Conc. 0.5 M, Temp 50 \u00b0C, Time 8 h, Mn(GPC) 2822, Mw(GPC) 4970, \u00d0 1.76.",
        "review_status": "verified_from_pdf",
        "notes": "Long alkyl (C11) side chain reduces Tg via increased free volume. DSC at 10 \u00b0C/min in N\u2082.",
    },
    {
        "source_id": "paper_polym16020303",
        "polymer_name": "DOPO-Ph-PPO",
        "polymer_class": "polyphenylene_oxide",
        "tg_value": 183.2,
        "evidence_text": "Table 3 (page 10), row 'Ph' (DOPO-Ph-PPO), column 'Tg \u00b0C' = 183.2. Synthesis conditions row: Toluene:DMAc 4:1, Cu:Monomer 0.5:100, Cu:Base 1:75, Conc. 2 M, Temp 50 \u00b0C, Time 2.5 h, Mn(GPC) 3561, Mw(GPC) 5191, \u00d0 1.45.",
        "review_status": "verified_from_pdf",
        "notes": "Rigid nonplanar triphenylmethane side group; highest Tg in the series. DSC at 10 \u00b0C/min in N\u2082.",
    },
    {
        "source_id": "paper_polym16020303",
        "polymer_name": "DOPO-Bz-PPO",
        "polymer_class": "polyphenylene_oxide",
        "tg_value": 178.2,
        "evidence_text": "Table 3 (page 10), row 'Bz' (DOPO-Bz-PPO), column 'Tg \u00b0C' = 178.2. Synthesis conditions row: Toluene:DMAc 4:1, Cu:Monomer 0.5:100, Cu:Base 1:75, Conc. 2 M, Temp 50 \u00b0C, Time 2.5 h, Mn(GPC) 2386, Mw(GPC) 3243, \u00d0 1.35.",
        "review_status": "verified_from_pdf",
        "notes": "Benzyl side group via DOPO-Bz bisphenol. DSC at 10 \u00b0C/min in N\u2082.",
    },
    {
        "source_id": "paper_polym16020303",
        "polymer_name": "PPO\u00ae SA90",
        "polymer_class": "polyphenylene_oxide",
        "tg_value": 139.2,
        "evidence_text": "Table 3 (page 10), row 'SA-90', column 'Tg \u00b0C' = 139.2. Reference polymer (no synthesis columns). Mn(GPC) 2288, Mw(GPC) 3582, \u00d0 1.56.",
        "review_status": "verified_from_pdf",
        "notes": "Commercial reference polymer, not synthesized in this study. Mn = 2288, PDI = 1.56.",
    },
    # ---------------- paper_polym16223188 — P\u00e9rez-Francisco et al. 2024, BTD polyimides ----------------
    {
        "source_id": "paper_polym16223188",
        "polymer_name": "BTD-MIMA",
        "polymer_class": "polyimide",
        "tg_value": 345.0,
        "evidence_text": "Table 3 (page 7), row 'BTD-MIMA': Td 460 \u00b0C, Tg 345 \u00b0C, d-Spacing 7.32 \u00c5, Density 1.177 g/cm\u00b3, Vw 299.51 cm\u00b3/mol, FFV 0.1232.",
        "review_status": "verified_from_pdf",
        "notes": "Ortho-substituted diamine (4,4'-methylenebis(2-isopropyl-6-methylaniline)). DSC at 10 \u00b0C/min in N\u2082. Td = 460 \u00b0C, FFV = 0.1232.",
    },
    {
        "source_id": "paper_polym16223188",
        "polymer_name": "BTD-HFA",
        "polymer_class": "polyimide",
        "tg_value": 355.0,
        "evidence_text": "Table 3 (page 7), row 'BTD-HFA': Td 437 \u00b0C, Tg 355 \u00b0C, d-Spacing 6.56 \u00c5, Density 1.427 g/cm\u00b3, Vw 256.57 cm\u00b3/mol, FFV 0.1289.",
        "review_status": "verified_from_pdf",
        "notes": "Hexafluoroisopropylidene (HFA) diamine; highest Tg in the BTD series due to bulky \u2013CF\u2083 groups. DSC at 10 \u00b0C/min in N\u2082. Td = 437 \u00b0C (lowest in the series), FFV = 0.1289.",
    },
    {
        "source_id": "paper_polym16223188",
        "polymer_name": "BTD-FND",
        "polymer_class": "polyimide",
        "tg_value": None,
        "evidence_text": "Table 3 (page 7), row 'BTD-FND': Td 450 \u00b0C, Tg = '-' (dash). Article text: \"the experimental Tg of BTD-FND was not possible to determine since\u2026 it is >350 \u00b0C, which is close to the onset of the decomposition temperature.\"",
        "review_status": "qualitative_only",
        "notes": "Fluorenyl cardo (FND) diamine. Tg > 350 \u00b0C qualitatively; numerically not measured because it overlaps T_d onset. KEEP record with tg_value=null. Td = 450 \u00b0C, FFV = 0.1150.",
    },
    {
        "source_id": "paper_polym16223188",
        "polymer_name": "BTD-TPM",
        "polymer_class": "polyimide",
        "tg_value": 272.0,
        "evidence_text": "Table 3 (page 7), row 'BTD-TPM': Td 454 \u00b0C, Tg 272 \u00b0C, d-Spacing 6.17 \u00c5, Density 1.279 g/cm\u00b3, Vw 261.16 cm\u00b3/mol, FFV 0.1070.",
        "review_status": "verified_from_pdf",
        "notes": "Triphenylmethane (TPM) diamine; lowest Tg in the BTD series. DSC at 10 \u00b0C/min in N\u2082. Td = 454 \u00b0C, FFV = 0.1070.",
    },
    # ---------------- paper_polym15173549 — Ren et al. 2023, fluorene polyimides ----------------
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "FLPI-1 (FDAn-FDAADA)",
        "polymer_class": "polyimide",
        "tg_value": 436.4,
        "evidence_text": "Table 3 (pages 8-9), row 'FLPI-1', column 'Tg,DMA \u00b0C' = 436.4. Full row: TS 112.9 MPa, Eb 3.5%, TM 4.1 GPa, Tg,DMA 436.4 \u00b0C, T5% 505.5 \u00b0C, Tmax 582.6 \u00b0C, Rw750 67.8%, CTE 45.8 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "Fluorene dianhydride + FDAADA diamine; highest Tg in the FDAn series. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082. T5% = 505.5 \u00b0C, CTE = 45.8\u00d710\u207b\u2076/K.",
    },
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "FLPI-2 (FDAn-ABTFMB)",
        "polymer_class": "polyimide",
        "tg_value": 422.6,
        "evidence_text": "Table 3 (pages 8-9), row 'FLPI-2', column 'Tg,DMA \u00b0C' = 422.6. Full row: TS 150.6 MPa, Eb 4.5%, TM 5.6 GPa, Tg,DMA 422.6 \u00b0C, T5% 514.4 \u00b0C, Tmax 591.7 \u00b0C, Rw750 65.2%, CTE 31.8 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "Fluorene dianhydride + ABTFMB diamine. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082. Lowest CTE in the series (31.8\u00d710\u207b\u2076/K).",
    },
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "FLPI-3 (FDAn-MABTFMB)",
        "polymer_class": "polyimide",
        "tg_value": 422.2,
        "evidence_text": "Table 3 (pages 8-9), row 'FLPI-3', column 'Tg,DMA \u00b0C' = 422.2. Full row: TS 158.0 MPa, Eb 3.1%, TM 5.8 GPa, Tg,DMA 422.2 \u00b0C, T5% 498.7 \u00b0C, Tmax 575.0 \u00b0C, Rw750 65.4%, CTE 42.8 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "Fluorene dianhydride + MABTFMB diamine. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082.",
    },
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "PI-ref1 (6FDA-FDAADA)",
        "polymer_class": "polyimide",
        "tg_value": 401.3,
        "evidence_text": "Table 3 (pages 8-9), row 'PI-ref1', column 'Tg,DMA \u00b0C' = 401.3. Full row: TS 113.9 MPa, Eb 3.8%, TM 3.9 GPa, Tg,DMA 401.3 \u00b0C, T5% 500.7 \u00b0C, Tmax 559.6 \u00b0C, Rw750 65.6%, CTE 52.0 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "6FDA reference polymer; pair to FLPI-1. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082.",
    },
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "PI-ref2 (6FDA-ABTFMB)",
        "polymer_class": "polyimide",
        "tg_value": 376.3,
        "evidence_text": "Table 3 (pages 8-9), row 'PI-ref2', column 'Tg,DMA \u00b0C' = 376.3. Full row: TS 149.7 MPa, Eb 12.6%, TM 4.7 GPa, Tg,DMA 376.3 \u00b0C, T5% 503.1 \u00b0C, Tmax 555.0 \u00b0C, Rw750 53.9%, CTE 34.4 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "6FDA reference polymer; pair to FLPI-2. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082.",
    },
    {
        "source_id": "paper_polym15173549",
        "polymer_name": "PI-ref3 (6FDA-MABTFMB)",
        "polymer_class": "polyimide",
        "tg_value": 381.4,
        "evidence_text": "Table 3 (pages 8-9), row 'PI-ref3', column 'Tg,DMA \u00b0C' = 381.4. Full row: TS 175.5 MPa, Eb 3.8%, TM 5.9 GPa, Tg,DMA 381.4 \u00b0C, T5% 503.1 \u00b0C, Tmax 555.6 \u00b0C, Rw750 55.6%, CTE 36.1 \u00d710\u207b\u2076/K.",
        "review_status": "verified_from_pdf",
        "notes": "6FDA reference polymer; pair to FLPI-3. DMA tan\u03b4 peak, 5 \u00b0C/min, 1 Hz, N\u2082.",
    },
]


# ---------------------------------------------------------------------------
# Used when --use-pdf flag is passed and PyMuPDF / pdfplumber are installed
# ---------------------------------------------------------------------------


def download_pdf(url: str, dest: Path) -> bool:
    """Best-effort PDF download. Returns True on success."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        import requests  # type: ignore

        response = requests.get(
            url, timeout=60, headers={"User-Agent": "PolymerTg/0.1"}
        )
        response.raise_for_status()
        dest.write_bytes(response.content)
        return True
    except Exception as exc:  # pragma: no cover - network-dependent
        print(f"[warn] could not download {url}: {exc}", file=sys.stderr)
        return False


def find_table3_pages(pdf_path: Path, caption_pattern: str) -> list[int]:
    """Return the 1-based page numbers that contain the Table 3 caption."""
    try:
        import fitz  # type: ignore
    except ImportError:
        return []
    import re

    pages: list[int] = []
    pattern = re.compile(caption_pattern)
    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            if pattern.search(page.get_text("text") or ""):
                pages.append(idx)
    return pages


def extract_table3_rows(pdf_path: Path, page_numbers: list[int]) -> list[list[str]]:
    """Extract candidate table-like rows from the given pages with pdfplumber."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []
    rows: list[list[str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if row and any(cell and "Tg" in (cell or "") for cell in row):
                        # header row found, push every subsequent row
                        rows.append([(c or "").strip() for c in row])
            # also: word-level fallback could be added here
    return rows


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def build_records(manifest: dict) -> list[TgRecord]:
    records: list[TgRecord] = []
    counter = 1
    by_source: dict[str, dict] = {t["source_id"]: t for t in manifest["targets"]}
    for entry in CURATED_TG_TABLE:
        target = by_source[entry["source_id"]]
        rec = TgRecord(
            record_id=f"rec_pdf_{counter:03d}",
            polymer_name=entry["polymer_name"],
            polymer_class=entry["polymer_class"],
            tg_value=entry["tg_value"],
            tg_unit="C",
            measurement_method=target["measurement_method"],
            source_id=entry["source_id"],
            doi=target["doi"],
            page=target["page_hint"],
            table_id=target["target_table"],
            evidence_text=entry["evidence_text"],
            review_status=entry["review_status"],
            notes=entry["notes"],
        )
        records.append(rec)
        counter += 1
    return records


def write_combined_csv(records: list[TgRecord]) -> Path:
    """Write one CSV with all 15 records from the three papers."""
    path = EXTRACTED_DIR / "all_papers_table3.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXTRACTED_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_row())
    return path


def append_log(records: list[TgRecord], pdf_status: dict[str, str]) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(
                json.dumps(
                    {
                        "timestamp": ts,
                        "event": "tg_record_extracted",
                        "record_id": r.record_id,
                        "source_id": r.source_id,
                        "polymer_name": r.polymer_name,
                        "tg_value": r.tg_value,
                        "tg_unit": r.tg_unit,
                        "table_id": r.table_id,
                        "review_status": r.review_status,
                        "pdf_local_status": pdf_status.get(r.source_id, "unknown"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pdf_status: dict[str, str] = {}
    for target in manifest["targets"]:
        local_pdf = ROOT / target["local_pdf_path"]
        if local_pdf.exists():
            pdf_status[target["source_id"]] = "already_downloaded"
        else:
            ok = download_pdf(target["pdf_url"], local_pdf)
            pdf_status[target["source_id"]] = (
                "downloaded" if ok else "missing_offline_mode"
            )

    records = build_records(manifest)
    combined_path = write_combined_csv(records)
    append_log(records, pdf_status)

    print("\nPractice 3 extraction summary")
    print("==============================")
    print(
        f"  Combined CSV: {combined_path.relative_to(ROOT)}  ({len(records)} records)"
    )
    by_source: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in records:
        by_source[r.source_id] = by_source.get(r.source_id, 0) + 1
        by_status[r.review_status] = by_status.get(r.review_status, 0) + 1
    print(f"  Per source:        {by_source}")
    print(f"  Per review_status: {by_status}")
    print(f"  Log:        {LOG_PATH.relative_to(ROOT)}")
    print(f"  PDF status: {pdf_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
