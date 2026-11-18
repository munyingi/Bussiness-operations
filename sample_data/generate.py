"""Generate SYNTHETIC sample files that mimic the real sources' shape.

Nothing in sample_data/ is real tax data. Company names, Business IDs,
incomes, bankruptcies and price indexes are all invented. The files exist so
that tests and CI can run the whole pipeline without network access, and so
students can fork the repo and run it in seconds.

What the samples deliberately include, because the real data has it too:
  * header drift across years (three layouts, two encodings, two delimiters)
  * Finnish decimal commas and thousands separators
  * a few malformed Business IDs
  * companies in Vero that are missing from the PRH Trade Register
  * dissolved companies, bankruptcies, zero-tax years, later corrections
"""

from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
rng = random.Random(2011)

WEIGHTS = (7, 9, 10, 5, 8, 4, 2)
MUNICIPALITIES = [
    ("091", "Helsinki"), ("049", "Espoo"), ("092", "Vantaa"), ("837", "Tampere"),
    ("853", "Turku"), ("564", "Oulu"), ("179", "Jyväskylä"), ("297", "Kuopio"),
]
INDUSTRIES = [  # (TOL 2008 code, typical taxable income scale, growth per year)
    ("62010", 400_000, 0.07), ("41200", 250_000, 0.01), ("47111", 300_000, 0.02),
    ("56101", 60_000, 0.00), ("70220", 150_000, 0.04), ("10710", 200_000, 0.01),
    ("68201", 180_000, 0.03), ("86210", 220_000, 0.03), ("16100", 500_000, -0.01),
]
FORMS = [("OY", "Limited company"), ("OYJ", "Public limited company"), ("OK", "Cooperative")]
RATE = {2011: 0.26, 2012: 0.245, 2013: 0.245}
YEARS = range(2011, 2026)
WORDS = ["Pohjola", "Revontuli", "Kide", "Saimaa", "Aalto", "Kivi", "Tunturi", "Lumi",
         "Metsä", "Ranta", "Sisu", "Kaamos", "Helmi", "Koski", "Taiga", "Vesi"]
SUFFIX = ["Oy", "Ab", "Group Oy", "Tech Oy", "Rakennus Oy", "Palvelut Oy"]


def make_business_id(used: set[str]) -> str:
    while True:
        base = f"{rng.randint(1_000_000, 3_299_999):07d}"
        r = sum(int(d) * w for d, w in zip(base, WEIGHTS)) % 11
        if r == 1:
            continue
        bid = f"{base}-{0 if r == 0 else 11 - r}"
        if bid not in used:
            used.add(bid)
            return bid


def build_companies(n: int = 420) -> list[dict]:
    used: set[str] = set()
    companies = []
    for i in range(n):
        reg_year = rng.choice(range(1988, 2025))
        industry = rng.choice(INDUSTRIES)
        end_year = None
        if rng.random() < 0.22:
            end_year = rng.randint(max(reg_year + 1, 2012), 2025)
        companies.append({
            "business_id": make_business_id(used),
            "name": f"{rng.choice(WORDS)} {rng.choice(WORDS)} {rng.choice(SUFFIX)}",
            "reg_date": f"{reg_year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "reg_year": reg_year,
            "end_year": end_year,
            "bankrupt": end_year is not None and rng.random() < 0.4,
            "municipality": rng.choices(MUNICIPALITIES, weights=[30, 15, 10, 12, 8, 8, 5, 5])[0],
            "industry": industry,
            "form": rng.choices(FORMS, weights=[90, 3, 7])[0],
            "scale": industry[1] * math.exp(rng.gauss(0, 1.3)),
            "loss_prone": rng.random() < 0.25,
            "in_prh": rng.random() > 0.12,  # some Vero taxpayers are not in the Trade Register
        })
    return companies


def assessment(company: dict, year: int) -> tuple[float, float]:
    growth = (1 + company["industry"][2]) ** (year - 2011)
    shock = 0.7 if year == 2020 and company["industry"][0] in ("56101", "47111") else 1.0
    income = company["scale"] * growth * shock * math.exp(rng.gauss(0, 0.35))
    if company["loss_prone"] and rng.random() < 0.6:
        income = 0.0
    elif rng.random() < 0.08:
        income = 0.0
    income = round(income, 2)
    tax = round(income * RATE.get(year, 0.20), 2)
    return income, tax


def fi_number(x: float) -> str:
    """Format like '1 234 567,89' (Finnish style)."""
    whole, frac = f"{x:.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return " ".join(groups) + "," + frac


def write_vero(companies: list[dict]) -> list[tuple]:
    layouts = {
        "A": (["Y-tunnus", "Nimi", "Kotikunta", "Verotettava tulo", "Maksuunpannut verot yhteensä",
               "Ennakot yhteensä", "Jäännösvero", "Veronpalautus"], ";", "cp1252"),
        "B": (["Verovuosi", "Kotikunnan nro", "Kotikunta", "Y-tunnus", "Verovelvollisen nimi",
               "Verotettava tulo", "Maksuunpannun veron määrä", "Ennakoiden määrä",
               "Jäännösveron määrä", "Palautettava määrä"], ";", "utf-8"),
        "C": (["Verovuosi", "Y-tunnus / FO-nummer", "Nimi / Namn", "Kotikunta / Hemkommun",
               "Verotettava tulo / Beskattningsbar inkomst", "Maksuunpantu vero / Debiterad skatt",
               "Ennakot / Förskott", "Jäännösvero / Kvarskatt", "Palautus / Återbäring"], ",", "utf-8"),
    }
    history = []
    for year in YEARS:
        layout = "A" if year <= 2015 else "B" if year <= 2019 else "C"
        header, delim, enc = layouts[layout]
        rows = []
        for c in companies:
            if c["reg_year"] > year or (c["end_year"] and c["end_year"] < year):
                continue
            income, tax = assessment(c, year)
            history.append((c["business_id"], year, income, tax))
            prepay = round(tax * rng.uniform(0.7, 1.2), 2)
            residual = round(max(tax - prepay, 0), 2)
            refund = round(max(prepay - tax, 0), 2)
            bid = c["business_id"]
            if rng.random() < 0.004:
                bid = bid.replace("-", "")  # malformed on purpose
            code, muni = c["municipality"]
            num = fi_number if layout != "C" else (lambda v: f"{v:.2f}")
            values = {
                "A": [bid, c["name"], muni, num(income), num(tax), num(prepay), num(residual), num(refund)],
                "B": [str(year), code, muni, bid, c["name"], num(income), num(tax), num(prepay), num(residual), num(refund)],
                "C": [str(year), bid, c["name"], muni, num(income), num(tax), num(prepay), num(residual), num(refund)],
            }[layout]
            rows.append(values)
        with open(OUT / f"vero_{year}.csv", "w", newline="", encoding=enc) as f:
            w = csv.writer(f, delimiter=delim)
            w.writerow(header)
            w.writerows(rows)
    return history


def write_changes(history: list[tuple]) -> None:
    recent = [h for h in history if h[1] in (2022, 2023, 2024) and h[2] > 0]
    picks = rng.sample(recent, 30)
    with open(OUT / "vero_changes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Verovuosi", "Y-tunnus", "Nimi", "Kotikunta", "Verotettava tulo",
                    "Maksuunpantu vero", "Päätöspäivä"])
        for bid, year, income, _ in picks:
            new_income = round(income * rng.choice([0.5, 0.8, 1.15, 1.6]), 2)
            month = rng.randint(1, 12)
            decided = f"{year + rng.randint(1, 2)}-{month:02d}-{rng.randint(1, 28):02d}"
            w.writerow([year, bid, "", "", fi_number(new_income), fi_number(round(new_income * 0.2, 2)), decided])


def write_prh(companies: list[dict]) -> None:
    out = []
    for c in companies:
        if not c["in_prh"]:
            continue
        situations = []
        if c["bankrupt"]:
            situations.append({"type": "KONK", "registrationDate": f"{c['end_year'] - 1}-06-15",
                               "endDate": None, "source": "1"})
        end_date = f"{c['end_year']}-12-31" if c["end_year"] else None
        code, muni = c["municipality"]
        out.append({
            "businessId": {"value": c["business_id"], "registrationDate": c["reg_date"], "source": "3"},
            "names": [{"name": c["name"], "type": "1", "registrationDate": c["reg_date"],
                       "endDate": None, "version": 1, "source": "1"}],
            "mainBusinessLine": {"type": c["industry"][0], "typeCodeSet": "TOIMI4",
                                 "descriptions": [{"languageCode": "3", "description": f"Industry {c['industry'][0]}"}],
                                 "registrationDate": c["reg_date"], "source": "2"},
            "companyForms": [{"type": c["form"][0], "version": 1, "registrationDate": c["reg_date"],
                              "descriptions": [{"languageCode": "3", "description": c["form"][1]}],
                              "endDate": None, "source": "1"}],
            "companySituations": situations,
            "registeredEntries": [],
            "addresses": [{"type": 1, "street": "Esimerkkikatu", "postCode": "00100",
                           "postOffices": [{"city": muni.upper(), "languageCode": "1", "municipalityCode": code}],
                           "registrationDate": c["reg_date"], "source": "1"}],
            "tradeRegisterStatus": "2" if c["end_year"] else "1",
            "status": "3" if c["end_year"] else "2",
            "registrationDate": c["reg_date"],
            "endDate": end_date,
            "lastModified": "2026-11-01T00:00:00",
        })
    (OUT / "prh_companies.json").write_text(json.dumps({"companies": out}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    companies = build_companies()
    history = write_vero(companies)
    write_changes(history)
    write_prh(companies)
    print(f"wrote synthetic samples for {len(companies)} companies to {OUT}")
