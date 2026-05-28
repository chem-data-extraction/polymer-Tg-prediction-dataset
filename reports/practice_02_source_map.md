# Practice 2 — Source map

The machine-readable source map is in `specs/source_map.json`.
This report explains the search strategy, source groups, priorities, access conditions, expected data types, overlaps/conflicts, and known coverage gaps.

## Source search strategy

*Primary literature*: MDPI Polymers journal (open access, CC-BY licenses; permissive reuse). Selected three articles that explicitly report Tg from DSC for well-defined polymer structures.

*Datasets*: Zenodo search for "polymer glass transition temperature" filtered by Dataset resource type and open license. The LAMALAB curated dataset (Friedrich Schiller University Jena) is the main bulk source.

*Aggregator*: PubChem — used as a name → structure resolver, not as a Tg source.

*Keywords for the seed search*:
- "polymer Tg", "glass transition temperature", "DSC polymer", "polyimide Tg", "poly(phenylene oxide) Tg";
- "PSMILES", "polymer SMILES dataset";
- polymer classes from the controlled vocabulary (polyimide, polyamide, polyester, …).

## Source groups

*scientific_papers (3 sources)*

| source_id | reference | DOI | records | license |
|-----------|----------|-----|---------|---------|
| paper_polym16223188 | Pérez-Francisco et al., Polymers 2024, 16(22), 3188 — rigid alicyclic BTD polyimides | 10.3390/polym16223188 | 4 | CC-BY-4.0 |
| paper_polym15173549 | Ren et al., Polymers 2023, 15(17), 3549 — fluorene-containing polyimides with amide-bridged diamines | 10.3390/polym15173549 | 6 | CC-BY-4.0 |
| paper_polym16020303 | Lu et al., Polymers 2024, 16(2), 303 — DOPO-containing poly(2,6-dimethyl-1,4-phenylene oxide)s | 10.3390/polym16020303 | 5 | CC-BY-4.0 |

The three papers were chosen to give diversity in Tg range and polymer class: low-/mid-Tg PPO derivatives (~150–185 °C), mid-/high-Tg BTD polyimides (~270–360 °C), and very-high-Tg fluorene-containing polyimides (> 400 °C). Together they span ~250 °C of the Tg axis with three different chemistries, which is useful for validating the dataset's coverage at the extremes.

*aggregators (1 source)*

| source_id | service | purpose |
|-----------|----------|--------------|
| agg_pubchem_api | PubChem PUG-REST API | polymer name → canonical SMILES — identifier resolution only, no Tg |

*datasets (1 source)*

| source_id | URL | records | use |
|-----------|----------|---------|-----|
| ds_zenodo_lamalab_tg | https://zenodo.org/records/15783761 | ~1000 | primary data source |

Curated dataset with PSMILES, Tg values, reliability scores, standard deviation, and polymer class labels. Used as a primary data source. Check provenance column per record — if data originates from PoLyInfo or another database, cite the original source in addition to the Zenodo record.

*GitHub repositories / ML datasets / databases*
Currently empty. Candidates for future versions: PoLyInfo, PolymerGenome / PolymRetrival / PolyMetriX (the GitHub project linked from the Zenodo record).

## Priority sources

| priority | source_id | reason |
|-----------|----------|--------------|
| 1 | ds_zenodo_lamalab_tg | ~1000 records, direct CSV, open, with polymer class labels |
| 2 | paper_polym16020303 | Five DOPO-PPO records, fills the 150–185 °C Tg range with polymer_class |
| 3 | paper_polym16223188 |  Four BTD-polyimide records, fills the 270–360 °C range with polymer_class |
| 4 | paper_polym15173549 | ~6 fluorene-polyimide records, fills the > 400 °C tail |
| 5 | agg_pubchem_api | Identifier resolution only — no Tg |

## Access conditions

| source_id | terms of service  | extraction_method | data available |
|-----------|----------|---------|-----|
| paper_polym16020303 | CC BY — free use  | pdf_table | Table 1 — 5 records |
| paper_polym16223188 | CC BY — free use  | pdf_table | Table 3 — 4 records |
| paper_polym15173549 | CC BY — free use  | pdf_table | Table 3 — 6 records |
| agg_pubchem_api | public domain  | api | SMILES only |
| ds_zenodo_lamalab_tg | open  | api (pandas.read_csv) | Full CSV download |

## Expected data types per source

| source_id | format | fields available in schema |
|-----------|----------|--------------|
| paper_polym16223188 | PDF | polymer_name, tg_value, tg_unit, measurement_method |
| paper_polym15173549 | PDF | polymer_name, tg_value, tg_unit, measurement_method |
| paper_polym16020303 | PDF | polymer_name, tg_value, tg_unit |
| agg_pubchem_api | JSON | repeat_unit_smiles only |
| ds_zenodo_lamalab_tg | CSV | repeat_unit_smiles, tg_value, tg_unit, polymer_class |


## Expected conflicts and overlaps

1. *Conflict: same polymer, different Tg values across two sources.*
    E.g. PMMA Tg reported as 105 °C in one row and 110 °C in another.
    Resolution: keep both records (different source_id). Cleaning step may compute a per-SMILES mean and stddev as an aggregated view, but the raw rows are never      overwritten.
2. *Conflict: different polymer_class mappings for the same SMILES.*
    E.g. a DOPO-modified PPO could be classified by one author as polyphenylene_oxide and by another as flame_retardant_polymer.
    Resolution: enforce the controlled vocabulary in specs/dataset_schema.json; if a source value does not fit, map to the closest term and flag the original   label in notes.
    The schema vocabulary is chemistry-based (backbone family), not application-based, so flame-retardant variants of PPO still get polyphenylene_oxide.
3. *Conflict: unit mismatch (°C vs K).*
    tg_unit is preserved per-record; conversion to K is computed in the cleaning step (scripts/clean_dataset.py). No silent in-place conversion.
4. *Conflict: PSMILES vs. plain SMILES.*
    The Zenodo dataset uses PSMILES ([*] markers); papers rarely give explicit SMILES, so SMILES are reconstructed from the depicted repeat unit. After RDKit   canonicalisation, both forms are stored as PSMILES where possible; flag in notes if attachment points are ambiguous.

## Coverage gaps

1. Quantify Tg-axis and polymer-class coverage at the end of Practice 5 (histograms in reports/final_report.md).
2. If polyolefin / polysiloxane / elastomer counts < 20 records, add a targeted paper search for those classes in a future v0.X.0.
3. Re-run the full pipeline whenever a new Zenodo version of ds_zenodo_lamalab_tg is published.
