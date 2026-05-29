# Practice 4 — Web extraction

## Selected web sites

| source_id | page_id | URL |
|---|---|---|
| `ds_zenodo_lamalab_tg` | `zenodo_record_15783761` | `https://zenodo.org/records/15783761` |
| `ds_zenodo_lamalab_tg` | `zenodo_file_lamalab_curated_tg_csv` | `https://zenodo.org/records/15783761/files/LAMALAB_CURATED_Tg_structured_polymerclass_with_embeddings.csv?download=1` |
| `agg_pubchem` | `pubchem_pug_rest_compound_name` | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula/JSON` |

Two `source_id` values, three logical pages: the Zenodo record page provides authoritative metadata (HTML, BeautifulSoup-parsed), the Zenodo file URL provides the bulk CSV (43.6 MB, MD5-verified), and the PubChem REST endpoint resolves monomer canonical SMILES from common names. All three are documented in `specs/web_extraction_manifest.json` under `sources.zenodo` and `sources.pubchem`.

## Why these sites were selected

**Structured data.** Both sources expose machine-readable artefacts directly:
- Zenodo publishes the dataset as a single CSV (LAMALAB's curated Tg dataset, ~7,367 rows) with deterministic column conventions (`PSMILES`, `labels.Exp_Tg(K)`, `meta.polymer`, `meta.polymer_class`, `meta.std`, `meta.source`, `meta.reliability`, `meta.tg_range`, `meta.num_of_points`). No HTML table parsing needed for the data itself; the HTML record page is used only for metadata cross-check.
- PubChem PUG-REST is a documented JSON REST API (`/compound/name/{name}/property/.../JSON`). No HTML, no XPath, no DOM traversal — just GET + `r.json()`.

This is the "API first, HTML second" hierarchy that lecture 3 recommends; both targets are at the top of that hierarchy.

**License.**
- Zenodo dataset: **CC-BY-4.0** (Kunchapu & Jablonka, 2025). Free redistribution and reuse with attribution.
- PubChem PUG-REST: **public domain** (NCBI policy). No restriction on reuse beyond the documented rate limit (5 req/s).

**Complement to PDFs (Practice 3).**

| Aspect | Practice 3 (3 PDFs) | Practice 4 (Zenodo + PubChem) |
|---|---|---|
| Scale | 15 records | ~7,367 records (Zenodo) + 12 monomer SMILES (PubChem) |
| Tg range | 139–436 °C (high-Tg focused) | broad: commodity polymers from ~150 K up to ~700 K |
| Polymer classes | polyimide + polyphenylene oxide | many classes — polyolefin, polyester, polyimide, polyurethane, etc. |
| SMILES | absent in source | curated PSMILES for every Zenodo row |
| Method | DSC / DMA (known, per-paper) | aggregated across multiple methods (`measurement_method = "unknown"`) |

Zenodo dramatically increases coverage; PubChem closes the SMILES gap for the 15 Practice-3 records.

**Update frequency.** Zenodo dataset is versioned (we use **v6**, July 2025); future v7+ releases will appear at the same DOI parent. PubChem updates daily; our 12 monomer queries pull whatever PubChem has at request time. Both are stable enough for reproducibility — the manifest pins the Zenodo version + MD5 hash, and PubChem CIDs are immutable once assigned.

## Page structure

**`zenodo_record_15783761`** — HTML page, InvenioRDM-served.

- One-column layout, server-side rendered.
- No pagination, no infinite scroll, no JavaScript-only content.
- No JSON-LD on the page (despite InvenioRDM's support for it on landing pages — this particular page does not embed `<script type="application/ld+json">`). Metadata is in standard `<meta>` tags (`meta-citation_doi`, `meta-og:title`, `meta-citation_keywords`) and inline HTML text.
- Files section: a `<table>` listing the CSV with name, size, MD5 (text `md5:<hex32>` inside the row) and two `<a>` links (Preview / Download).
- License: text "Creative Commons Attribution 4.0 International" with a CC-BY icon.
- Version: text "Version v6" near the top of the page.
- No iframes, no login wall.

**`zenodo_file_lamalab_curated_tg_csv`** — direct CSV download, not HTML.

- HTTPS GET to the `/files/.../download=1` URL returns `application/csv; charset=utf-8`.
- 43.6 MB; ~7,367 rows × ~4100 columns (most of the width is per-polymer embedding vectors that we drop at the schema-mapping step).

**`pubchem_pug_rest_compound_name`** — JSON REST endpoint.

- Path pattern: `/compound/name/{name}/property/{properties}/JSON` where `{name}` is URL-encoded and `{properties}` is a comma-separated list (`CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula`).
- Response: `{"PropertyTable": {"Properties": [{"CID": ..., "CanonicalSMILES": ..., ...}]}}`.
- 200 on hit, 404 on unknown name. Plain JSON; no HTML, no pagination.
- Documented rate limit: 5 req/s, 400 req/min.

## Extraction methods

**Tooling per source.**

| source_id / page_id | Tool used | Why |
|---|---|---|
| `zenodo_file_lamalab_curated_tg_csv` | `requests.get(url).content` + `hashlib.md5` + `pandas.read_csv` | Direct file download is the cheapest, most reliable path — no HTML parsing risks. MD5 verification ensures bit-exact download. |
| `zenodo_record_15783761` | `requests.get(url).text` + `BeautifulSoup("html.parser")` + a few `re.search()` patterns | The page is small and static; BeautifulSoup is sufficient and pulls metadata cleanly. Used only as a cross-check against the manifest (see "Extracted fields" below). |
| `pubchem_pug_rest_compound_name` | `requests.get(url).json()` | Documented REST API; no need for HTML tooling. |

**Parser plan, as encoded in `specs/web_extraction_manifest.json`.**

The manifest under `sources.zenodo` defines:
- `csv_url`, `expected_md5`, `file_size_mb`, `local_path` — file download contract.
- `expected_key_columns` — the nine Zenodo columns we read; presence is asserted at runtime.
- `column_mapping` — `meta.polymer → polymer_name`, `PSMILES → repeat_unit_smiles`, `meta.polymer_class → polymer_class`, `labels.Exp_Tg(K) → tg_value`, `meta.std → tg_std`, plus several `meta.*` fields collapsed into `notes`.
- `defaults` — constant per-row values: `tg_unit = "K"`, `measurement_method = "unknown"`, `source_id`, `source_type = "dataset"`, `doi`, `extraction_method = "dataset_download"`.

For PubChem the manifest defines `monomer_queries` — 12 entries, each with one or more alternative names to try in order until PubChem returns a hit. For three research-grade compounds (FDAADA, ABTFMB, MABTFMB) the manifest marks `expected_pubchem_status: "likely_not_found"`; the script's `CURATED_MONOMER_TABLE` is the documented fallback.

**Rate limits.**

| Source | Limit | How the script honours it |
|---|---|---|
| Zenodo file | none documented for downloads | single GET per run |
| Zenodo HTML | crawler limits in robots.txt for `*`; documented APIs/files exempt | one GET per run |
| PubChem PUG-REST | 5 req/s, 400 req/min, 300 s aggregate request time per min | `time.sleep(0.25)` between requests; max ~36 requests per run |

User-Agent header `PolymerTg/0.1` is sent on every request, identifying the client cleanly.

**`robots.txt` notes.**

The script runs `urllib.robotparser` against both domains as **step 0** of the pipeline, before any data fetch. Result is saved to `data/extracted/robots_txt_check.json`.

| Domain | Sample URL | `*` allowed? | Interpretation |
|---|---|---|---|
| `zenodo.org` | `/records/15783761/files/.../download=1` | `false` | robots.txt forbids `*` crawling of the site as a whole; downloads of DOI-published files have their own usage terms (CC-BY-4.0). |
| `pubchem.ncbi.nlm.nih.gov` | `/rest/pug/compound/...` | `false` | robots.txt forbids `*` crawling of the HTML site; PUG-REST is documented elsewhere with its own [usage policy](https://pubchem.ncbi.nlm.nih.gov/docs/programmatic-access). |

The script records the technical verdict and continues. The lecture-3 principle of "responsible extraction" is honoured by (a) declaring our User-Agent, (b) rate-limiting, (c) preferring APIs over HTML, (d) logging the robots.txt result for audit.

## Extracted fields

### Zenodo → 13-column schema

| Zenodo column | Schema column | Notes |
|---|---|---|
| `PSMILES` | `repeat_unit_smiles` | Polymer SMILES with `*` markers at chain-extension points |
| `labels.Exp_Tg(K)` | `tg_value` | **Kelvin**; `tg_unit` set to `"K"` |
| `meta.polymer` | `polymer_name` | curated polymer name string |
| `meta.polymer_class` | `polymer_class` | LAMALAB's vocabulary; mapped to `"other"` if blank |
| `meta.std` | `tg_std` | standard deviation across `meta.num_of_points` measurements |
| `meta.source` | `notes` (prefix `source=`) | original literature citation |
| `meta.reliability` | `notes` (prefix `reliability=`) | flag from LAMALAB curation |
| `meta.tg_range` | `notes` (prefix `tg_range=`) | reported Tg range |
| `meta.num_of_points` | `notes` (prefix `n_points=`) | aggregated measurement count |
| *constants set by script* | `tg_unit = "K"`, `measurement_method = "unknown"`, `source_id`, `source_type = "dataset"`, `doi`, `extraction_method = "dataset_download"`, `review_status = "imported_from_zenodo"` | — |

**Hierarchical feature columns** (`fullpolymerlevel.features.*`, `backbonelevel.features.*`, `sidechainlevel.features.*`) and the **4096-dim Llama-3 embedding columns** are **dropped** at this stage — they are not part of our 13-column schema and are recomputable from PSMILES.

### PubChem → `pubchem_lookups.csv`

| PubChem JSON path | Output column | Notes |
|---|---|---|
| `PropertyTable.Properties[0].CID` | `pubchem_cid` | integer; empty if not found |
| `PropertyTable.Properties[0].CanonicalSMILES` | `canonical_smiles` | non-isomeric canonical |
| `PropertyTable.Properties[0].IsomericSMILES` | (parallel field, used for sanity-check) | not exported as a separate column |
| `PropertyTable.Properties[0].IUPACName` | `iupac_name` | full systematic name |
| `PropertyTable.Properties[0].MolecularFormula` | `molecular_formula` | Hill order |

Plus script-set fields: `monomer_label`, `role`, `appears_in_polymers`, `query_used` (which alternative name actually returned a hit), `lookup_status` (`found` / `not_found` / network error), `smiles_source` (`pubchem` / `curated_fallback`), `notes`.

### Zenodo HTML record page → `zenodo_metadata_scraped.json`

BeautifulSoup pass; selectors / patterns:

| DOM hook | Output field | Notes |
|---|---|---|
| `<h1>` text | `title` | Page title |
| `<a href="…doi.org/10.…">` | `doi` | First matching anchor |
| Text match for "CC-BY-4.0" / "Creative Commons Attribution 4.0" | `license` | Pattern set |
| Regex `Version\s+(v\d+(?:\.\d+)*)` on page text | `version` | e.g. `v6` |
| `<a href="*.csv?download=1">` | `file_url`, `file_name` | First match wins |
| Regex `md5:([a-fA-F0-9]{32})` | `md5` | The file row exposes MD5 inline |
| Regex `\((\d+\.?\d*)\s*MB\)` | `file_size_mb` | The file row exposes size inline |

Each scraped field is then diff'd against the manifest's expected value — output in `diff.{field}.match` (`true` / `false` / `null`).

### Manual corrections / cleaning during extraction

- Zenodo rows where `labels.Exp_Tg(K)` is NaN are kept in the mapped CSV (Pydantic validation later flags them).
- Zenodo rows whose `meta.polymer_class` is missing are filled with `"other"` so they validate against the schema's enum.
- PubChem queries are retried with up to three alternative name forms before giving up.
- For the three research-grade diamines (FDAADA, ABTFMB, MABTFMB) that PubChem doesn't index, the curated SMILES from `CURATED_MONOMER_TABLE` is used and flagged `smiles_source = "curated_fallback"` so Practice-5 cleaning can review it.

## Extraction problems

- **`robots.txt` `*`-disallow on both domains.** Technically disallowed for our anonymous User-Agent, but inapplicable to documented file URLs (Zenodo `/files/`) and the PUG-REST API. The script records the verdict and continues — see "robots.txt notes" above.
- **No JSON-LD on the Zenodo page.** Despite InvenioRDM's general support, this specific record page does not include a `<script type="application/ld+json">` block. We fall back to text-based regex / BeautifulSoup `.find()` patterns.
- **Embedding columns inflate the Zenodo CSV.** ~4,100 columns × 7,367 rows; pandas reads in ~5 s. The mapping step keeps only nine of those columns, so the output CSV shrinks ~10× compared with the input.
- **Tg in Kelvin, not Celsius.** Practice 3 records are in °C, Zenodo records are in K. We store both verbatim with `tg_unit` per row; conversion happens in Practice 5 cleaning, never silently at extraction.
- **`measurement_method` aggregated.** LAMALAB does not preserve the per-row measurement method (DSC vs DMA vs TMA) — `measurement_method` is set to `"unknown"` for every Zenodo row. Practice 5 may filter or weight by this where it can be inferred from `meta.source`.
- **PubChem 404 for research-grade compounds.** FDAADA / ABTFMB / MABTFMB don't exist in PubChem; the script logs `lookup_status="not_found"` and falls back to the curated table. SMILES correctness for these three should be re-verified during Practice 5 by RDKit round-trip + comparison with the structural drawings in DOI 10.3390/polym15173549.
- **No login wall, no dynamic content, no markup changes observed.** Both targets are stable, public, and server-side rendered. If Zenodo's HTML layout shifts in a future InvenioRDM release, the BeautifulSoup-scrape step would degrade gracefully: the regex/text patterns are field-specific and miss-soft (returning `null` for unmatched fields), and the diff step would surface mismatches against the manifest immediately.
- **Pydantic-rejected rows (if any).** Logged to `data/extracted/zenodo_validation_errors.csv` with per-row error fields. Common failure modes encountered on the LAMALAB v6 file: blank PSMILES (small handful of rows) and `tg_value` outside the plausible range (0 < Tg < 2000 K).
- **Polyimide PSMILES not auto-assembled.** PubChem gives us monomer SMILES, not polymer PSMILES. The 10 polyimide records in Practice 3 remain `smiles_source = "needs_polymer_assembly"` after Practice 4; the (dianhydride, diamine) SMILES pair is stored on each row, ready for RDKit reaction SMARTS in Practice 5.

## Output files

| Path | Contents |
|---|---|
| `data/raw/lamalab_tg_dataset.csv` | Zenodo CSV, raw, MD5-verified (43.6 MB, ~7,367 rows × ~4,100 cols) |
| `data/raw/web/zenodo_record_15783761.html` | Raw HTML snapshot of the Zenodo record page, taken at scrape time (used as evidence for the BeautifulSoup pass) |
| `data/extracted/robots_txt_check.json` | Step-0 verdict for both domains: robots.txt URL, parsed status, `*`-allowed verdict |
| `data/extracted/zenodo_metadata_scraped.json` | BeautifulSoup-scraped metadata (title / DOI / license / version / MD5 / file size) + per-field diff against the manifest |
| **`data/extracted/ds_zenodo_lamalab_tg.csv`** | **Zenodo rows mapped to the 13-column dataset schema** — ~7,367 records, the `web_extracted_records.csv` equivalent for this project |
| `data/extracted/zenodo_validation_errors.csv` | Pydantic-rejected rows (empty file if all pass) with per-row failing fields and full error payload |
| `data/extracted/pubchem_lookups.csv` | 12 monomer rows: label, role, query used, PubChem CID, canonical SMILES, IUPAC, molecular formula, lookup status, SMILES source |
| `data/extracted/all_papers_table3_filled.csv` | Practice-3 records (15 rows) with `repeat_unit_smiles` populated where possible: 5 textbook PSMILES (DOPO-PPOs), 10 `needs_polymer_assembly` (polyimides — with monomer SMILES stored per row) |
| `data/extracted/extraction_log.jsonl` | Append-only JSONL of every pipeline event: robots.txt verdicts, Zenodo download status, HTML scrape diff, schema-mapping summary, Pydantic validation summary, PubChem lookup per-monomer, fill-Practice-3 strategy counts |

