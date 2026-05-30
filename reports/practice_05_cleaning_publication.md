# Practice 5 — Cleaning, normalization and publication

## 1. Goal

Assemble the publication-ready Polymer Tg prediction dataset from the Practice 3
(PDF) and Practice 4 (web / dataset) extraction outputs, normalize values,
deduplicate, validate against the schema, and document the result.

## 2. Inputs

| File | Origin | Rows |
|------|--------|------|
| `data/extracted/all_papers_table3_filled.csv` | Practice 3 (PDF, MDPI Polymers articles 16020303, 16223188, 15173549) | 15 |
| `data/extracted/ds_zenodo_lamalab_tg.csv` | Practice 4 (Zenodo dataset 10.5281/zenodo.15783761, LamaLab) | 7,367 |
| `data/extracted/pubchem_lookups.csv` | Practice 4 (PubChem PUG-REST lookups for monomers) | reference only — not merged into the published table |

Total input rows for cleaning: **7,382**.

## 3. Cleaning pipeline

The pipeline is declared in `specs/cleaning_pipeline.json` and executed by
`scripts/build_dataset.py` (column alignment + merge) and
`scripts/clean_dataset.py` (steps 03–14 below).

| # | Step | Effect on real data |
|---|------|---------------------|
| 01 | Select schema columns | Drops helper columns (`page`, `table_id`, `evidence_text`, `review_status`, `zenodo_row_index`, `monomer_a_smiles`, `monomer_b_smiles`, `smiles_source`) from each extracted CSV |
| 02 | Concatenate PDF + web | 15 + 7 367 = 7 382 interim rows |
| 03 | Strip/Unicode-normalize text fields | Trims whitespace, NFC, maps `NA / N/A / - / none / null` to empty string |
| 04 | Normalize `polymer_class` | Maps the 22 Zenodo plural labels (`Polysiloxanes`, `Polyvinyls`, ...) and the snake_case PDF labels to the schema vocabulary; unmappable labels become `other` with a note |
| 05 | Normalize `tg_unit` | All PDF rows: `C` (5 surviving); all Zenodo rows: `K` (7 367) |
| 06 | Cast `tg_value` to float; drop missing | Drops 1 row (`rec_pdf_008` — BTD-FND, Tg could not be measured, > 350 °C close to decomposition) |
| 07 | Internal K conversion + range check `[100, 900] K` | 0 rows dropped |
| 08 | Drop rows without `repeat_unit_smiles` | Drops 9 polyimide rows (`rec_pdf_006/007/009/010..015`) whose repeat units were not auto-assembled in Practice 3 |
| 09 | Normalize `measurement_method` | All PDF: `DSC` (4) or `DMA` (1 surviving in this run — only the PPO paper rows survived; the DMA rows were the polyimide rows that got dropped at step 08); all Zenodo: `unknown` |
| 10 | Check `source_id ∈ source_map.json` | 0 rows dropped (all five declared sources are valid) |
| 11 | Exact deduplication | 0 rows removed |
| 12 | Flag cross-source disagreement (>20 K) | 6 rows flagged (see §5) |
| 13 | Schema validation (columns) | Passes |
| 14 | Write `data/processed/dataset.csv` | **7 372 rows** |

`scripts/clean_dataset.py` writes:

- `data/processed/dataset.csv` — final publication artifact (7 372 rows × 13 schema columns)
- `data/interim/merged_records.csv` — concatenated interim table (7 382 rows)
- `data/interim/cleaning_drops.csv` — full drop log, one row per dropped record + reason
- `data/interim/cleaning_summary.txt` — short summary of counts

## 4. Drops

| Reason | Count | Examples |
|--------|-------|----------|
| `smiles_missing` | 9 | `rec_pdf_006` (BTD-MIMA), `rec_pdf_010` (FLPI-1) — polyimides whose repeat unit was not auto-assembled in Practice 3; raw data preserved in `data/extracted/` |
| `tg_value_missing` | 1 | `rec_pdf_008` (BTD-FND) — Tg overlaps T_d onset; reported qualitatively as ">350 °C" but no numeric value in the source |

Both drop categories are *expected* and reflect honest limitations of the
upstream extraction, not pipeline failures. The dropped records remain
available in `data/extracted/` for follow-up enrichment (e.g. building the
polyimide repeat unit from `monomer_a_smiles` + `monomer_b_smiles` columns with
RDKit).

## 5. Cross-source disagreement

After cleaning, six rows share the SMILES
`[*]Oc1c(C)cc([*])cc1C` (poly(2,6-dimethyl-1,4-phenylene oxide), PPO).
Their Tg values, converted to Kelvin for comparison only:

| record_id | source_id | polymer_name | Tg (orig.) | Tg (K) |
|-----------|-----------|--------------|-----------|--------|
| `rec_pdf_001` | `paper_polym16020303` | DOPO-Me-PPO | 173.60 °C | 446.75 |
| `rec_pdf_002` | `paper_polym16020303` | DOPO-C11-PPO | 157.80 °C | 430.95 |
| `rec_pdf_003` | `paper_polym16020303` | DOPO-Ph-PPO | 183.20 °C | 456.35 |
| `rec_pdf_004` | `paper_polym16020303` | DOPO-Bz-PPO | 178.20 °C | 451.35 |
| `rec_pdf_005` | `paper_polym16020303` | PPO® SA90 | 139.20 °C | 412.35 |
| `rec_zen_04737` | `ds_zenodo_lamalab_tg` | (Zenodo entry) | 485.15 K | 485.15 |

Spread: **72.8 K**. All six rows have `cross_source_disagreement` appended
to their `notes` field. The dataset deliberately **keeps all six** because the
disagreement is real and informative:

- The five PDF rows are DOPO-functionalized low-molecular-weight PPO
  oligomers (Mn = 2 288 – 3 561 g/mol per the source). Tg is depressed by
  end-group dominance and low MW (Flory–Fox behaviour).
- The Zenodo entry (485.15 K ≈ 212 °C) is the textbook Tg for
  high-molecular-weight PPO.

Downstream models can either filter by source or use this spread to
estimate measurement uncertainty for this repeat unit.

## 6. Final dataset

- Path: `data/processed/dataset.csv`
- Rows: **7 372**
- Columns: 13 (exact match to `specs/dataset_schema.json`)
- License: CC-BY-4.0 (`LICENSE`)
- Citation metadata: `CITATION.cff`
- Dataset card: `dataset_card.md`

Composition:

| Field | Distribution |
|-------|--------------|
| `source_type` | `dataset` 7 367; `paper` 5 |
| `source_id` | `ds_zenodo_lamalab_tg` 7 367; `paper_polym16020303` 5 |
| `measurement_method` | `unknown` 7 367; `DSC` 5 |
| `polymer_class` | `polyimide` 1 765; `polyether` 1 749; `other` 1 233; `polyester` 660; `poly(meth)acrylate` 617; `polyamide` 486; `polystyrene` 241; `polysiloxane` 238; `polycarbonate` 160; `polyurethane` 123; `polyolefin` 55; `fluoropolymer` 40; `polyphenylene_oxide` 5 |
| `tg_value` range (in K, computed) | 134.15 – 768.15; mean 417.08; median 410.15 |

## 7. Validation

```
$ python scripts/validate_project.py
Validation passed. (0 warning(s))

$ pytest -q
15 passed in 0.92s
```

The validation script checks: required files, JSON parsability, schema column
match, `record_id` uniqueness, foreign keys against `source_map.json`, numeric
`tg_value` in `[100, 900] K`, controlled vocabularies for `tg_unit`,
`polymer_class`, `measurement_method`, `source_type`, `extraction_method`, and
non-empty `repeat_unit_smiles`.

## 8. Publication-readiness checklist

- [x] `data/processed/dataset.csv` matches `specs/dataset_schema.json`
- [x] All `source_id` values present in `specs/source_map.json`
- [x] Cleaning pipeline declared in `specs/cleaning_pipeline.json`
- [x] Validation rules declared in `specs/validation_rules.json`
- [x] `LICENSE` replaced with real license text (CC-BY-4.0)
- [x] `CITATION.cff` updated with project metadata
- [x] `dataset_card.md` updated for polymer Tg dataset
- [x] `reports/final_report.md` written
- [x] `pytest` suite passes (15 tests)
- [ ] Fill author name, ORCID, and email in `project.json` and `CITATION.cff`
      before publication
- [ ] Decide whether to re-attempt polyimide repeat-unit assembly (RDKit) and
      re-run the pipeline to recover the 9 dropped polyimide records

## 9. Reproducibility

```
# from the repo root, in Colab or any Python 3.10+ environment
pip install -r requirements.txt

python scripts/build_dataset.py     # 15 + 7367 -> 7382 interim rows
python scripts/clean_dataset.py     # -> 7372 published rows
python scripts/validate_project.py  # -> "Validation passed."
pytest                              # 15 tests pass
```
