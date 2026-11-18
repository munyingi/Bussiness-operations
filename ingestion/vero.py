"""Ingest Vero corporate income tax public data, tax years 2011 onward.

Produces three raw tables:
  raw.vero_assessments     one row per company per tax year (original assessment)
  raw.vero_changes         later corrections to tax years 2022+
  raw.vero_header_profile  how every source header was mapped (drift audit)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import requests

from ingestion.common import (
    RAW_DIR,
    ROOT,
    SAMPLE_DIR,
    download,
    load_config,
    log,
    normalise_business_id,
    parse_number,
    read_text_any_encoding,
    sniff_rows,
    write_raw_table,
)
from ingestion.header_map import map_headers, missing_required

NUMERIC = ["taxable_income", "tax_imposed", "prepayments", "residual_tax", "tax_refund"]
TEXT = ["name", "municipality", "municipality_code"]


def discover_files(cfg: dict) -> dict[int, str]:
    """Return {tax_year: url}. Direct vero.fi links win over CKAN resources."""
    vero = cfg["vero"]
    files: dict[int, str] = {}
    try:
        resp = requests.get(vero["ckan_api"], params={"id": vero["ckan_package_id"]}, timeout=60)
        resp.raise_for_status()
        for res in resp.json()["result"]["resources"]:
            label = f"{res.get('name', '')} {res.get('url', '')}"
            match = re.search(r"(20[12]\d)", label)
            if match and str(res.get("format", "")).lower() in ("csv", "", "text/csv"):
                files[int(match.group(1))] = res["url"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        log.warning("CKAN discovery failed, using direct links only: %s", exc)
    for year, url in vero["direct_files"].items():
        files[int(year)] = url
    wanted = range(vero["first_year"], vero["last_year"] + 1)
    missing = [y for y in wanted if y not in files]
    if missing:
        log.warning("no source file found for tax years %s", missing)
    return {y: u for y, u in sorted(files.items()) if y in wanted}


def parse_file(path: Path, tax_year: int | None, kind: str) -> tuple[pd.DataFrame, list[dict]]:
    """Parse one Vero CSV into canonical columns plus a header profile."""
    header, rows = sniff_rows(read_text_any_encoding(path))
    mapping = map_headers(header)
    profile = [
        {
            "source_file": path.name,
            "kind": kind,
            "tax_year": tax_year,
            "column_position": i,
            "source_header": h,
            "canonical_column": mapping.get(i),
        }
        for i, h in enumerate(header)
    ]
    missing = missing_required(mapping)
    if missing:
        raise ValueError(f"{path.name}: could not find required columns {missing}. Headers: {header}")

    records = []
    for row in rows:
        rec = {canon: (row[i] if i < len(row) else None) for i, canon in mapping.items()}
        out = {"business_id_raw": rec.get("business_id")}
        out["business_id"] = normalise_business_id(rec.get("business_id"))
        for col in TEXT:
            val = rec.get(col)
            out[col] = val.strip() if isinstance(val, str) and val.strip() else None
        for col in NUMERIC:
            out[col] = parse_number(rec.get(col))
        year_val = rec.get("tax_year")
        out["tax_year"] = int(parse_number(year_val)) if parse_number(year_val) else tax_year
        if kind == "changes":
            out["decision_date"] = rec.get("decision_date")
        out["source_file"] = path.name
        records.append(out)
    return pd.DataFrame.from_records(records), profile


def run(sample: bool = False) -> None:
    cfg = load_config()
    frames, changes, profiles = [], [], []

    if sample:
        year_files = {int(re.search(r"(\d{4})", p.name).group(1)): p for p in SAMPLE_DIR.glob("vero_20[0-9][0-9].csv")}
        changes_path = SAMPLE_DIR / "vero_changes.csv"
    else:
        year_files = {}
        for year, url in discover_files(cfg).items():
            try:
                year_files[year] = download(url, RAW_DIR / "vero" / f"vero_{year}.csv")
            except RuntimeError as exc:
                # Vero only keeps recent years online; older catalogue links are dead.
                log.warning("tax year %s unavailable online, skipped: %s", year, exc)
        history = ROOT / cfg["vero"]["history_dir"]
        for path in sorted(history.glob("*.csv")) if history.exists() else []:
            match = re.search(r"(20[12]\d)", path.name)
            if match and int(match.group(1)) not in year_files:
                year_files[int(match.group(1))] = path
                log.info("tax year %s loaded from %s", match.group(1), path)
        log.info("tax years loaded: %s", sorted(year_files))
        changes_path = download(cfg["vero"]["changes_file"], RAW_DIR / "vero" / "vero_changes.csv")

    for year, path in sorted(year_files.items()):
        df, prof = parse_file(path, year, "assessment")
        frames.append(df)
        profiles.extend(prof)
        log.info("tax year %s: %s rows, %s invalid business ids", year, len(df), df["business_id"].isna().sum())

    if changes_path.exists():
        df, prof = parse_file(changes_path, None, "changes")
        changes.append(df)
        profiles.extend(prof)

    write_raw_table(pd.concat(frames, ignore_index=True), "vero_assessments")
    if changes:
        write_raw_table(pd.concat(changes, ignore_index=True), "vero_changes")
    write_raw_table(pd.DataFrame(profiles), "vero_header_profile")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use synthetic files in sample_data/")
    run(parser.parse_args().sample)
