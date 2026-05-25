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

# scientific_papers (4 sources)

| source_id | citation | DOI | records | license |
|-----------|----------|-----|---------|---------|
| paper_chen_2021 | Chen et al. 2021 | 10.3390/polym13111898 | 12 | CC-BY-4.0 |
| paper_fatriansyah_2024 | Fatriansyah et al. 2024 | 10.3390/polym16172464 | 9 | CC-BY-4.0 |
| paper_uddin_2024 | Uddin & Fan 2024 | 10.3390/polym16081049 | 6 | CC-BY-4.0 |
| paper_rasulev_2024 | Rasulev et al. 2024 | 10.1038/s42004-024-01305-0 | 902 | CC-BY-4.0 |

*paper_chen_2021*, *paper_fatriansyah_2024*, *paper_uddin_2024* — open-access CC BY papers. Training datasets sourced from PoLyInfo — not republished; data available from authors upon request. Extraction targets: benchmark Tg values from tables and body text. Method: `pdf_table` or `pdf_text_regex`.
*paper_rasulev_2024* — the primary bulk source for this project. 902 unique homopolymers with SMILES and experimental Tg assembled independently from public sources and rigorously deduplicated. Published as Supplementary Data 1 (CC BY). Extraction method: `api` (direct download, `pandas.read_csv()`).

# databases (1 source)

| source_id | database | records | access_status |
|-----------|----------|--------------|---------|
| db_polyinfo | PoLyInfo (NIMS) | ~60 000 | registration_required — manual GUI only |

Primary authoritative source of experimentally measured polymer Tg. Automated scraping explicitly prohibited by Terms of Service. Copyright © NIMS. Access via manual GUI export (~50 records per session). Used for gap-filling only.
Note: Polymer Genome was considered but excluded — it is an ML prediction platform, not a database of experimental measurements. GitHub repository `figotj/Polymer_Tg_` was considered but excluded — it contains PoLyInfo data published without NIMS permission; copyright is unclear.

Summarize each group in `source_map.json`:

- scientific_papers
- supplementary_materials
- databases
- aggregators
- github_repositories
- ml_datasets

## Priority sources

Rank sources by reliability, license, and expected yield. Which will you extract first?

## Access conditions

Note paywalls, registration, API keys, and institutional access. Record `access_status`, `access_method`, and `access_date` per source.

## Expected data types

Tables, figures, HTML tables, CSV dumps, API JSON, etc.

## Expected conflicts and overlaps

Example: database Kd may disagree with primary paper — which wins? Document resolution rules.

## Coverage gaps

Targets, assay types, or years missing from your map. Plan follow-up searches or justify exclusions.
