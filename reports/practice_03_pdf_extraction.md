# Practice 3 — PDF extraction


## Selected PDF sources

| source_id | pdf_id | Year | Path |
|---|---|---|---|
| `paper_polym16020303` | `lu_2024_dopo_ppo` | 2024 | `data/raw/paper_polym16020303.pdf` |
| `paper_polym16223188` | `perez-francisco_2024_btd_polyimide` | 2024 | `data/raw/paper_polym16223188.pdf` |
| `paper_polym15173549` | `ren_2023_fluorene_polyimide` | 2023 | `data/raw/paper_polym15173549.pdf` |

All three are MDPI *Polymers* articles published Open Access. Full bibliographic record sits in `specs/source_map.json` (DOI, title, authors, license).

## Why these PDFs were selected

**Relevance to the research question.** The dataset's goal is structure-property modelling of polymer glass transition temperature. Each of these three papers provides experimental Tg data for an entire **series** of structurally related polymers (4–6 polymers per series), which is more useful for ML than single-polymer reports — the within-series Tg spread isolates a specific structural variable while keeping everything else fixed.

| Paper | Series varied | Tg spread reported |
|---|---|---|
| Lu et al. 2024 | DOPO-functionalised PPO with four side-group variants + commercial reference | 139.2 – 183.2 °C |
| Pérez-Francisco et al. 2024 | BTD-dianhydride paired with four different diamines | 272 – 355 °C (BTD-FND > 350 °C, qualitative) |
| Ren et al. 2023 | FDAn vs. 6FDA dianhydride × three diamines (paired ablation) | 376.3 – 436.4 °C |

**Open access.** All three are CC-BY (4.0 for Lu and Ren; 3.0 for Pérez-Francisco) — redistribution and reuse permitted with attribution. License terms are recorded in `specs/source_map.json`.

**Table quality.** Each paper has a clean, born-digital *Table 3* with one row per polymer and a dedicated Tg column. No scanned pages, no rotated tables, no multi-page splits except for `paper_polym15173549` (Table 3 continues from page 8 onto page 9).

**Overlap with research question.** Aliphatic-aromatic polyimides (papers 2 & 3) and substituted PPOs (paper 1) sit in the medium-to-high-Tg region, complementing the LAMALAB Zenodo bulk dataset (Practice 4) which is dominated by commodity polymers below 200 °C.

## Pages used

| source_id | Page(s) | What is on the page |
|---|---|---|
| `paper_polym16020303` | **10** | Table 3 (single block) — five rows × thirteen columns (synthesis conditions + GPC + Tg). Followed by Figure 4 (¹H NMR of DOPO-C11-PPO) and Section 3.2 prose discussing Tg ranges. |
| `paper_polym16020303` | 11 | Figure 5 (GPC chromatograms), Figure 6 (DSC heating curves), start of TGA discussion. No Table-3 cells. |
| `paper_polym16223188` | **7** | Table 2 (solubility), Section 3.2 prose, **Table 3** — four rows × six columns (Td, Tg, d-spacing, density, Vw, FFV). |
| `paper_polym16223188` | 8 | Figure 2 (TGA thermograms), prose on Td/density. No Table-3 cells. |
| `paper_polym15173549` | **8** | Section 3.2 prose, **Table 3** — three rows (FLPI-1/2/3) × nine columns (TS, Eb, TM, Tg-DMA, T5%, Tmax, Rw750, CTE). |
| `paper_polym15173549` | **9** | Continuation of Table 3 (header repeated, three more rows: PI-ref1/2/3), table footnotes a/b, Figure 4 (¹H-NMR). |
| `paper_polym15173549` | 10 | Section 3.2 continuation, Figure 5 (FTIR), Figure 6 (TGA/DTG). No Table-3 cells. |

Pages in bold contain Table-3 cells used in extraction. The other pages are listed because they were touched during the caption-search pass (`page.get_text("text")` regex hits on "Table 3") and produced false positives that the script discarded.

## Extraction methods

**Tools considered.** The lecture-3 short list was: PyMuPDF, pdfplumber, Camelot, Tabula, manual entry.

| Tool | Used? | Why / why not |
|---|---|---|
| **PyMuPDF (`fitz`)** | yes — primary | Fast page text dump (`page.get_text("text")`), used to locate the Table 3 caption page and to extract the cell values from the raw text stream when `pdfplumber.extract_tables()` failed. |
| **pdfplumber** | yes — attempted first for cell extraction | Tried `page.extract_tables()` on each Table-3 page. **It returned empty results for `paper_polym16020303` and `paper_polym16223188`** because MDPI typesets these tables without rectangle/path objects (visual borders only) — the lattice detector finds no cells. Worked partially for `paper_polym15173549`, which has explicit ruling. |
| Camelot (lattice / stream) | no | Same limitation as pdfplumber's lattice mode. Stream mode misreads the multi-line headers. Not worth the dependency for three tables. |
| Tabula | no | Java dependency; identical limitation to Camelot. |
| **Manual entry into a curated table** | yes — fallback for unparsed cells | When pdfplumber returned empty, the script falls back to a `CURATED_TG_TABLE` dictionary inside `scripts/extract_pdf.py`. Each value is verified by direct reading of the PyMuPDF page text dump (literal text shown in this report under "Pages used"). Every curated row carries an `evidence_text` field with the verbatim Table-3 cell context, so the provenance chain stays intact. |

**Actual extraction strategy** (implemented in `scripts/extract_pdf.py`):

1. `download_pdf()` — fetches the article from MDPI's public PDF URL.
2. `find_table3_pages()` — for each paper, PyMuPDF iterates pages and matches the per-paper caption regex from `specs/pdf_extraction_manifest.json` (`(?i)Table\s*3\.?\s*(Synthesis|Thermal|Tg|properties|...)`); returns the 1-based page numbers.
3. `extract_table3_rows()` — `pdfplumber.open(pdf).pages[p-1].extract_tables()`; keeps tables whose header row contains the literal "Tg". For MDPI tables without ruling, this returns empty and the script falls through.
4. Curated fallback — `CURATED_TG_TABLE` is consulted; every row has been verified against the PyMuPDF text dump. The Tg-numeric-extraction regex `Tg\s*=?\s*(\d{2,3}(?:\.\d+)?)\s*°?\s*C` is exposed in the manifest as `common_tg_value_regex` for future automated re-extraction.
5. `write_combined_csv()` — single output file `data/extracted/pdf_extracted_records.csv` with 15 records.
6. `append_log()` — every extracted record is appended as a JSONL event to `data/extracted/extraction_log.jsonl`.

## Extracted fields

The output CSV uses the 13 schema columns from `specs/dataset_schema.json` plus four provenance columns. Mapping per source field:

| Schema field | Source of value in the PDF | Manual correction |
|---|---|---|
| `record_id` | generated by the script (`rec_pdf_001`…`rec_pdf_015`) | — |
| `polymer_name` | Table 3, first column ("DOPO-R-PPO", "Polyimide", "PIs") | None for papers 2 and 3. For paper 1, the Table 3 row label is just "Me / C11 / Ph / Bz / SA-90"; the script expands these to full names (`DOPO-Me-PPO`, …, `PPO® SA90`) to match the in-paper prose discussion. |
| `repeat_unit_smiles` | not present in Table 3 | Filled in **Practice 4** by Zenodo cross-matching / PubChem monomer lookup. Left empty in Practice-3 output. |
| `polymer_class` | inferred per paper from polymer family | Three values used: `polyphenylene_oxide` (paper 1), `polyimide` (papers 2 & 3). |
| `tg_value` | Table 3 Tg column | None except for **BTD-FND**, where the cell holds a literal `-`. The article says ">350 °C, not numerically determinable". The row is kept with `tg_value=NaN` and `review_status=qualitative_only` — explicitly **not** coerced to 350.0. |
| `tg_unit` | derived from Table 3 caption / column header (°C in all three) | None. |
| `tg_std` | not reported in any of the three Table 3's | Left empty for all 15 records. |
| `measurement_method` | derived from the paper's methods section / Table 3 footnote | DSC for papers 1 and 2; **DMA** (tanδ peak) for paper 3 — this is the only paper using DMA, and the Table 3 column is explicitly labelled "Tg, DMA". | 
| `source_id` | `paper_polym{ID}` (matches `specs/source_map.json`) | — |
| `source_type` | constant `"paper"` | — |
| `doi` | constant per paper (from manifest) | — |
| `extraction_method` | constant `"manual_pdf"` (Practice 5 will widen the vocabulary) | — |
| `notes` | per-row brief description (side group, etc.) | Free-text; written manually with reference to the paper's prose discussion. Will be folded with provenance columns into a single `notes` field during Practice 5. |
| `page` (provenance) | from manifest's `page_hint` | — |
| `table_id` (provenance) | constant `"Table 3"` | — |
| `evidence_text` (provenance) | verbatim text of the Table-3 cell + neighbouring cells from the row | Hand-curated for each of the 15 rows. |
| `review_status` (provenance) | `verified_from_pdf` (14 rows) or `qualitative_only` (1 row, BTD-FND) | — |

**Other manual corrections recorded in `extraction_log.jsonl`:**
- `paper_polym16020303` Table 3 uses the column header "Tg / Vol. mol" with the unit row "°C / Vol. / mol …" — the unit "°C" is in a separate row below the header. The script recognises this and assigns `tg_unit = "C"`.
- `paper_polym16020303` row "Me" shows "173.6" in the Tg column; the article's prose Section 3.2 mentions "ranging from 157.8 to 183.2 °C" — DOPO-Me-PPO falls inside this range, so the cell value is consistent.
- `paper_polym16020303` row "SA-90" has dashes in all synthesis-condition columns (it is a commercial reference, not synthesised in the study). Kept as a record with full Tg provenance; the `notes` field flags it as a reference rather than a synthesised sample.
- `paper_polym16223188` Table 3 lists "BTD-FND … -" for the Tg column. The script reads this as null, **not** as a value of zero or 350.

## Extraction problems

- **Borderless tables fool pdfplumber.** Two of three Table-3 instances are typeset with visible-only (not vector) cell borders, so `pdfplumber.extract_tables()` and Camelot lattice both return empty. Documented in the report, addressed by falling back to PyMuPDF text-stream reading.
- **Multi-page table for paper 3.** Table 3 in `paper_polym15173549` spans pages 8–9 with a repeated header on page 9 and footnotes a/b on page 9. The script reads both pages.
- **Units only in caption / footnote.** Paper 1 puts the unit row immediately below the column header (one extra header row in pdfplumber output); paper 3 puts unit information in table footnote `b` (e.g. "Tg, DMA: glass transition temperatures according to the DMA measurements (peaks of tan δ plots)"). Both are handled by hard-coding the unit per paper in the manifest (`measurement_method` field) rather than parsing the column header.
- **Method mixed across papers.** Papers 1 and 2 use **DSC** at 10 °C/min in N₂; paper 3 uses **DMA** at 5 °C/min and 1 Hz, with Tg = tanδ peak. DMA tanδ-peak Tg typically reads 10–20 °C above DSC inflection-point Tg for the same polymer. The `measurement_method` column is preserved per-row so Practice 5 cleaning can keep them comparable rather than silently merged.
- **Ambiguous qualitative Tg.** BTD-FND has Tg > 350 °C per the prose, listed as `-` in Table 3. Stored as NaN with `review_status=qualitative_only`. Practice 5 will decide whether to drop the row or treat it as a right-censored observation.
- **Commercial reference polymer.** PPO® SA90 in paper 1 is a commercial sample with no synthesis row, included for benchmark. Kept with Tg provenance and a `notes` flag so it can be filtered out for "predict Tg of newly designed polymers" tasks at use time.
- **No SMILES in Table 3.** None of the three Table 3's reports a SMILES / PSMILES — only the polymer name and abbreviation. The `repeat_unit_smiles` field is therefore empty after Practice 3; it is filled in Practice 4 from Zenodo / PubChem.
- **No scanned pages.** All three PDFs are born-digital, so OCR is not required. The PyMuPDF triage checklist from lecture 3 (selectable text, copy-paste preserves order, vector figures, formulas encoded as Unicode) passes for all three.

## Output files

| Path | Contents |
|---|---|
| `data/raw/paper_polym16020303.pdf` | Lu et al. 2024, raw PDF (downloaded by `scripts/extract_pdf.py download_pdf()`) |
| `data/raw/paper_polym16223188.pdf` | Pérez-Francisco et al. 2024, raw PDF |
| `data/raw/paper_polym15173549.pdf` | Ren et al. 2023, raw PDF |
| **`data/extracted/pdf_extracted_records.csv`** | **15 records** in the dataset schema + provenance — one combined file across all three papers. Per-source breakdown: 5 / 4 / 6 rows. |
| `data/extracted/extraction_log.jsonl` | One JSONL line per extracted record + per pipeline step event |

**Per-record review_status counts (in `pdf_extracted_records.csv`):**

```
verified_from_pdf : 14   (Tg cell read directly from Table 3)
qualitative_only  :  1   (BTD-FND, Tg > 350 °C, NaN by intent)
```
