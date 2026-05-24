# Practice 1 — Record definition and dataset schema

## Topic

Polymer Glass Transition Temperature (Tg) Prediction Dataset.

## Scientific task

Collect experimentally reported glass transition temperatures (Tg) for synthetic polymers defined by their SMILES repeat unit, for downstream structure–property modeling and cross-source comparison of Tg values across polymer families.

## One-record definition

**One record** = one experimentally reported Tg measurement for one polymer (defined by its repeat unit SMILES) under specific measurement conditions from one identified source (one row in `data/processed/dataset.csv`).

## Examples of records

| Example | Why it counts |
|---------|----------------|
| Tg = 373 K for polystyrene (CC(c1ccccc1)), Table 1, Chen 2021, DSC, 10 K/min, N2 | Single measurement + SMILES + method + source |
| Tg = 126 °C for conjugated polymer (SMILES: C12=NSN…) from figotj/Polymer_Tg_ GitHub repo | Single measurement + SMILES + identified source |
| Tg = 378 K for PMMA (CC(C)(C(=O)OC)), Fatriansyah 2024, Table 2 | Single measurement + SMILES + source |
| Tg = 354 K for PVC (CC(Cl)), PoLyInfo manual export, DSC | Single measurement + SMILES + method |

## Non-record examples

| Example | Why it is not a record |
|---------|-------------------------|
| "Tg of polystyrene is around 100 °C" (no precise value, no source table) | Vague statement, not a single identified measurement |
| Tg from MD simulation or group-contribution estimation | Not experimental; out of scope |
| Tg range "320–380 K" without a central value | Not a single numeric value |
| Polystyrene Tg without knowing which source reported it | Missing provenance — cannot assign source_id |
| Tg for PS/PMMA blend without composition specified | Composition required for non-pure system |

## Dataset fields

See `specs/dataset_schema.json` for full definitions. Summary:

| Field | Type | Required | Notes |
|-------|-------|----------|--------|
| `record_id` | string | yes | Stable unique ID, e.g. `rec_tg_ps_chen2021_pdf_001` |
| `polymer_name` | string | yes | Name as given in source |
| `repeat_unit_smiles` | string | yes | SMILES with * markers; canonicalize via RDKit |
| `polymer_class` | string | yes | homopolymer / copolymer / conjugated_polymer / other |
| `tg_value` | number | yes | Numeric, in tg_unit |
| `tg_unit` | string | yes | K or C (as reported) |
| `tg_value_K` | number | yes | Normalized to Kelvin for comparison |
| `tg_uncertainty` | number | optional | ±σ if reported |
| `measurement_method` | string | yes | DSC / DMA / dilatometry / TMA / other / unknown |
| `heating_rate_K_min` | number | optional | Typically 10 K/min for DSC |
| `atmosphere` | string | optional | N2 / air / Ar / vacuum |
| `molecular_weight_g_mol` | number | optional | Often absent in ML datasets |
| `mw_type` | string | optional | Mn / Mw — required if Mw present |
| `source_id` | string | yes | Links to source_map.json |
| `source_type` | string | yes | scientific_paper / database / github_repository / … |
| `doi` | string | optional | DOI string when available |
| `conflict_flag` | boolean | optional | True if another source gives Tg differing >10 K |
| `extraction_method` | string | optional | pdf_table / pdf_text_regex / github_payload / … |
| `notes` | string | optional | Curation notes and caveats |

## Ambiguous cases

| Situation | Decision |
|-----------|-------------------------|
| Same polymer measured at different heating rates (5 vs 10 K/min) | Separate records; record heating_rate_K_min in each |
| Tg reported as a range "320–380 K" | Store null in tg_value; note range in notes field |
| Same SMILES in paper and database with different Tg | Keep both records; set conflict_flag = True |
| Plasticized polymer (e.g. PVC + DOP) | Exclude unless plasticizer type and loading fraction both recorded |
| Copolymer with unknown sequence distribution | Include with polymer_class = copolymer; note ambiguity in notes |
| Polymer name given as abbreviation (PS, PMMA) | Expand to full name; store abbreviation in notes |
| Tg reported as "above 300 K" without a number | Exclude; not a numeric value |
