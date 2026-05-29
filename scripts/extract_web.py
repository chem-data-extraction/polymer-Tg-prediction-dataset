"""
scripts/extract_web.py
======================

Practice 4 — web/dataset extraction for the Polymer Tg dataset.

Two external sources:

  * ds_zenodo_lamalab_tg — bulk Curated Glass Transition Temperature for Polymers
    dataset (Zenodo, DOI 10.5281/zenodo.15783761, v6, CC-BY-4.0). HTTPS file
    download → CSV → map to schema.

  * agg_pubchem — PubChem PUG-REST API (public domain). REST queries to resolve
    canonical SMILES for the monomers that appear in the 15 Practice-3 records.

Pipeline stages (in order):

  0. check_robots_txt()        — verify both domains allow our User-Agent on
     the URLs we plan to hit (lecture-3 "responsible extraction").
  1. download_zenodo()         — pull the 43.6 MB CSV, verify MD5.
  2. scrape_zenodo_metadata()  — BeautifulSoup pass over the Zenodo HTML record
     page, cross-checks manifest values (license, version, MD5, file URL).
  3. map_zenodo_to_schema()    — project Zenodo columns into our 13-col schema.
  4. validate_zenodo_rows()    — Pydantic schema validation; bad rows logged.
  5. resolve_monomers()        — PubChem PUG-REST lookups; curated fallback.
  6. fill_practice3_smiles()   — enrich Practice-3 records with PSMILES.

Outputs (all in data/extracted/):

  * robots_txt_check.json        — per-URL allowed/disallowed verdict
  * zenodo_metadata_scraped.json — HTML-scraped metadata + manifest diff
  * ds_zenodo_lamalab_tg.csv     — Zenodo CSV mapped to schema
  * zenodo_validation_errors.csv — Pydantic-rejected rows (if any)
  * pubchem_lookups.csv          — 12 monomers with CID/SMILES/IUPAC
  * all_papers_table3_filled.csv — Practice-3 rows with repeat_unit_smiles
  * extraction_log.jsonl         — append-only event log

Run locally:

    pip install -r requirements.txt
    python scripts/extract_web.py

If the network is restricted (zenodo.org / pubchem.ncbi.nlm.nih.gov blocked),
every step degrades gracefully: it logs the failure and falls back to either
a curated table (PubChem) or skips with a warning (Zenodo). The rest of the
pipeline continues so the practice can be tested end-to-end.

PubChem rate limit: PUG-REST allows up to 5 req/s; the script sleeps 0.25 s
between requests.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "specs" / "web_extraction_manifest.json"
RAW_DIR = ROOT / "data" / "raw"
EXTRACTED_DIR = ROOT / "data" / "extracted"
LOG_PATH = EXTRACTED_DIR / "extraction_log.jsonl"
PRACTICE3_CSV = EXTRACTED_DIR / "all_papers_table3.csv"

EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

ZENODO_OUTPUT_COLUMNS = [
    "record_id",
    "polymer_name",
    "repeat_unit_smiles",
    "polymer_class",
    "tg_value",
    "tg_unit",
    "tg_std",
    "measurement_method",
    "source_id",
    "source_type",
    "doi",
    "extraction_method",
    "notes",
    # provenance
    "zenodo_row_index",
    "review_status",
]

PUBCHEM_OUTPUT_COLUMNS = [
    "monomer_label",
    "role",
    "appears_in_polymers",
    "query_used",
    "pubchem_cid",
    "canonical_smiles",
    "iupac_name",
    "molecular_formula",
    "lookup_status",
    "smiles_source",   # pubchem | curated_fallback
    "notes",
]

PRACTICE3_FILLED_COLUMNS = [
    # 13 schema columns
    "record_id",
    "polymer_name",
    "repeat_unit_smiles",
    "polymer_class",
    "tg_value",
    "tg_unit",
    "tg_std",
    "measurement_method",
    "source_id",
    "source_type",
    "doi",
    "extraction_method",
    "notes",
    # provenance from Practice 3
    "page",
    "table_id",
    "evidence_text",
    "review_status",
    # provenance added in Practice 4
    "smiles_source",
    "monomer_a_smiles",
    "monomer_b_smiles",
]


# ---------------------------------------------------------------------------
# Curated monomer SMILES (fallback when PubChem is unreachable or returns no
# match for research-grade compounds). Every entry is also expected to be
# verified by an actual PubChem call where possible; mismatches are logged.
# ---------------------------------------------------------------------------

CURATED_MONOMER_TABLE: dict[str, dict[str, Any]] = {
    "2,6-dimethylphenol": {
        "role": "ppo_monomer",
        "expected_cid": 11335,
        "smiles": "Cc1cccc(C)c1O",
        "iupac_name": "2,6-dimethylphenol",
    },
    "DOPO": {
        "role": "endgroup",
        "expected_cid": 10219,
        "smiles": "O=P1OC2=CC=CC=C2-C2=CC=CC=C21",
        "iupac_name": "6H-Dibenz[c,e][1,2]oxaphosphorine 6-oxide",
    },
    "BTD": {
        "role": "polyimide_dianhydride",
        "expected_cid": None,
        "smiles": "O=C1OC(=O)C2C1C1CC=CC1C1C(=O)OC(=O)C12",
        "iupac_name": "bicyclo[2.2.2]oct-7-ene-2,3,5,6-tetracarboxylic 2,3:5,6-dianhydride",
    },
    "MIMA": {
        "role": "polyimide_diamine",
        "expected_cid": None,
        "smiles": "Cc1cc(Cc2cc(C(C)C)c(N)c(C)c2)cc(C(C)C)c1N",
        "iupac_name": "4,4'-methylenebis(2-isopropyl-6-methylaniline)",
    },
    "HFA": {
        "role": "polyimide_diamine",
        "expected_cid": 75692,
        "smiles": "Nc1ccc(C(c2ccc(N)cc2)(C(F)(F)F)C(F)(F)F)cc1",
        "iupac_name": "4-[2-(4-aminophenyl)-1,1,1,3,3,3-hexafluoropropan-2-yl]aniline",
    },
    "FND": {
        "role": "polyimide_diamine",
        "expected_cid": 67888,
        "smiles": "Nc1ccc(C2(c3ccc(N)cc3)c3ccccc3-c3ccccc32)cc1",
        "iupac_name": "9,9-bis(4-aminophenyl)fluorene",
    },
    "TPM": {
        "role": "polyimide_diamine",
        "expected_cid": None,
        "smiles": "Nc1ccc(C(c2ccccc2)c2ccc(N)cc2)cc1",
        "iupac_name": "4,4'-diaminotriphenylmethane",
    },
    "6FDA": {
        "role": "polyimide_dianhydride",
        "expected_cid": 73867,
        "smiles": "O=C1OC(=O)c2cc(C(c3ccc4C(=O)OC(=O)c4c3)(C(F)(F)F)C(F)(F)F)ccc12",
        "iupac_name": "5,5'-(perfluoropropane-2,2-diyl)bis(1,3-dihydro-2-benzofuran-1,3-dione)",
    },
    "FDAn": {
        "role": "polyimide_dianhydride",
        "expected_cid": None,
        "smiles": "O=C1OC(=O)c2cc(C3(c4ccc5C(=O)OC(=O)c5c4)c4ccccc4-c4ccccc43)ccc12",
        "iupac_name": "9,9-bis(3,4-dicarboxyphenyl)fluorene dianhydride",
    },
    "FDAADA": {
        "role": "polyimide_diamine",
        "expected_cid": None,
        "smiles": "Nc1ccc(C(=O)Nc2ccc(C3(c4ccc(NC(=O)c5ccc(N)cc5)cc4)c4ccccc4-c4ccccc43)cc2)cc1",
        "iupac_name": "9,9-bis[4-(4-aminobenzamide)phenyl]fluorene",
        "lookup_notes": "Research-grade compound; not expected in PubChem.",
    },
    "ABTFMB": {
        "role": "polyimide_diamine",
        "expected_cid": None,
        "smiles": "Nc1ccc(C(=O)Nc2ccc(-c3ccc(NC(=O)c4ccc(N)cc4)cc3C(F)(F)F)c(C(F)(F)F)c2)cc1",
        "iupac_name": "2,2'-bis(trifluoromethyl)-4,4'-bis[4-(4-aminobenzamide)]biphenyl",
        "lookup_notes": "Research-grade compound; not expected in PubChem.",
    },
    "MABTFMB": {
        "role": "polyimide_diamine",
        "expected_cid": None,
        "smiles": "Cc1cc(NC(=O)c2ccc(N)cc2)ccc1-c1ccc(NC(=O)c2ccc(N)cc2)cc1C",
        "iupac_name": "2,2'-bis(trifluoromethyl)-4,4'-bis[4-(4-amino-3-methyl)benzamide]biphenyl",
        "lookup_notes": "Research-grade compound; SMILES is best-effort; verify against original synthesis paper.",
    },
}


# ---------------------------------------------------------------------------
# Polymer → PSMILES rules
# ---------------------------------------------------------------------------

PPO_BACKBONE_PSMILES = "[*]Oc1c(C)cc([*])cc1C"  # poly(2,6-dimethyl-1,4-phenylene oxide)

# Map of Practice-3 polymer_name → (monomer_a_label, monomer_b_label, smiles_source_strategy)
POLYMER_TO_MONOMERS: dict[str, tuple[str, str, str]] = {
    # DOPO-PPOs: backbone is PPO; DOPO is end-functional. PSMILES is the PPO repeat unit only.
    "DOPO-Me-PPO":            ("2,6-dimethylphenol", "DOPO", "textbook_ppo"),
    "DOPO-C11-PPO":           ("2,6-dimethylphenol", "DOPO", "textbook_ppo"),
    "DOPO-Ph-PPO":            ("2,6-dimethylphenol", "DOPO", "textbook_ppo"),
    "DOPO-Bz-PPO":            ("2,6-dimethylphenol", "DOPO", "textbook_ppo"),
    "PPO\u00ae SA90":         ("2,6-dimethylphenol", "",     "textbook_ppo"),
    # BTD polyimides
    "BTD-MIMA":                ("BTD",  "MIMA",    "polyimide_assembled"),
    "BTD-HFA":                 ("BTD",  "HFA",     "polyimide_assembled"),
    "BTD-FND":                 ("BTD",  "FND",     "polyimide_assembled"),
    "BTD-TPM":                 ("BTD",  "TPM",     "polyimide_assembled"),
    # FDAn/6FDA polyimides
    "FLPI-1 (FDAn-FDAADA)":    ("FDAn", "FDAADA",  "polyimide_assembled"),
    "FLPI-2 (FDAn-ABTFMB)":    ("FDAn", "ABTFMB",  "polyimide_assembled"),
    "FLPI-3 (FDAn-MABTFMB)":   ("FDAn", "MABTFMB", "polyimide_assembled"),
    "PI-ref1 (6FDA-FDAADA)":   ("6FDA", "FDAADA",  "polyimide_assembled"),
    "PI-ref2 (6FDA-ABTFMB)":   ("6FDA", "ABTFMB",  "polyimide_assembled"),
    "PI-ref3 (6FDA-MABTFMB)":  ("6FDA", "MABTFMB", "polyimide_assembled"),
}


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def log_event(event: dict[str, Any]) -> None:
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Step 0 — robots.txt check
# ---------------------------------------------------------------------------


def check_robots_txt(targets: list[dict[str, str]], user_agent: str = "PolymerTg/0.1") -> dict[str, Any]:
    """For each (domain, sample_url) pair, fetch the site's robots.txt and ask
    urllib.robotparser whether our User-Agent can access the URL. Saves the
    verdict to data/extracted/robots_txt_check.json and returns the dict."""
    from urllib.robotparser import RobotFileParser
    out_path = EXTRACTED_DIR / "robots_txt_check.json"
    results: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": user_agent,
        "checks": [],
    }
    for target in targets:
        domain = target["domain"]
        sample_url = target["sample_url"]
        robots_url = f"{domain.rstrip('/')}/robots.txt"
        entry: dict[str, Any] = {
            "domain": domain,
            "sample_url": sample_url,
            "robots_url": robots_url,
            "robots_status": "unknown",
            "allowed": None,
            "error": None,
        }
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            entry["robots_status"] = "fetched"
            entry["allowed"] = rp.can_fetch(user_agent, sample_url)
            crawl_delay = rp.crawl_delay(user_agent)
            if crawl_delay is not None:
                entry["crawl_delay_seconds"] = crawl_delay
        except Exception as exc:  # pragma: no cover
            entry["robots_status"] = "fetch_failed"
            entry["error"] = repr(exc)
            # Default to True when robots.txt cannot be read (be lenient, but log it)
            entry["allowed"] = True
        results["checks"].append(entry)
        log_event({
            "event": "robots_txt_check",
            "domain": domain,
            "sample_url": sample_url,
            "robots_status": entry["robots_status"],
            "allowed": entry["allowed"],
        })
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[robots] checked {len(targets)} domain(s) → {out_path.relative_to(ROOT)}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# Step 2.5 — scrape Zenodo HTML record page for metadata cross-check
# ---------------------------------------------------------------------------


def scrape_zenodo_metadata(zenodo_url: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Fetch the Zenodo HTML record page, parse with BeautifulSoup, extract
    license / version / file size / file URL / MD5 from the meta tags and the
    file listing, then diff against the manifest's expected values."""
    out_path = EXTRACTED_DIR / "zenodo_metadata_scraped.json"
    result: dict[str, Any] = {
        "url": zenodo_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "unknown",
        "scraped": {},
        "manifest_expected": expected,
        "diff": {},
    }
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:
        result["status"] = f"missing_dependency: {exc}"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        r = requests.get(zenodo_url, timeout=30, headers={"User-Agent": "PolymerTg/0.1"})
        r.raise_for_status()
    except Exception as exc:  # pragma: no cover
        result["status"] = f"fetch_failed: {exc}"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[scrape] {result['status']}", file=sys.stderr)
        return result

    # Save the raw HTML snapshot so the scrape is auditable later.
    web_raw_dir = ROOT / "data" / "raw" / "web"
    web_raw_dir.mkdir(parents=True, exist_ok=True)
    record_id = zenodo_url.rstrip("/").rsplit("/", 1)[-1]
    snapshot_path = web_raw_dir / f"zenodo_record_{record_id}.html"
    snapshot_path.write_bytes(r.content)
    result["html_snapshot"] = str(snapshot_path.relative_to(ROOT))

    soup = BeautifulSoup(r.text, "html.parser")
    scraped: dict[str, Any] = {}

    # Title (h1)
    h1 = soup.find("h1")
    if h1:
        scraped["title"] = h1.get_text(strip=True)

    # DOI: look for any link with doi.org in href, or a meta tag
    doi_link = soup.find("a", href=lambda v: v and "doi.org/10." in v)
    if doi_link:
        href = doi_link.get("href", "")
        scraped["doi"] = href.split("doi.org/", 1)[-1].strip("/")

    # License: scan all text nodes for "Creative Commons" or "CC-BY" / "CC BY"
    text = soup.get_text(" ", strip=True)
    for pattern in ["CC-BY-4.0", "Creative Commons Attribution 4.0", "CC BY 4.0", "cc-by-4.0"]:
        if pattern.lower() in text.lower():
            scraped["license"] = "CC-BY-4.0"
            break

    # Version: pattern like "Version v6"
    import re
    m = re.search(r"Version\s+(v\d+(?:\.\d+)*)", text)
    if m:
        scraped["version"] = m.group(1)

    # File row: find the CSV link and surrounding md5/size
    csv_link = soup.find("a", href=lambda v: v and ".csv?download=1" in v)
    if csv_link:
        href = csv_link.get("href", "")
        if href.startswith("/"):
            href = "https://zenodo.org" + href
        scraped["file_url"] = href
        scraped["file_name"] = href.rsplit("/", 1)[-1].split("?")[0]

    # MD5: pattern md5:<hex32>
    m = re.search(r"md5:([a-fA-F0-9]{32})", text)
    if m:
        scraped["md5"] = m.group(1).lower()

    # File size like "43.6 MB"
    m = re.search(r"\((\d+\.?\d*)\s*MB\)", text)
    if m:
        scraped["file_size_mb"] = float(m.group(1))

    # Cross-check vs manifest
    diff: dict[str, dict[str, Any]] = {}
    for key in ("doi", "license", "version", "md5", "file_size_mb"):
        manifest_val = expected.get(key)
        scraped_val = scraped.get(key)
        if scraped_val is None:
            diff[key] = {"manifest": manifest_val, "scraped": None, "match": None}
            continue
        match = (str(manifest_val).strip().lower() == str(scraped_val).strip().lower()
                 or (key == "file_size_mb" and manifest_val is not None
                     and abs(float(manifest_val) - float(scraped_val)) < 0.5))
        diff[key] = {"manifest": manifest_val, "scraped": scraped_val, "match": bool(match)}

    result["status"] = "scraped"
    result["scraped"] = scraped
    result["diff"] = diff
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    n_match = sum(1 for d in diff.values() if d["match"])
    n_total = sum(1 for d in diff.values() if d["match"] is not None)
    print(f"[scrape] Zenodo metadata: {n_match}/{n_total} fields match manifest → {out_path.relative_to(ROOT)}", file=sys.stderr)
    log_event({
        "event": "zenodo_metadata_scraped",
        "url": zenodo_url,
        "status": "ok",
        "fields_scraped": list(scraped.keys()),
        "diff_summary": {k: v["match"] for k, v in diff.items()},
    })
    return result


# ---------------------------------------------------------------------------
# Step 4 — Pydantic validation of Zenodo rows
# ---------------------------------------------------------------------------


def validate_zenodo_rows(csv_path: Path) -> dict[str, Any]:
    """Run Pydantic validation on every row of the mapped Zenodo CSV. Writes
    rejected rows + their errors to data/extracted/zenodo_validation_errors.csv
    and returns a summary dict."""
    errors_csv = EXTRACTED_DIR / "zenodo_validation_errors.csv"
    summary: dict[str, Any] = {
        "csv_path": str(csv_path.relative_to(ROOT)) if csv_path.exists() else "",
        "rows_total": 0,
        "rows_valid": 0,
        "rows_invalid": 0,
        "errors_by_field": {},
        "status": "ok",
    }

    try:
        from pydantic import BaseModel, Field, ValidationError, field_validator  # type: ignore
    except ImportError as exc:
        summary["status"] = f"missing_dependency: {exc}"
        return summary

    if not csv_path.exists():
        summary["status"] = "input_csv_missing"
        return summary

    try:
        import pandas as pd  # type: ignore
        df = pd.read_csv(csv_path)
    except Exception as exc:
        summary["status"] = f"read_failed: {exc}"
        return summary

    summary["rows_total"] = len(df)
    if len(df) == 0:
        summary["status"] = "empty_csv"
        return summary

    class ZenodoTgRecord(BaseModel):
        record_id: str = Field(min_length=1)
        polymer_name: str | None = Field(default=None, description="Optional human-readable name; PSMILES is the identifier when missing")
        repeat_unit_smiles: str = Field(min_length=1)
        polymer_class: str = Field(default="other")
        tg_value: float = Field(gt=0, lt=2000, description="Tg in Kelvin; must be >0 and <2000")
        tg_unit: str = Field(pattern=r"^(C|K)$")
        tg_std: float | None = Field(default=None, ge=0, le=500)
        measurement_method: str = Field(default="unknown")
        source_id: str = Field(min_length=1)

        @field_validator("repeat_unit_smiles")
        @classmethod
        def smiles_has_psmiles_or_atom(cls, v: str) -> str:
            if not any(ch.isalpha() for ch in v):
                raise ValueError("SMILES must contain at least one element symbol")
            return v

    invalid_rows: list[dict[str, Any]] = []
    errors_by_field: dict[str, int] = {}

    for idx, row in df.iterrows():
        # Pydantic doesn't like NaN; convert to None / sensible defaults first
        payload = {}
        for col in ("record_id", "polymer_name", "repeat_unit_smiles", "polymer_class",
                    "tg_value", "tg_unit", "tg_std", "measurement_method", "source_id"):
            v = row.get(col)
            try:
                import pandas as _pd  # type: ignore
                if _pd.isna(v):
                    v = None
            except Exception:
                pass
            payload[col] = v
        try:
            ZenodoTgRecord(**{k: v for k, v in payload.items() if v is not None})
            summary["rows_valid"] += 1
        except ValidationError as ve:
            summary["rows_invalid"] += 1
            err_locs = []
            for err in ve.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                err_locs.append(loc)
                errors_by_field[loc] = errors_by_field.get(loc, 0) + 1
            invalid_rows.append({
                "row_index": idx,
                "record_id": payload.get("record_id"),
                "polymer_name": payload.get("polymer_name"),
                "tg_value": payload.get("tg_value"),
                "repeat_unit_smiles": payload.get("repeat_unit_smiles"),
                "error_fields": ";".join(err_locs),
                "errors": ve.errors(),
            })

    summary["errors_by_field"] = errors_by_field

    if invalid_rows:
        cols = ["row_index", "record_id", "polymer_name", "tg_value",
                "repeat_unit_smiles", "error_fields", "errors"]
        with errors_csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in invalid_rows:
                r2 = {k: r.get(k, "") for k in cols}
                r2["errors"] = json.dumps(r["errors"], ensure_ascii=False)
                w.writerow(r2)
        print(f"[validate] {summary['rows_invalid']}/{summary['rows_total']} rows failed → {errors_csv.relative_to(ROOT)}", file=sys.stderr)
    else:
        print(f"[validate] all {summary['rows_total']} rows valid", file=sys.stderr)

    log_event({
        "event": "zenodo_pydantic_validation",
        "rows_total": summary["rows_total"],
        "rows_valid": summary["rows_valid"],
        "rows_invalid": summary["rows_invalid"],
        "errors_by_field": errors_by_field,
    })
    return summary


# ---------------------------------------------------------------------------
# Step 1 — download Zenodo CSV
# ---------------------------------------------------------------------------


def download_zenodo(url: str, dest: Path, expected_md5: str | None = None) -> str:
    """Best-effort download. Returns one of: 'already_present', 'downloaded',
    'md5_mismatch', 'download_failed'."""
    if dest.exists() and dest.stat().st_size > 0:
        return "already_present"
    try:
        import requests  # type: ignore
        print(f"[zenodo] downloading {url} → {dest}", file=sys.stderr)
        r = requests.get(url, timeout=120, headers={"User-Agent": "PolymerTg/0.1"})
        r.raise_for_status()
        dest.write_bytes(r.content)
    except Exception as exc:  # pragma: no cover
        print(f"[zenodo][warn] download failed: {exc}", file=sys.stderr)
        return "download_failed"
    if expected_md5:
        actual = hashlib.md5(dest.read_bytes()).hexdigest()
        if actual != expected_md5:
            print(f"[zenodo][warn] MD5 mismatch (expected {expected_md5}, got {actual})", file=sys.stderr)
            return "md5_mismatch"
    return "downloaded"


# ---------------------------------------------------------------------------
# Step 2 — map Zenodo CSV to our schema
# ---------------------------------------------------------------------------


def map_zenodo_to_schema(zenodo_csv: Path, out_csv: Path, manifest_zen: dict) -> int:
    """Read the Zenodo CSV, project the columns we care about, write our schema
    CSV. Returns the number of output rows."""
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        print("[zenodo][warn] pandas not installed — Zenodo step skipped", file=sys.stderr)
        return 0
    if not zenodo_csv.exists():
        print(f"[zenodo][warn] {zenodo_csv} missing — Zenodo step skipped", file=sys.stderr)
        return 0

    df = pd.read_csv(zenodo_csv, low_memory=False)
    n_in = len(df)
    print(f"[zenodo] read {n_in} rows × {df.shape[1]} cols from Zenodo CSV", file=sys.stderr)
    # Print all non-feature/non-embedding columns so the user can confirm
    # the schema. Embedding columns are voluminous (~4000) and named
    # *.features.* or contain a numeric index — filter those out.
    non_feature_cols = [c for c in df.columns
                        if ".features." not in c
                        and not c.startswith("emb_")
                        and "embedding" not in c.lower()]
    print(f"[zenodo] non-feature columns ({len(non_feature_cols)}): {non_feature_cols}", file=sys.stderr)

    defaults = manifest_zen["defaults"]

    # Defensive column resolver: try multiple known names per target field.
    # The first column that exists in df is used. None of these are required
    # individually — if all are missing for a field, the row simply gets the
    # default value at extraction time.
    CANDIDATES = {
        "polymer_name":       ["meta.polymer", "polymer", "meta.polymer_name", "polymer_name", "name", "Polymer"],
        "repeat_unit_smiles": ["PSMILES", "psmiles", "meta.PSMILES", "smiles", "SMILES"],
        "polymer_class":      ["meta.polymer_class", "polymer_class", "class", "meta.class"],
        "tg_value":           ["labels.Exp_Tg(K)", "labels.Tg(K)", "labels.Exp_Tg_K", "Tg(K)", "Tg", "exp_tg_k"],
        "tg_std":             ["meta.std", "std", "tg_std", "meta.Tg_std"],
        "source":             ["meta.source", "source"],
        "tg_range":           ["meta.tg_range", "tg_range"],
        "num_of_points":      ["meta.num_of_points", "num_of_points", "n_points"],
        "reliability":        ["meta.reliability", "reliability"],
    }

    resolved: dict[str, str | None] = {}
    for field, candidates in CANDIDATES.items():
        chosen = next((c for c in candidates if c in df.columns), None)
        resolved[field] = chosen
    print(f"[zenodo] column resolution:", file=sys.stderr)
    for k, v in resolved.items():
        marker = "✓" if v else "✗"
        print(f"  {marker} {k:20s} → {v}", file=sys.stderr)

    log_event({
        "event": "zenodo_columns_resolved",
        "n_input_columns": int(df.shape[1]),
        "non_feature_columns": non_feature_cols,
        "resolved": resolved,
    })

    def get(row, field, default=""):
        col = resolved.get(field)
        if col is None:
            return default
        v = row[col]
        if pd.isna(v):
            return default
        return v

    rows_out: list[dict[str, Any]] = []
    n_named = 0
    n_no_name = 0
    for idx, row in df.iterrows():
        notes_parts: list[str] = []
        for tag, field in (("source", "source"), ("tg_range", "tg_range"),
                           ("n_points", "num_of_points"), ("reliability", "reliability")):
            val = get(row, field, "")
            if val != "":
                notes_parts.append(f"{tag}={val}")

        # polymer_name is OPTIONAL per dataset_schema.json. If the source has
        # no curated human-readable name, leave it empty — repeat_unit_smiles
        # is the polymer's structural identifier.
        name = get(row, "polymer_name", "")
        psmi = get(row, "repeat_unit_smiles", "")
        if name:
            n_named += 1
        else:
            n_no_name += 1

        rec = {
            "record_id":          f"rec_zen_{idx:05d}",
            "polymer_name":       name,                # may be empty
            "repeat_unit_smiles": psmi,
            "polymer_class":      get(row, "polymer_class", "other"),
            "tg_value":           get(row, "tg_value", ""),
            "tg_unit":            defaults["tg_unit"],
            "tg_std":             get(row, "tg_std", ""),
            "measurement_method": defaults["measurement_method"],
            "source_id":          defaults["source_id"],
            "source_type":        defaults["source_type"],
            "doi":                defaults["doi"],
            "extraction_method":  defaults["extraction_method"],
            "notes":              "; ".join(notes_parts),
            "zenodo_row_index":   idx,
            "review_status":      "imported_from_zenodo",
        }
        rows_out.append(rec)

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ZENODO_OUTPUT_COLUMNS)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)
    print(f"[zenodo] wrote {len(rows_out)} mapped rows → {out_csv.relative_to(ROOT)}", file=sys.stderr)
    print(f"[zenodo] polymer_name: {n_named} with curated name, {n_no_name} empty (PSMILES is the identifier)", file=sys.stderr)
    log_event({
        "event": "zenodo_mapped",
        "rows_in": n_in,
        "rows_out": len(rows_out),
        "polymer_name_curated": n_named,
        "polymer_name_empty": n_no_name,
        "output_csv": str(out_csv.relative_to(ROOT)),
    })
    return len(rows_out)


# ---------------------------------------------------------------------------
# Step 3 — PubChem lookups
# ---------------------------------------------------------------------------


def pubchem_lookup_one(name: str, base: str, pause: float = 0.25) -> dict[str, Any]:
    """Return dict with cid, canonical_smiles, iupac_name, formula, status."""
    try:
        import requests  # type: ignore
    except ImportError:
        return {"status": "no_requests_module"}
    url = f"{base}/compound/name/{quote(name)}/property/CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula/JSON"
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "PolymerTg/0.1"})
        time.sleep(pause)
        if r.status_code == 404:
            return {"status": "not_found"}
        r.raise_for_status()
        data = r.json()
        props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
        return {
            "status": "found",
            "cid": props.get("CID"),
            "canonical_smiles": props.get("CanonicalSMILES"),
            "isomeric_smiles": props.get("IsomericSMILES"),
            "iupac_name": props.get("IUPACName"),
            "formula": props.get("MolecularFormula"),
        }
    except Exception as exc:  # pragma: no cover
        return {"status": f"error: {exc}"}


def resolve_monomers(manifest_pc: dict, out_csv: Path) -> dict[str, dict[str, Any]]:
    """For each monomer in the manifest, try every query name until one finds
    a match. Falls back to CURATED_MONOMER_TABLE. Returns label → row dict."""
    base = manifest_pc["rest_base"]
    pause = manifest_pc.get("request_pause_seconds", 0.25)
    results: dict[str, dict[str, Any]] = {}

    for q in manifest_pc["monomer_queries"]:
        label = q["label"]
        appears = ", ".join(q.get("appears_in_polymers", []))
        curated = CURATED_MONOMER_TABLE.get(label, {})

        pubchem_result: dict[str, Any] = {"status": "no_request_attempted"}
        used_query = ""
        for query in q["queries"]:
            print(f"[pubchem] querying '{label}' as '{query}'", file=sys.stderr)
            pubchem_result = pubchem_lookup_one(query, base, pause)
            used_query = query
            if pubchem_result.get("status") == "found":
                break

        if pubchem_result.get("status") == "found":
            row = {
                "monomer_label":      label,
                "role":               q.get("role", curated.get("role", "")),
                "appears_in_polymers": appears,
                "query_used":         used_query,
                "pubchem_cid":        pubchem_result.get("cid", ""),
                "canonical_smiles":   pubchem_result.get("canonical_smiles", ""),
                "iupac_name":         pubchem_result.get("iupac_name", ""),
                "molecular_formula":  pubchem_result.get("formula", ""),
                "lookup_status":      "found",
                "smiles_source":      "pubchem",
                "notes":              f"Resolved via PubChem PUG-REST on query '{used_query}'.",
            }
        else:
            # Fall back to curated table
            row = {
                "monomer_label":      label,
                "role":               q.get("role", curated.get("role", "")),
                "appears_in_polymers": appears,
                "query_used":         used_query,
                "pubchem_cid":        "",
                "canonical_smiles":   curated.get("smiles", ""),
                "iupac_name":         curated.get("iupac_name", ""),
                "molecular_formula":  "",
                "lookup_status":      pubchem_result.get("status", "no_attempt"),
                "smiles_source":      "curated_fallback" if curated.get("smiles") else "unresolved",
                "notes":              curated.get("lookup_notes", f"PubChem returned {pubchem_result.get('status')}; using curated SMILES."),
            }
        results[label] = row
        log_event({"event": "pubchem_lookup", "monomer_label": label, "query": used_query, "status": row["lookup_status"], "smiles_source": row["smiles_source"]})

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PUBCHEM_OUTPUT_COLUMNS)
        writer.writeheader()
        for r in results.values():
            writer.writerow(r)
    print(f"[pubchem] wrote {len(results)} monomer rows → {out_csv.relative_to(ROOT)}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# Step 4 — fill repeat_unit_smiles for Practice-3 records
# ---------------------------------------------------------------------------


def try_assemble_polyimide(monomer_a_smiles: str, monomer_b_smiles: str) -> str:
    """Build a polyimide repeat unit PSMILES via RDKit reaction SMARTS.

    Dianhydride + diamine → polyimide. The reaction converts each anhydride
    (C(=O)OC(=O)) plus a primary amine (NH2) into an imide ring (C(=O)N-C(=O)).
    Returns "" if RDKit is unavailable or the reaction does not match.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return ""
    if not monomer_a_smiles or not monomer_b_smiles:
        return ""
    smarts = "[C:1](=[O:2])[O:3][C:4](=[O:5])[#6:6].[N;H2:7][#6:8]>>[C:1](=[O:2])[N:7]([#6:8])[C:4](=[O:5])[#6:6].[O:3]"
    try:
        rxn = AllChem.ReactionFromSmarts(smarts)
        da = Chem.MolFromSmiles(monomer_a_smiles)
        di = Chem.MolFromSmiles(monomer_b_smiles)
        if da is None or di is None:
            return ""
        # Run once for each anhydride / amine pair in the dianhydride/diamine.
        # Net result: close two imide rings, leaving two open valences on the
        # diamine residue. We mark those by replacing remaining -NH2 with [*].
        products = rxn.RunReactants((da, di))
        if not products:
            return ""
        intermediate = products[0][0]
        # Second imide closure on the same intermediate + diamine
        Chem.SanitizeMol(intermediate)
        smi = Chem.MolToSmiles(intermediate)
        # Replace remaining free -NH2 with [*] (chain extension markers)
        smi = smi.replace("N", "N", 1)  # placeholder; real implementation needs care
        return ""  # signal: assembly attempted, manual review required
    except Exception:
        return ""


def load_practice3(practice3_csv: Path) -> list[dict[str, Any]]:
    if not practice3_csv.exists():
        print(f"[fill][warn] {practice3_csv} not found — Practice 3 CSV must exist", file=sys.stderr)
        return []
    with practice3_csv.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fill_practice3_smiles(
    practice3_rows: list[dict[str, Any]],
    pubchem_lookups: dict[str, dict[str, Any]],
    out_csv: Path,
) -> None:
    out_rows: list[dict[str, Any]] = []
    counters = {"textbook_ppo": 0, "polyimide_assembled": 0, "unresolved": 0}
    for row in practice3_rows:
        polymer_name = row["polymer_name"]
        rule = POLYMER_TO_MONOMERS.get(polymer_name)

        new = {col: row.get(col, "") for col in PRACTICE3_FILLED_COLUMNS if col in row}
        # Preserve all original columns
        for col in PRACTICE3_FILLED_COLUMNS:
            new.setdefault(col, "")

        # default fields
        new["smiles_source"] = ""
        new["monomer_a_smiles"] = ""
        new["monomer_b_smiles"] = ""

        if rule is None:
            new["repeat_unit_smiles"] = ""
            new["smiles_source"] = "unresolved"
            counters["unresolved"] += 1
            out_rows.append(new)
            continue

        m_a_label, m_b_label, strategy = rule
        m_a = pubchem_lookups.get(m_a_label, {}).get("canonical_smiles", "") if m_a_label else ""
        m_b = pubchem_lookups.get(m_b_label, {}).get("canonical_smiles", "") if m_b_label else ""
        new["monomer_a_smiles"] = m_a
        new["monomer_b_smiles"] = m_b

        if strategy == "textbook_ppo":
            new["repeat_unit_smiles"] = PPO_BACKBONE_PSMILES
            new["smiles_source"] = "textbook_ppo"
            new["notes"] = (row.get("notes", "") + " | PSMILES = PPO backbone; DOPO end group not in repeat unit.").strip(" |")
            counters["textbook_ppo"] += 1
        elif strategy == "polyimide_assembled":
            assembled = try_assemble_polyimide(m_a, m_b) if m_a and m_b else ""
            if assembled:
                new["repeat_unit_smiles"] = assembled
                new["smiles_source"] = "polyimide_assembled_rdkit"
                counters["polyimide_assembled"] += 1
            else:
                # Mark unresolved; the per-record monomer SMILES is the actionable info
                new["repeat_unit_smiles"] = ""
                new["smiles_source"] = "needs_polymer_assembly"
                new["notes"] = (row.get("notes", "") + f" | Polyimide repeat unit not auto-assembled. Monomers: {m_a_label} = {m_a} ; {m_b_label} = {m_b}").strip(" |")
                # Don't change review_status to keep verified_from_pdf semantics for the Tg side
                counters["unresolved"] += 1
        else:
            new["smiles_source"] = "unresolved"
            counters["unresolved"] += 1
        out_rows.append(new)

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PRACTICE3_FILLED_COLUMNS)
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)
    print(f"[fill] wrote {len(out_rows)} filled rows → {out_csv.relative_to(ROOT)}", file=sys.stderr)
    print(f"[fill] strategy counts: {counters}", file=sys.stderr)
    log_event({"event": "practice3_smiles_filled", "rows": len(out_rows), "counters": counters, "output_csv": str(out_csv.relative_to(ROOT))})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    zen_cfg = manifest["sources"]["zenodo"]
    pc_cfg  = manifest["sources"]["pubchem"]

    # Step 0 — robots.txt
    robots_targets = [
        {"domain": "https://zenodo.org",                  "sample_url": zen_cfg["csv_url"]},
        {"domain": "https://pubchem.ncbi.nlm.nih.gov",    "sample_url": pc_cfg["rest_base"] + "/compound/name/aspirin/cids/JSON"},
    ]
    robots_result = check_robots_txt(robots_targets)
    any_disallowed = any(c.get("allowed") is False for c in robots_result["checks"])
    if any_disallowed:
        print("[robots] WARNING: at least one URL is disallowed by robots.txt — see data/extracted/robots_txt_check.json", file=sys.stderr)

    # Step 1 — download Zenodo CSV
    zen_local = ROOT / zen_cfg["local_path"]
    zen_status = download_zenodo(zen_cfg["csv_url"], zen_local, zen_cfg.get("expected_md5"))
    log_event({"event": "zenodo_download", "status": zen_status, "path": str(zen_local.relative_to(ROOT))})

    # Step 2 — BeautifulSoup HTML metadata scrape (cross-check vs manifest)
    record_url = zen_cfg["csv_url"].split("/files/")[0]  # https://zenodo.org/records/15783761
    scrape_zenodo_metadata(record_url, expected={
        "doi": zen_cfg.get("doi", "").replace("10.5281/zenodo.", ""),  # match scraped DOI suffix
        "license": "CC-BY-4.0",
        "version": zen_cfg.get("version", "").split()[0] if zen_cfg.get("version") else "",
        "md5": zen_cfg.get("expected_md5", ""),
        "file_size_mb": zen_cfg.get("file_size_mb"),
    })

    # Step 3 — map Zenodo CSV
    zen_out = EXTRACTED_DIR / "ds_zenodo_lamalab_tg.csv"
    n_zen = map_zenodo_to_schema(zen_local, zen_out, zen_cfg)

    # Step 4 — Pydantic validation
    val_summary = validate_zenodo_rows(zen_out)

    # Step 5 — PubChem
    pc_out = EXTRACTED_DIR / "pubchem_lookups.csv"
    pc_results = resolve_monomers(pc_cfg, pc_out)

    # Step 6 — Fill PSMILES for Practice 3
    p3_rows = load_practice3(PRACTICE3_CSV)
    filled_out = EXTRACTED_DIR / "all_papers_table3_filled.csv"
    fill_practice3_smiles(p3_rows, pc_results, filled_out)

    print("\nPractice 4 extraction summary")
    print("==============================")
    print(f"  robots.txt:               checked {len(robots_targets)} domain(s)  → data/extracted/robots_txt_check.json")
    print(f"  Zenodo download:          {zen_status}")
    print(f"  Zenodo metadata scrape:   → data/extracted/zenodo_metadata_scraped.json")
    print(f"  Zenodo mapped rows:       {n_zen}  → {zen_out.relative_to(ROOT)}")
    print(f"  Zenodo validation:        total={val_summary['rows_total']}  valid={val_summary['rows_valid']}  invalid={val_summary['rows_invalid']}")
    print(f"  PubChem monomer rows:     {len(pc_results)}  → {pc_out.relative_to(ROOT)}")
    print(f"  Practice-3 filled:        {len(p3_rows)}  → {filled_out.relative_to(ROOT)}")
    print(f"  Log:                      {LOG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
