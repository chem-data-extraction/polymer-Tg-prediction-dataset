# Practice 1 — Record definition and dataset schema

> Replace template text with your project decisions. Keep this report aligned with `project.json` and `specs/dataset_schema.json`.

## Topic

Polymer Glass Transition Temperature (Tg) Prediction Dataset.

## Scientific task

Collect experimentally reported glass transition temperatures (Tg) for synthetic polymers defined by their SMILES repeat unit, for downstream structure–property modeling and cross-source comparison of Tg values across polymer families.

## One-record definition

**One record** = one experimentally reported Tg measurement for one polymer (defined by its repeat unit SMILES) under specific measurement conditions from one identified source (one row in `data/processed/dataset.csv`).

## Examples of records

| Example | Why it counts |
|---------|----------------|
| Kd = 0.5 nM for sequence GGTTGGTGTGGTTGG vs thrombin from Table 2 in Green 2018 | Single measurement + sequence + target + source |
| IC50 from supplementary table for one aptamer–lysozyme pair | One numeric binding outcome tied to one pair |

## Non-record examples

| Example | Why it is not a record |
|---------|-------------------------|
| General review paragraph on SELEX without numeric binding data | No measurement |
| Full list of 50 sequences without per-sequence affinity | Not one measurement per row (unless split) |
| Predicted docking score without experimental citation | Out of scope if only experimental data allowed |

## Dataset fields

List each schema field and how you will populate it. Update `specs/dataset_schema.json` when fields change.

## Ambiguous cases

Document decisions here, for example:

- Multiple Kd values for the same aptamer under different buffers → separate records or one record with notes?
- Range reported as “0.1–1 nM” → store null + note, or midpoint?
- Duplicate sequence in paper and database → deduplication rule in Practice 5.
