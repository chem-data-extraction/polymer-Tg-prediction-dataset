# Practice 2 — Source map

## Source search strategy

*Keywords used:* `polymer glass transition temperature Tg DSC experimental SMILES repeat unit`, `polymer Tg dataset machine learning prediction structure property`, `polymer Tg homopolymer supplementary data open access CC-BY`

*Platforms searched:*

- Google Scholar — primary literature
- MDPI Polymers — open-access papers with supplementary data
- Nature Communications Chemistry — curated polymer datasets
- Zenodo — curated open datasets
- PoLyInfo web interface — database scope and ToS review

*Snowballing:* Chen 2021 → PoLyInfo (primary experimental database). Uddin 2024 → Liu et al. KDD 2022 (original 7174-polymer dataset, PoLyInfo-based). Rasulev 2024 found via Google Scholar keyword search as independent curated source. Abdulhamid 2022 and Wang 2023 found by filtering MDPI Polymers synthesis papers with documented DSC/DMA tables.

## Source groups

*scientific_papers (6 sources)*

| source_id | citation | DOI | records | license |
|-----------|----------|-----|---------|---------|
| paper_chen_2021 | Chen et al. 2021 | 10.3390/polym13111898 | 12 | CC-BY-4.0 |
| paper_fatriansyah_2024 | Fatriansyah et al. 2024 | 10.3390/polym16172464 | 9 | CC-BY-4.0 |
| paper_uddin_2024 | Uddin & Fan 2024 | 10.3390/polym16081049 | 6 | CC-BY-4.0 |
| paper_rasulev_2024 | Rasulev et al. 2024 | 10.1038/s42004-024-01305-0 | 902 | CC-BY-4.0 |
| paper_abdulhamid_2022 | Abdulhamid et al. 2022 | 10.3390/polym14091888 | 5 | CC-BY-4.0 |
| paper_wang_2023 | Wang et al. 2023 | 10.3390/polym15173549 | 4 | CC-BY-4.0 |

*paper_rasulev_2024* — primary bulk source. 902 unique homopolymers with SMILES and experimental Tg, independently assembled and deduplicated from public sources. Supplementary Data 1 is a direct download from the Nature journal page.

*paper_chen_2021*, *paper_fatriansyah_2024*, *paper_uddin_2024* — CC BY papers. Full datasets from PoLyInfo not republished. Only benchmark values from tables and body text are extractable directly from the PDF.

*paper_abdulhamid_2022*, *paper_wang_2023* — experimental synthesis papers with full measurement conditions documented (DSC or DMA, 10 °C/min, N2). Polyimide class with high Tg (336–693 K). SMILES derived from structural formulas.

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

*datasets (1 source)*

| source_id | URL | records | use |
|-----------|----------|---------|-----|
| ds_zenodo_lamalab_tg | https://zenodo.org/records/15783761 | ~1000 | primary data source |

Curated dataset with PSMILES, Tg values, reliability scores, standard deviation, and polymer class labels. Used as a primary data source. Check provenance column per record — if data originates from PoLyInfo or another database, cite the original source in addition to the Zenodo record.

## Priority sources

| priority | source_id | reason |
|-----------|----------|--------------|
| 1 | paper_rasulev_2024 | 902 records, CC BY, direct CSV download, independently curated |
| 1 | ds_zenodo_lamalab_tg | ~1000 records, direct CSV, open, with polymer class labels |
| 2 | paper_chen_2021 | 12 SMILES + Tg from Table 1, CC BY, pdf_table |
| 2 | paper_abdulhamid_2022 | 5 records, full conditions documented, polyimide class |
| 2 | paper_wang_2023 | 4 records, full conditions documented, polyimide class |
| 2 | paper_fatriansyah_2024 | Benchmark Tg values in body text, CC BY |
| 2 | paper_uddin_2024 | Cross-source Tg comparison Table 3, CC BY |
| 3 | db_polyinfo | High quality, primary source — manual export for gap-filling |
| 4 | agg_pubchem_api | Identifier resolution only — no Tg |

## Access conditions

| source_id | terms of service  | extraction_method | data available |
|-----------|----------|---------|-----|
| paper_chen_2021 | CC BY — free use  | pdf_table | Table 1 — 12 records |
| paper_fatriansyah_2024 | CC BY — free use  | pdf_text_regex | Inline values; full dataset from authors |
| paper_uddin_2024 | CC BY — free use  | pdf_table | Table 3 — 6 records |
| paper_rasulev_2024 | CC BY — free use  | api (supplementary download) | Supplementary Data 1 — 902 records |
| paper_abdulhamid_2022 | CC BY — free use  | pdf_table | Table 2 — 5 records, conditions documented |
| paper_wang_2023 | CC BY — free use  | pdf_table | Table 3 — 4 records, conditions documented |
| db_polyinfo | parsing prohibited  | manual | Manual export ~50 records/session |
| agg_pubchem_api | public domain  | api | SMILES only |
| ds_zenodo_lamalab_tg | open  | api (pandas.read_csv) | Full CSV download |

## Expected data types per source

| source_id | format | fields available in schema |
|-----------|----------|--------------|
| paper_chen_2021 | PDF | polymer_name, repeat_unit_smiles, tg_value, tg_unit, measurement_method |
| paper_fatriansyah_2024 | PDF | polymer_name, tg_value, tg_unit, measurement_method |
| paper_uddin_2024 | PDF | polymer_name, tg_value, tg_unit |
| paper_rasulev_2024 | supplementary CSV | polymer_name, repeat_unit_smiles, tg_value, tg_unit |
| paper_abdulhamid_2022 | PDF | polymer_name, tg_value, tg_unit, measurement_method, heating_rate_K_min, atmosphere |
| paper_wang_2023 | PDF | polymer_name, tg_value, tg_unit, measurement_method |
| db_polyinfo | Web GUI | polymer_name, repeat_unit_smiles, tg_value, tg_unit, measurement_method, heating_rate_K_min |
| agg_pubchem_api | JSON | repeat_unit_smiles only |
| ds_zenodo_lamalab_tg | CSV | repeat_unit_smiles, tg_value, tg_unit, polymer_class |

Fields not covered by any automated source: molecular_weight_g_mol, atmosphere (except Abdulhamid 2022 and PoLyInfo manual export).

## Expected conflicts and overlaps

| overlap | sources | resolution rule |
|-----------|----------|--------------|
| benchmark polymers (PS, PMMA, PC) appear in multiple sources | paper_rasulev_2024 + paper_chen_2021 + ds_zenodo_lamalab_tg | both records kept; conflict_flag = True if delta > 10 K |
| ds_zenodo_lamalab_tg may include data from PoLyInfo or Rasulev 2024 | ds_zenodo_lamalab_tg + db_polyinfo / paper_rasulev_2024 | check provenance column; cite original; both records kept |
| paper values vs PoLyInfo for same polymer | paper_* + db_polyinfo | paper preferred when measurement conditions are documented |
| DMA vs DSC for same polymer | paper_wang_2023 + any DSC source | both records kept; measurement_method field distinguishes them |
| high-Tg polyimide reported as limit "Tg > 420 °C" | paper_wang_2023 | store with tg_relation = ">", tg_limit_value = 420, tg_value = null |
| any two sources, same SMILES, delta > 10 K | any | conflict_flag = True; resolution in Practice 5 |

## Coverage gaps

| gap | reason | plan |
|-----------|----------|--------------|
| molecular_weight_g_mol | Absent in all automated sources | Optional field; fill from PoLyInfo manual export where possible |
| heating_rate_K_min per record | In paper methods section only, not per table row | Assign from methods section; note as inferred in notes field |
| atmosphere per record | Rarely stated per row | Assign from methods section where confirmed (e.g. Abdulhamid 2022 — N2) |
| fluoropolymers (PTFE, PVDF) | Underrepresented in open sources | PoLyInfo manual export for gap-filling |
| copolymer composition series | Not compiled systematically | Out of scope for v0.1.0; noted as limitation |
