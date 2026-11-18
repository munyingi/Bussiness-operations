"""Ingest the PRH / YTJ Trade Register bulk file (open data API v3).

Produces:
  raw.prh_companies         one row per company, flattened
  raw.prh_company_events    company situations (bankruptcy, liquidation,
                            restructuring) with start and end dates
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd

from ingestion.common import RAW_DIR, SAMPLE_DIR, download, load_config, log, write_raw_table


def _current(items: list[dict] | None) -> dict:
    """Pick the current version (version == 1, no end date) from a history list."""
    if not items:
        return {}
    current = [i for i in items if i.get("version") == 1 and not i.get("endDate")]
    return (current or sorted(items, key=lambda i: i.get("registrationDate") or "", reverse=True))[0]


def _description(item: dict, lang: str = "3") -> str | None:
    """PRH descriptions use languageCode 1=fi, 2=sv, 3=en."""
    for d in item.get("descriptions") or []:
        if str(d.get("languageCode")) == lang:
            return d.get("description")
    descs = item.get("descriptions") or []
    return descs[0].get("description") if descs else None


def flatten(company: dict) -> tuple[dict, list[dict]]:
    bid = (company.get("businessId") or {}).get("value")
    name = _current(company.get("names")).get("name")
    form = _current(company.get("companyForms"))
    line = company.get("mainBusinessLine") or {}
    street = next((a for a in company.get("addresses") or [] if a.get("type") == 1), None)
    address = street or ((company.get("addresses") or [None])[0]) or {}
    post_office = next(iter(address.get("postOffices") or []), {}) if address else {}

    row = {
        "business_id": bid,
        "name": name,
        "company_form": form.get("type"),
        "company_form_desc": _description(form) if form else None,
        "industry_code": line.get("type"),
        "industry_desc": _description(line) if line else None,
        "industry_code_set": line.get("typeCodeSet"),
        "business_id_registration_date": (company.get("businessId") or {}).get("registrationDate"),
        "registration_date": company.get("registrationDate"),
        "end_date": company.get("endDate"),
        "status": company.get("status"),
        "trade_register_status": company.get("tradeRegisterStatus"),
        "post_code": address.get("postCode") if address else None,
        "city": post_office.get("city"),
        "municipality_code": post_office.get("municipalityCode"),
        "last_modified": company.get("lastModified"),
    }
    events = [
        {
            "business_id": bid,
            "situation": s.get("type"),
            "start_date": s.get("registrationDate"),
            "end_date": s.get("endDate"),
        }
        for s in company.get("companySituations") or []
    ]
    return row, events


def _iter_companies(path: Path):
    """Yield company dicts from the PRH zip (or a plain JSON file in sample mode)."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            for member in zf.namelist():
                if member.endswith(".json"):
                    with zf.open(member) as f:
                        data = json.load(f)
                        yield from data.get("companies", data) if isinstance(data, dict) else data
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        yield from data.get("companies", data) if isinstance(data, dict) else data


def run(sample: bool = False) -> None:
    if sample:
        path = SAMPLE_DIR / "prh_companies.json"
    else:
        path = download(load_config()["prh"]["all_companies"], RAW_DIR / "prh" / "all_companies.zip", timeout=600)

    rows, events = [], []
    for company in _iter_companies(path):
        row, ev = flatten(company)
        rows.append(row)
        events.extend(ev)
    log.info("PRH companies parsed: %s", len(rows))

    write_raw_table(pd.DataFrame(rows), "prh_companies")
    write_raw_table(
        pd.DataFrame(events, columns=["business_id", "situation", "start_date", "end_date"]),
        "prh_company_events",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    run(parser.parse_args().sample)
