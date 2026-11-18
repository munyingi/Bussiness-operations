"""Map 15 years of drifting Vero CSV headers onto one canonical schema.

Vero has renamed and reordered columns over the years, and publishes in
Finnish (sometimes with Swedish in the same header). Instead of hard-coding
one layout per year, each header is matched against keyword rules. Every
match is logged to raw.vero_header_profile so drift is visible and testable.
"""

from __future__ import annotations

import re
import unicodedata

# Order matters: the first rule that matches a header wins, and each canonical
# column is only assigned once. More specific rules come first.
RULES: list[tuple[str, list[str]]] = [
    ("business_id", [r"y.?tunnus", r"yritys.*tunnus", r"fo.?nummer", r"business.?id"]),
    ("municipality_code", [r"kunta.*(nro|numero|koodi)", r"kunnan.*(nro|numero|koodi)"]),
    ("municipality", [r"kotikunta", r"kunta", r"hemkommun", r"municipality"]),
    ("name", [r"^nimi", r"verovelvollisen nimi", r"namn", r"^name"]),
    ("taxable_income", [r"verotettava", r"beskattningsbar", r"taxable"]),
    ("tax_imposed", [r"maksuunpan", r"maksuun pan", r"debiterad", r"tax imposed", r"verot yhteens", r"vero yhteens"]),
    ("prepayments", [r"ennak", r"forskott", r"prepay"]),
    ("residual_tax", [r"jaannos", r"kvarskatt", r"residual"]),
    ("tax_refund", [r"palaut", r"aterbaring", r"refund"]),
    ("tax_year", [r"verovuosi", r"skatteår", r"skattear", r"tax.?year"]),
    ("decision_date", [r"paatospaiva", r"paatos.*pvm", r"muutos.*pvm", r"beslut", r"decision"]),
]


def _fold(text: str) -> str:
    """Lowercase and strip accents so 'Jäännösvero' matches 'jaannos'."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def map_headers(headers: list[str]) -> dict[int, str]:
    """Return {column_index: canonical_name} for every header we recognise."""
    assigned: dict[int, str] = {}
    used: set[str] = set()
    folded = [_fold(h) for h in headers]
    for canonical, patterns in RULES:
        if canonical in used:
            continue
        for idx, header in enumerate(folded):
            if idx in assigned:
                continue
            if any(re.search(p, header) for p in patterns):
                assigned[idx] = canonical
                used.add(canonical)
                break
    return assigned


REQUIRED = {"business_id", "taxable_income", "tax_imposed"}


def missing_required(mapping: dict[int, str]) -> set[str]:
    return REQUIRED - set(mapping.values())
