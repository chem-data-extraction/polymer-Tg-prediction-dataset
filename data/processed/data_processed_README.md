# Processed data

This folder holds the publication-ready Polymer Tg dataset: one row per record,
columns aligned with `specs/dataset_schema.json`.

## Files

- **`dataset.csv`** — final published dataset, 7 372 rows × 13 columns.
  Produced by `scripts/build_dataset.py` (merge of Practice 3 + Practice 4
  extractions) and `scripts/clean_dataset.py` (14-step cleaning pipeline),
  validated with `scripts/validate_project.py` + `pytest`.
- **`dataset_preview.csv`** — stratified 1 000-row preview of `dataset.csv`
  (~240 KB), small enough for GitHub to render as a searchable, sortable
  table. Produced by `scripts/make_preview.py`. The preview is **not**
  a substitute for the full dataset; it is a viewing convenience only.

## Why a separate preview file

GitHub renders CSV/TSV files as interactive tables only when they are under
about 0.5 MB. The full `dataset.csv` is ≈ 1.8 MB, so on its blob page GitHub
shows:

> *We can't make this file beautiful and searchable because it's too large.*

`dataset_preview.csv` solves this by exposing a representative 1 000-row sample
of the same schema. It is deliberately **stratified**, not random:

- all 5 rows from the PDF source (Practice 3)
- all 6 rows flagged with `cross_source_disagreement` in `notes`
- 994 rows randomly sampled from Zenodo (`random_state=42` for reproducibility)
- sorted by `source_type` then `record_id`

so a viewer can immediately see (a) what a PDF-sourced row looks like, (b)
what a Zenodo-sourced row looks like, and (c) the cross-source disagreement
case in the same table.

For analysis or modelling, always use the full `dataset.csv`. The preview
exists only to make the data inspectable in the browser.

## Guidelines

- Regenerate `dataset.csv` from scripts; avoid hand-editing.
  ```bash
  python scripts/build_dataset.py
  python scripts/clean_dataset.py
  ```
- Regenerate `dataset_preview.csv` after every change to `dataset.csv`:
  ```bash
  python scripts/make_preview.py
  ```
- Record the dataset version (or the commit hash that produced it) in
  `reports/final_report.md` and `dataset_card.md`.
- Do not edit `dataset_preview.csv` by hand — it is a derived artefact and
  any manual edits will be overwritten on the next regeneration.
