# Practice 1 — Record definition and dataset schema

## Topic

Polymer Glass Transition Temperature (Tg) Prediction Dataset.

## Scientific task

Collect polymers with experimentally measured glass transition temperature (Tg) for downstream use:
compare polymer families and build a structure–property dataset for predicting Tg from molecular or computed descriptors (PSMILES → Tg regression / classification).

## One-record definition

**One record** = one experimentally measured glass transition temperature (Tg) for a single polymer (or repeat unit) reported in a specific source.

Each record is one row in `data/processed/dataset.csv` and contains at minimum:

- the polymer name (as given in the source);
- the repeat-unit SMILES (preferably PSMILES with `[*]` dummy atoms);
- the polymer class (controlled vocabulary);
- the Tg value and its unit;
- the measurement method (DSC / DMA / TMA / dilatometry / dielectric / simulation_MD);
- a pointer to the source (source_id, source_type, DOI when available);
- the extraction method used to obtain the record.

If the same polymer is reported in two different sources, it appears as two records with different source_id; merging across sources happens later in cleaning (Practice 5).

## Examples of records

| Example | Why it counts |
|---------|----------------|
| BTD-HFA polyimide from Pérez-Francisco et al. 2024 (DOI: 10.3390/polym16223188). Repeat-unit PSMILES reconstructed from the BTD dianhydride + HFA diamine pair. polymer_class = polyimide. tg_value = 355, tg_unit = C, measurement_method = DSC (10 °C/min, N₂). source_id = paper_polym16223188, source_type = paper | All required fields present: structure, class, Tg with unit, explicit DSC method, traceable to a DOI'd publication. |
| Poly(2,6-dimethyl-1,4-phenylene oxide) DOPO−Me−PPO from Lu et al. 2024 (DOI: 10.3390/polym16020303). Repeat-unit PSMILES [*]Oc1c(C)cc(C)c1[*] (PPO backbone), DOPO−Me monomer in notes. polymer_class = polyphenylene_oxide. tg_value = 183.2, tg_unit = C, measurement_method = DSC. source_id = paper_polym16020303, source_type = paper | Valid record: polymer name, PSMILES (backbone), class, single experimental Tg with method, source traceable. Side-chain detail goes in notes, not separate columns. |
| A row from ds_zenodo_lamalab_tg (DOI: 10.5281/zenodo.15783761) for poly(methyl methacrylate). PSMILES, Tg, Tg_std, polymer_class taken directly from the CSV; source_id = ds_zenodo_lamalab_tg, source_type = dataset | All required fields populated. Source is a curated public dataset; we keep it as one of many primary inputs. |

## Non-record examples

| Example | Why it is not a record |
|---------|-------------------------|
| BTD-FND polyimide from Pérez-Francisco et al. 2024 — the authors state Tg "could not be determined experimentally (>350 °C, close to onset of decomposition)" and report no numeric value | Required field tg_value is missing (no numeric measurement). The qualitative statement "Tg > 350 °C" is not stored as a value; it would only be retained as a notes-only entry, not a record |
| A review article that mentions "polystyrene typically has Tg around 100 °C" without citing a specific experiment, sample, or method | Required field measurement_method is missing; no source-specific experimental measurement; the value is a textbook estimate, not a measurement |
| A polymer blend (e.g. PS/PMMA blend) reported with a single broad Tg | Record definition is one polymer = one repeat unit; blends are not a single polymer and have no single repeat-unit SMILES |
| A copolymer reported only as "PS-co-PMMA, 70/30" without the exact composition and without a PSMILES specifying both repeat units | Required field repeat_unit_smiles cannot be defined unambiguously for a random copolymer at this level. Excluded; possible inclusion in a future schema version with a copolymer-aware structure |
| A simulated Tg from a molecular-dynamics paper that uses a coarse-grained model with no atomistic mapping to PSMILES | repeat_unit_smiles is undefined for a coarse-grained bead-spring polymer; without a SMILES, the record cannot be used in the structure → Tg ML task. Excluded |

## Dataset fields

See `specs/dataset_schema.json` for full definitions. Summary:

| Field | Type | Required | Notes |
|-------|-------|----------|--------|
| `record_id` | string | yes | Stable unique ID |
| `polymer_name` | string | optional | Name as given in source; expand abbreviations in notes |
| `repeat_unit_smiles` | string | yes | SMILES with * markers; canonicalize via RDKit |
| `polymer_class` | string | yes | Controlled vocabulary: polyimide, polyamide, polyester, polycarbonate, other. Lower snake_case. |
| `tg_value` | number | yes | Numeric, in tg_unit |
| `tg_unit` | string | yes | K or C (as reported); converted to K at cleaning stage |
| `tg_std` | number | optional | ±σ in same unit as tg_value |
| `measurement_method` | string | yes | DSC / DMA / dilatometry / TMA / other / unknown |
| `source_id` | string | yes | Links to entry in specs/source_map.json |
| `source_type` | string | yes | scientific_paper / database / curated_dataset / other |
| `doi` | string | optional | DOI of source when available |
| `extraction_method` | string | optional | pdf_table / pdf_text_regex / manual / api |
| `notes` | string | optional | Free text:  measurement context (heating rate, atmosphere), Mn / PDI when relevant, data-quality flags, ambiguities, conflicts |

## Ambiguous cases

- *Tg reported as a range* (e.g. "Tg = 100–110 °C"). Store the midpoint in tg_value and the half-range in tg_std; record the original range string in notes.
- *Multiple Tg values for the same polymer in the same source* (e.g. first heating vs second heating, or two DSC runs). Keep them as separate records with the same polymer and source, distinguished in notes ("first heating" / "second heating"). Cleaning may average them later, but raw provenance is preserved.
- *Tg given only qualitatively* ("Tg > 350 °C", "Tg below room temperature"). Excluded from the dataset; not a numeric measurement.
- *Different polymer names refer to the same structure* (e.g. "PMMA" vs "poly(methyl methacrylate)"). Keep both records; the canonical key for deduplication is canonicalised repeat_unit_smiles, not polymer_name. Conflicts of polymer_class for the same SMILES are flagged in notes and reconciled in cleaning.
- *Same polymer appears in ds_zenodo_lamalab_tg and in one of the three MDPI papers. Keep both records; the dataset entry will state in its own notes field that it was curated from the primary literature. Duplication is resolved (or explicitly retained with provenance) at the cleaning stage.
- *PSMILES vs. canonical SMILES. The Zenodo dataset stores PSMILES with [*] markers; PubChem returns standard SMILES for monomers. We canonicalise both with RDKit and store the PSMILES form; if attachment points cannot be inferred for a record, the standard SMILES is stored and flagged in notes.
- *Polymer Tg from a copolymer / blend* — excluded at v0.1.0 of the schema (see non-record examples).
