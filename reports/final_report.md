# Final report — Polymer Tg prediction dataset
## Project summary

**Title:** Polymer Tg prediction dataset

**Version:** 1.0.0 (Practice 5 completed)

**Repository:** https://github.com/chem-data-extraction/polymer-Tg-prediction-dataset

**License:** CC-BY-4.0

**Citation:** see `CITATION.cff`

The dataset contains experimentally measured glass transition temperatures
(Tg) of polymers, together with each polymer's structure (repeat unit SMILES),
material class, measurement method, and provenance. It is intended for
comparing polymer families and for building structure–property models that
predict Tg from molecular or computed descriptors.

## Dataset goal

Provide a single, schema-validated table that joins (a) a small, curated set
of Tg values manually extracted from open-access MDPI *Polymers* papers, with
(b) a large-scale Tg corpus from the LamaLab Zenodo dataset, so the two can
be inspected, compared, and used together in downstream ML pipelines.

Intended audience: students and researchers in polymer informatics, materials
science, and cheminformatics who need a small, transparent, reproducible
starting point with end-to-end provenance.

## Source summary

| source_id | source_type | License | Records in this dataset |
|-----------|-------------|---------|------------------------|
| `paper_polym16020303` (Lecoeur et al., DOPO-PPO) | paper | CC-BY-3.0 | 5 |
| `paper_polym16223188` (Pérez-Francisco, BTD polyimides) | paper | CC-BY-3.0 | 0 (extracted but dropped: SMILES not resolved) |
| `paper_polym15173549` (Ren, FLPI polyimides) | paper | CC-BY-4.0 | 0 (extracted but dropped: SMILES not resolved) |
| `ds_zenodo_lamalab_tg` (LamaLab Zenodo) | dataset | CC-BY (Zenodo deposit) | 7 367 |
| `agg_pubchem` (PubChem PUG-REST) | aggregator | public-domain facts | 0 (reference only, monomer lookup) |
Full source descriptions: `specs/source_map.json`.

## Extraction summary

- **Practice 3 (PDF):** manual extraction of Table 3 from each of three MDPI
  *Polymers* articles → 15 records. Output:
  `data/extracted/all_papers_table3_filled.csv`. Detailed in
  `reports/practice_03_pdf_extraction.md`.
- **Practice 4 (web/dataset):** download of the LamaLab Zenodo deposit
  (`10.5281/zenodo.15783761`) plus PubChem PUG-REST lookups for the
  monomer/end-group identities used in the PDF papers → 7 367 records.
  Output: `data/extracted/ds_zenodo_lamalab_tg.csv` and
  `data/extracted/pubchem_lookups.csv`. Detailed in
  `reports/practice_04_web_extraction.md`.

## Cleaning and normalization summary

Pipeline declared in `specs/cleaning_pipeline.json` and executed by
`scripts/build_dataset.py` + `scripts/clean_dataset.py`.

- 7 382 interim rows → **7 372 published rows**
- 10 rows dropped (1 missing Tg, 9 missing SMILES) — see
  `data/interim/cleaning_drops.csv`
- 6 rows flagged with `cross_source_disagreement` (PPO low-MW oligomers from
  the PDF source vs. the textbook high-MW PPO entry in Zenodo)
- Controlled vocabularies enforced for `polymer_class`, `tg_unit`,
  `measurement_method`, `source_type`, `extraction_method`

Details in `reports/practice_05_cleaning_publication.md`.

## Validation summary

```
$ python scripts/validate_project.py
Validation passed. (0 warning(s))

$ pytest
15 passed in 0.92s
```

15 pytest checks cover required files, JSON parsability, schema column match,
record_id uniqueness, source_id foreign keys, controlled vocabularies, Tg
numeric range, non-empty SMILES, and the combined-source composition.

## Limitations

1. **Polyimide repeat units not assembled.** Nine of the fifteen PDF records
   (the BTD and FLPI polyimide series) carry monomer SMILES but no assembled
   repeat unit. Practice 5 deliberately drops them rather than emit
   schema-violating rows; recovering them requires RDKit-based imide
   construction from a dianhydride + diamine pair.
2. **Measurement method is `unknown` for the Zenodo subset (7 367 rows).**
   The upstream deposit does not record per-record method; downstream models
   should either treat this column as a categorical and learn its effect, or
   filter to the 5 DSC-labeled records when method is critical.
3. **Cross-source duplicates of the same SMILES are kept, not merged.** Tg
   legitimately varies with method, heating rate, molecular weight and
   tacticity. Aggregation is left to the downstream user.
4. **The five surviving PDF records are all PPO.** This means the published
   dataset's "papers" stratum is dominated by one chemistry class. Mitigated
   by re-running the pipeline once polyimide assembly is added (planned
   follow-up).
5. **License compatibility checked but not verified by counsel.** All
   underlying sources are open (Zenodo deposit + MDPI CC-BY); the published
   dataset is released as CC-BY-4.0 under the principle that numeric
   measurements are facts.

## Final artifacts

| Artifact | Path |
|----------|------|
| Processed dataset | `data/processed/dataset.csv` |
| Interim merged table | `data/interim/merged_records.csv` |
| Drop log | `data/interim/cleaning_drops.csv` |
| Cleaning summary | `data/interim/cleaning_summary.txt` |
| Dataset schema | `specs/dataset_schema.json` |
| Source map | `specs/source_map.json` |
| Cleaning pipeline spec | `specs/cleaning_pipeline.json` |
| Validation rules | `specs/validation_rules.json` |
| Build script | `scripts/build_dataset.py` |
| Clean script | `scripts/clean_dataset.py` |
| Validation script | `scripts/validate_project.py` |
| Tests | `tests/test_required_artifacts.py` |
| Practice 1–5 reports | `reports/practice_0{1..5}_*.md` |
| Dataset card | `dataset_card.md` |
| Citation | `CITATION.cff` |
| License | `LICENSE` |
| Colab verification notebook | `notebooks/practice_05_colab.ipynb` |

## How to reproduce
```
git clone https://github.com/chem-data-extraction/polymer-Tg-prediction-dataset.git
cd polymer-Tg-prediction-dataset
pip install -r requirements.txt
python scripts/build_dataset.py
python scripts/clean_dataset.py
python scripts/validate_project.py
pytest
```
