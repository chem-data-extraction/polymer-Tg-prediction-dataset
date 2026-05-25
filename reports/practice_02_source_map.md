# Practice 2 — Source map

## Source search strategy

*Keywords used:* `polymer glass transition temperature Tg DSC experimental SMILES repeat unit`, `polymer Tg dataset machine learning prediction structure property`, `polymer Tg homopolymer supplementary data open access CC-BY`

*Platforms searched:*

- Google Scholar — primary literature
- MDPI Polymers — open-access papers with supplementary data
- Nature Communications Chemistry — curated polymer datasets
- Zenodo — curated open datasets
- PoLyInfo web interface — database scope and ToS review

*Snowballing:* References of Chen 2021 and Uddin 2024 led to PoLyInfo as the primary experimental database. Rasulev 2024 (Communications Chemistry) found via Google Scholar as an independent curated source.

## Source groups

*scientific_papers (4 sources)*

| source_id | citation | DOI | records | license |
|-----------|----------|-----|---------|---------|
| paper_chen_2021 | Chen et al. 2021 | 10.3390/polym13111898 | 12 | CC-BY-4.0 |
| paper_fatriansyah_2024 | Fatriansyah et al. 2024 | 10.3390/polym16172464 | 9 | CC-BY-4.0 |
| paper_uddin_2024 | Uddin & Fan 2024 | 10.3390/polym16081049 | 6 | CC-BY-4.0 |
| paper_rasulev_2024 | Rasulev et al. 2024 | 10.1038/s42004-024-01305-0 | 902 | CC-BY-4.0 |

*paper_chen_2021*, *paper_fatriansyah_2024*, *paper_uddin_2024* — open-access CC BY papers. Training datasets sourced from PoLyInfo — not republished; data available from authors upon request. Extraction targets: benchmark Tg values from tables and body text. Method: `pdf_table` or `pdf_text_regex`.
*paper_rasulev_2024* — the primary bulk source for this project. 902 unique homopolymers with SMILES and experimental Tg assembled independently from public sources and rigorously deduplicated. Published as Supplementary Data 1 (CC BY). Extraction method: `api` (direct download, `pandas.read_csv()`).

*databases (1 source)*

| source_id | database | records | access_status |
|-----------|----------|--------------|---------|
| db_polyinfo | PoLyInfo (NIMS) | ~60 000 | registration_required — manual GUI only |

Primary authoritative source of experimentally measured polymer Tg. Automated scraping explicitly prohibited by Terms of Service. Copyright © NIMS. Access via manual GUI export (~50 records per session). Used for gap-filling only.
Note: Polymer Genome was considered but excluded — it is an ML prediction platform, not a database of experimental measurements. GitHub repository `figotj/Polymer_Tg_` was considered but excluded — it contains PoLyInfo data published without NIMS permission; copyright is unclear.

*aggregators (1 source)*

| source_id | service | purpose |
|-----------|----------|--------------|
| agg_pubchem_api | PubChem PUG-REST API | polymer name → canonical SMILES — identifier resolution only, no Tg |

*ml_datasets (1 source)*

| source_id | URL | records | use |
|-----------|----------|---------|-----|
| ml_zenodo_lamalab_tg | https://zenodo.org/records/15783761 | ~1000 | cross-validation |

## Priority sources

| priority | source_id | reason |
|-----------|----------|--------------|
| 1 | paper_rasulev_2024 | 902 records, CC BY, Supplementary Data 1, independently curated |
| 2 | paper_chen_2021 | 12 SMILES + Tg benchmark records from Table 1, CC BY |
| 2 | paper_fatriansyah_2024 | Benchmark Tg values in body text, CC BY |
| 2 | paper_uddin_2024 | Cross-source Tg comparison Table 3, CC BY |
| 3 | db_polyinfo | High quality, primary source — manual export for gap-filling |
| 4 | agg_pubchem_api | Identifier resolution only — no Tg |
| 4 | ml_zenodo_lamalab_tg | Cross-validation |

## Access conditions

| source_id | terms of service  | extraction_method | data available |
|-----------|----------|---------|-----|
| paper_chen_2021 | CC BY — free use  | pdf_table | Table 1 only (12 records); full dataset from authors |
| paper_fatriansyah_2024 | CC BY — free use  | pdf_text_regex | Inline values only; full dataset from authors |
| paper_uddin_2024 | CC BY — free use  | pdf_table | Table 3 only (6 records); full dataset from authors |
| paper_rasulev_2024 | CC BY — free use  | api (supplementary download) | Supplementary Data 1 — 902 records |
| db_polyinfo | parsing prohibited  | manual | Manual export ~50 records/session |
| agg_pubchem_api | public domain  | api | SMILES only |
| ml_zenodo_lamalab_tg | open  | api (pandas.read_csv) | Full CSV download |

## Expected data types

| source_id | format | fields available in schema |
|-----------|----------|--------------|
| paper_chen_2021 | PDF | polymer_name, repeat_unit_smiles, tg_value, tg_unit, measurement_method |
| paper_fatriansyah_2024 | PDF | polymer_name, tg_value, tg_unit, measurement_method |
| paper_uddin_2024 | PDF | polymer_name, tg_value, tg_unit |
| paper_rasulev_2024 | supplementary CSV/XLSX | polymer_name, repeat_unit_smiles, tg_value, tg_unit |
| db_polyinfo | Web GUI | polymer_name, repeat_unit_smiles, tg_value, tg_unit, measurement_method, heating_rate_K_min |
| agg_pubchem_api | JSON | repeat_unit_smiles only |
| ml_zenodo_lamalab_tg | CSV | repeat_unit_smiles, tg_value, tg_unit |

Fields not covered by any automated source: `molecular_weight_g_mol`, `atmosphere`, `heating_rate_K_min` (except PoLyInfo manual ). These remain optional in the schema.

## Expected conflicts and overlaps

| overlap | sources | resolution rule |
|-----------|----------|--------------|
| paper_rasulev_2024 and paper_chen_2021 share benchmark polymers (PS, PMMA, etc.) | paper_rasulev_2024 + paper_* | Both records kept; set conflict_flag = True if delta > 10 K |

| LAMALAB_CURATED_Tg_structured_polymerclass dataset overlap with Rasulev 2024 | ml_zenodo_lamalab_tg + paper_rasulev_2024 | Use Rasulev as authoritative; LamaLab for cross-validation only |
| Same polymer in papers and PoLyInfo | paper_* + db_polyinfo | Paper value preferred when measurement conditions are documented |
| Two sources report different Tg for same SMILES | any | Keep both records; set conflict_flag = True if delta > 10 K |


## Coverage gaps

| gap | reason | plan |
|-----------|----------|--------------|
| molecular_weight_g_mol | Absent in all automated sources | Accept as missing; mw_type = null |
| heating_rate_K_min per record | Only in paper methods sections, not per row | Assign from methods section; note as inferred |
| atmosphere per record | Rarely stated per row | Assign from methods section where confirmed |
| fluoropolymers, high-Tg engineering polymers | Underrepresented in open sources | PoLyInfo manual export for targeted gap-filling |
| copolymer composition series | Not compiled systematically | Out of scope for v0.1.0; noted as limitation |
