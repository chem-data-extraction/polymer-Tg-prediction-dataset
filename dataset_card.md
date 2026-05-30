# Dataset card — Polymer Tg prediction dataset

## Dataset title

Polymer Tg prediction dataset

## Version

1.0.0 — released after Practice 5 (cleaning, normalization, publication).

## Dataset summary

Tabular collection of experimentally measured polymer glass transition
temperatures (Tg), with each polymer's repeat-unit SMILES, material class,
measurement method, and full provenance (source ID, source type, DOI,
extraction method). 7 372 records combining a small set of manually extracted
records from open-access journal articles and a large-scale public Zenodo
deposit.

## Scientific task

Compare polymer families and build a structure–property dataset for
predicting Tg from molecular or computed descriptors. Each row supports two
typical downstream uses:

1. **Property prediction** — train a regressor on `repeat_unit_smiles` →
   `tg_value` (converting `tg_value` to a common unit using `tg_unit`).
2. **Provenance-aware analysis** — slice by `source_type`, `source_id`,
   `measurement_method`, or `polymer_class` to study how Tg depends on the
   measurement context, not only on chemistry.

## Record unit

One row = one experimentally measured Tg for a single polymer (or repeat
unit) reported in one specific source, together with the measurement context.

## Schema

13 columns, defined in `specs/dataset_schema.json`:

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `record_id` | string | yes | Unique row identifier |
| `polymer_name` | string | optional  | Name as given in the source |
| `repeat_unit_smiles` | string | yes | PSMILES with `[*]` attachment points |
| `polymer_class` | string | yes | Controlled vocabulary (16 classes incl. `other`) |
| `tg_value` | float | yes | Raw numeric Tg as reported |
| `tg_unit` | string | yes | `C` or `K` |
| `tg_std` | float | optional  | Reported uncertainty (same unit as `tg_value`) |
| `measurement_method` | string | yes | DSC / DMA / TMA / dilatometry / dielectric_spectroscopy / simulation_MD / unknown |
| `source_id` | string | yes | Foreign key into `specs/source_map.json` |
| `source_type` | string | yes | paper / supplementary / dataset / aggregator / database / github_repository |
| `doi` | string | optional  | DOI without the `https://doi.org/` prefix |
| `extraction_method` | string | yes | manual_pdf / pdf_table_extraction / web_scraping / api_query / dataset_download / manual_aggregator_lookup |
| `notes` | string | optional  | Free text; carries `cross_source_disagreement` flags and unit/method provenance |

## Data sources

| source_id | type | records | reference |
|-----------|------|---------|-----------|
| `paper_polym16020303` | paper (MDPI CC-BY) | 5 | DOPO-functionalized PPO oligomers |
| `ds_zenodo_lamalab_tg` | dataset (Zenodo) | 7 367 | LamaLab Tg deposit, DOI `10.5281/zenodo.15783761` |

Two further sources (`paper_polym16223188`, `paper_polym15173549`) were
extracted in Practice 3 but their rows are not published in `dataset.csv`
because the polyimide repeat unit was not auto-assembled in Practice 3 (the
schema requires non-empty `repeat_unit_smiles`). Their raw extractions
remain in `data/extracted/all_papers_table3_filled.csv`.

Full source descriptions: `specs/source_map.json`.

## Data extraction procedure

1. **PDF (Practice 3):** manual transcription of Table 3 in each MDPI
   article, guided by `specs/pdf_extraction_manifest.json` and
   `scripts/extract_pdf.py`. Documented in
   `reports/practice_03_pdf_extraction.md`.
2. **Web/dataset (Practice 4):** programmatic download of the Zenodo deposit
   and PubChem monomer lookups, guided by
   `specs/web_extraction_manifest.json` and `scripts/extract_web.py`.
   Documented in `reports/practice_04_web_extraction.md`.

## Data cleaning and normalization

Pipeline declared in `specs/cleaning_pipeline.json`; implemented in
`scripts/clean_dataset.py`. Key normalizations:

- 22 free-text `polymer_class` labels mapped to a 16-class controlled
  vocabulary; unmappable labels become `other` with the original recorded
  in `notes`.
- `tg_value` cast to float; rows with no value are dropped (schema requires
  it). Range check: converted to Kelvin internally, must lie in [100, 900] K.
- `tg_unit` normalized to `C` or `K`. The raw unit is preserved in the
  published table; conversion to a common unit is left to the downstream
  user.
- Rows with empty `repeat_unit_smiles` are dropped.
- Within each SMILES group, if Tg values disagree by more than 20 K (in
  Kelvin) the rows are flagged with `cross_source_disagreement` in `notes`
  but kept. This dataset deliberately preserves measurement variance.
- All `source_id` values are foreign-key checked against
  `specs/source_map.json`.

The result is 7 372 rows from 7 382 interim rows (10 drops). See
`reports/practice_05_cleaning_publication.md` for a step-by-step accounting.

## Validation

`scripts/validate_project.py` and `tests/test_required_artifacts.py` enforce
the schema, vocabularies, foreign keys, and tg range. Validation passes with
no errors or warnings.

## Known limitations

- The five surviving PDF records are all PPO chemistry — coverage of the
  "papers" stratum is narrow. Polyimide records can be recovered once
  repeat-unit assembly from monomer SMILES is implemented.
- `measurement_method` is `unknown` for 7 367/7 372 rows (99.9 %), because
  the Zenodo deposit does not record per-record method. The five DSC rows
  come from the PDF source.
- The same repeat-unit SMILES (PPO) shows substantial Tg variance across
  sources (412–485 K, 73 K spread) due to molecular-weight and end-group
  effects; flagged but not aggregated.
- License compatibility checked but not verified by legal counsel.

## Recommended use

- **Allowed:** academic reuse with attribution under CC-BY-4.0; redistribution
  with citation; modification (e.g. adding canonical SMILES via RDKit,
  recomputing in K, joining with computed descriptors).
- **Recommended workflow:** load `data/processed/dataset.csv`, optionally
  compute `tg_K = tg_value if tg_unit=='K' else tg_value + 273.15`, filter or
  weight by `source_id` / `measurement_method`, then featurize
  `repeat_unit_smiles` with RDKit or any polymer-aware encoder.

## Citation

See `CITATION.cff` in the repository root.

## License

CC-BY-4.0 (see `LICENSE`).
