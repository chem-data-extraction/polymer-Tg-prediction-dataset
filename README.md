# Polymer Glass Transition Temperature (Tg) Prediction Dataset

Publication-ready **dataset project** for the course *Extraction and preparation of chemical information*. The repository moves from a research topic to a structured, validated dataset with documented sources, extraction steps, cleaning pipeline, reports, and citation metadata.

**Topic:** Polymers with experimentally measured glass transition temperature, assembled from open-access scientific articles and a public Zenodo deposit.

## Scientific task

Collect polymers with experimentally measured glass transition temperature (Tg). Each record contains the polymer structure or repeat unit, material class, measurement context (method, unit, uncertainty), and reported Tg value, so that polymer families can be compared and a structure–property dataset can be built for predicting Tg from molecular or computed descriptors.

## What is one record?

One **record** = one experimentally measured Tg for a single polymer (or repeat unit) reported in a specific source, together with the measurement context (one row in `data/processed/dataset.csv`). See `project.json` and `reports/practice_01_record_and_schema.md`.

## Repository structure

| Path | Role |
|------|------|
| `project.json` | Machine-readable project metadata |
| `specs/` | JSON schemas, source map, manifests, pipeline, validation rules |
| `data/raw/` | Unmodified PDFs, web snapshots, external exports |
| `data/extracted/` | Extraction outputs (CSV + `extraction_log.jsonl`) |
| `data/interim/` | Merged table before final cleaning + cleaning logs |
| `data/processed/` | Publication dataset (`dataset.csv`, 7 372 rows) |
| `scripts/` | Reproducible extract, build, clean, validate |
| `reports/` | Human-readable practice and final reports |
| `notebooks/` | Optional exploration only |
| `tests/` | Pytest checks for required artifacts |

**Formats:** JSON for specs and manifests; CSV for tabular data; Python for pipelines; Markdown for reports and documentation only. Notebooks are optional.

## Five course practices

The repository was developed in five steps (see `reports/`):

1. **Record definition and dataset schema** — `specs/dataset_schema.json`, `reports/practice_01_record_and_schema.md`
2. **Source map** — `specs/source_map.json`, `reports/practice_02_source_map.md`
3. **PDF extraction** — `specs/pdf_extraction_manifest.json`, `scripts/extract_pdf.py`, `reports/practice_03_pdf_extraction.md`
4. **Web extraction** — `specs/web_extraction_manifest.json`, `scripts/extract_web.py`, `reports/practice_04_web_extraction.md`
5. **Cleaning, normalization and publication** — `specs/cleaning_pipeline.json`, `scripts/build_dataset.py`, `scripts/clean_dataset.py`, `reports/practice_05_cleaning_publication.md`

`reports/final_report.md` and `dataset_card.md` summarize the finished dataset.

## Data pipeline

```text
raw (PDF / web / external)
  → extract (pdf + web scripts) → data/extracted/*.csv
  → build (merge) → data/interim/merged_records.csv
  → clean → data/processed/dataset.csv
  → validate (rules + pytest)
```

Concrete numbers in this project:

- 15 rows from PDF extraction (3 MDPI *Polymers* articles) + 7 367 rows from the LamaLab Zenodo Tg deposit → **7 382 interim rows**
- 14 cleaning steps applied (vocabulary normalization, Tg range check [100, 900] K, missing-SMILES drop, cross-source disagreement flag, schema validation)
- **7 372 rows** in the published dataset, 10 rows dropped with reasons logged in `data/interim/cleaning_drops.csv`
- 6 rows flagged with `cross_source_disagreement` in `notes` (textbook PPO Tg vs. low-MW DOPO-PPO oligomers)

## Final dataset at a glance

| Column | Description |
|--------|-------------|
| `record_id` | Unique row identifier |
| `polymer_name` | Name as given in the source |
| `repeat_unit_smiles` | PSMILES with `[*]` attachment points |
| `polymer_class` | Controlled vocabulary (16 classes incl. `other`) |
| `tg_value` | Raw numeric Tg as reported |
| `tg_unit` | `C` or `K` |
| `tg_std` | Reported uncertainty (same unit as `tg_value`) |
| `measurement_method` | DSC / DMA / TMA / dilatometry / dielectric_spectroscopy / simulation_MD / unknown |
| `source_id` | Foreign key into `specs/source_map.json` |
| `source_type` | paper / supplementary / dataset / aggregator / database / github_repository |
| `doi` | DOI of the source |
| `extraction_method` | manual_pdf / pdf_table_extraction / web_scraping / api_query / dataset_download / manual_aggregator_lookup |
| `notes` | Free text; carries `cross_source_disagreement` flags |

## Required final artifacts

- `data/processed/dataset.csv` aligned with `specs/dataset_schema.json`
- Updated `specs/source_map.json` and extraction manifests
- Practice reports 1–5 and `reports/final_report.md`
- `dataset_card.md`, `LICENSE`, `CITATION.cff`
- Passing validation and tests

## How to run validation

```bash
pip install -r requirements.txt
python scripts/validate_project.py
pytest
```

Expected output: `Validation passed. (0 warning(s))` and `15 passed`.

## How to build the dataset

```bash
python scripts/build_dataset.py    # merge extracts → data/interim/merged_records.csv
python scripts/clean_dataset.py    # normalize and write data/processed/dataset.csv
```

Practices 3 and 4 used the actual extraction scripts:

```bash
python scripts/extract_pdf.py      # PDF extraction (Practice 3)
python scripts/extract_web.py      # web/dataset extraction (Practice 4)
```

## License and citation

- License: **CC-BY-4.0** (see `LICENSE`). Underlying sources retain their own licenses (CC-BY-3.0 / CC-BY-4.0 for MDPI *Polymers*; Zenodo deposit licensed as declared on the record).
- Citation: see `CITATION.cff` (authors, version, repository URL).
- Dataset summary for downstream users: `dataset_card.md`.
