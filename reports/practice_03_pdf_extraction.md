# Practice 3 — Extraction from PDF Sources

**Dataset project:** Polymer Glass Transition Temperature (Tg) Prediction Dataset  
**Practice:** 3 — PDF extraction  
**Date:** 2025-05-27

---

## Goal

Extract Tg data from three open-access scientific papers using a deterministic PDF extraction pipeline, and compare results with a GPT-4 baseline.

---

## Source PDFs

| ID | DOI | Title (shortened) | License | Records |
|----|-----|--------------------|---------|---------|
| S01 | 10.3390/polym13111898 | Chen et al. 2021 — ML/SMILES Tg model | CC BY 4.0 | 15 |
| S02 | 10.3390/polym15173549 | Ren et al. 2023 — Fluorene-PI synthesis | CC BY 4.0 | 6 |
| S03 | 10.3390/polym16223188 | Yeste et al. 2024 — Alicyclic PI synthesis | CC BY 4.0 | 4 |

All three papers are published in *Polymers* (MDPI), open access under CC BY 4.0.

**Why these three?**  
S01 provides a diverse set of 15 common polymers with well-known Tg values, including SMILES strings — ideal for ML training. S02 and S03 provide high-Tg aromatic and alicyclic polyimides measured by DSC, filling an important chemical space region underrepresented in general datasets.

---

## Extraction pipeline

```
PDF files (data/raw/)
  ├── text extraction: PyMuPDF (fitz) + pdfplumber (cross-validate)
  ├── table extraction: pdfplumber.extract_tables()
  │     ├── parse_table_paper1()  → 15 records (name, SMILES, Tg °C)
  │     ├── parse_table_paper2()  → 6 records  (sample ID, dianhydride, diamine, Tg °C, Td5%)
  │     └── parse_table_paper3()  → 4 records  (sample ID, diamine, Mn, Mw, Tg °C, Td5%)
  └── regex mining: Tg=X°C / Tg=X K / RMSE / MAE / R² / Td5%
        → 5 additional records (ML metrics + regex Tg mentions)
  ↓
data/extracted/extracted_records_raw.csv   (30 records)
data/extracted/extraction_log.jsonl
  ↓
Normalization:
  - value_celsius + value_kelvin for all Tg records
  - polymer_class classification
  - measurement_method and condition inferred from paper methods
  - review_status and issue_flag assigned
  ↓
data/interim/merged_records.csv    (30 records)
data/processed/dataset.csv         (25 clean Tg records)
```

---

## Results

### Extraction counts

| Paper | Tool | Records | Property |
|-------|------|---------|----------|
| Chen 2021 | pdfplumber (Table 1) | 15 | Tg °C + SMILES |
| Chen 2021 | regex | 2 | RMSE, R² |
| Ren 2023  | pdfplumber (Table 4) | 6 | Tg °C (DSC) |
| Ren 2023  | regex | 2 | Tg, Td5% (text mentions) |
| Yeste 2024 | pdfplumber (Table 3) | 4 | Tg °C (DSC) |
| Yeste 2024 | regex | 1 | R² (gas transport) |
| **Total** | | **30 raw / 25 clean Tg** | |

### Tg range

| Source | Min Tg (°C) | Max Tg (°C) | Polymer type |
|--------|-------------|-------------|--------------|
| Chen 2021 | −125 (PE) | 360 (PI-PMDA-ODA) | diverse |
| Ren 2023  | 385.1 (6FDA-PI-3) | 436.4 (FLPI-1) | aromatic PI |
| Yeste 2024 | 272 (BTD-TPM) | 355 (BTD-MIMA) | alicyclic PI |

---

## Normalization decisions

1. **Units:** All Tg stored in both °C (`value_normalized`) and K (`value_kelvin`). Formula: K = °C + 273.15.
2. **Duplicates:** Regex Tg records that duplicate table records were flagged as `possible_duplicate_of_table_record` and excluded from `data/processed/dataset.csv`.
3. **Entity resolution:** `entity_or_material` kept as original paper label (e.g. "FLPI-1"); `polymer_class` column added for grouping.
4. **Conditions:** For S02/S03 the DSC condition `heating_rate=10°C/min; atmosphere=N2; scan=2nd_heating` was extracted from the Methods sections and stored in the `condition` column.
5. **ML metrics:** RMSE and R² records are kept in `data/interim/merged_records.csv` for reference but excluded from `data/processed/dataset.csv` which contains only material property measurements.

---

## Extraction difficulties

| Issue | Description | Resolution |
|-------|-------------|------------|
| Minus sign encoding | `−125` uses Unicode minus (U+2212), not ASCII `-` | Replaced in normalization |
| Superscripts in Tg | Some PDFs render Tg as "Tg" without subscript | Regex matches `T\s*g` with optional whitespace |
| Regex duplicates table | Text narrative repeats table values | Flagged and removed in dedup step |
| `polymer (unspecified)` | Regex finds Tg in running text without entity context | Flagged for manual review |

---

## Pipeline vs GPT baseline

| Criterion | Pipeline | GPT-4 baseline |
|-----------|----------|----------------|
| Table rows captured (Paper 1) | **15 / 15** | 10 / 15 (5 missed) |
| Tg value errors | **0** | 1 (PLA: 60 instead of 55) |
| Hallucinated records | **0** | 1 (Polyurethane Tg=120, not in paper) |
| Source page recorded | **yes** | no |
| Table ID recorded | **yes** | no |
| Raw evidence text | **yes** | no |
| Units (both °C and K) | **yes** | only °C |
| Reproducibility | deterministic | stochastic |

**Conclusion:** The deterministic pipeline is more complete (25 vs 20 correct records), more reliable (0 hallucinations), and provides full provenance. GPT is faster to set up but cannot be trusted for systematic data collection without manual verification of every record.

---

## Output files

| File | Description |
|------|-------------|
| `data/raw/polym13111898_chen2021.pdf` | Source PDF, Chen 2021 |
| `data/raw/polym15173549_ren2023.pdf` | Source PDF, Ren 2023 |
| `data/raw/polym16223188_yeste2024.pdf` | Source PDF, Yeste 2024 |
| `data/extracted/extracted_records_raw.csv` | 30 raw extracted records |
| `data/extracted/extraction_log.jsonl` | Event log with timestamps |
| `data/interim/merged_records.csv` | 30 records with all metadata |
| `data/processed/dataset.csv` | 25 clean Tg records (final) |
| `scripts/extract_pdf.py` | Reproducible extraction script |
| `notebooks/practice_03_pdf_extraction.ipynb` | Full pipeline notebook |
| `reports/tg_distribution.png` | Tg distribution figure |

---

## Limitations

- PDFs were processed as born-digital documents; OCR was not required.
- SMILES strings from Paper 1 (Table 1) need validation against PubChem before use in ML.
- Paper 1 provides only 15 of the 391 total dataset polymers; the remaining 376 require additional PDF pages or supplementary material.
- Conditions for Paper 1 entries vary by original source; `condition = literature_compiled; original_method_varies` was assigned.
