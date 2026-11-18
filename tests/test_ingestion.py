from pathlib import Path

import pytest

from ingestion.common import normalise_business_id, parse_number, sniff_rows
from ingestion.header_map import map_headers, missing_required
from ingestion.prh import flatten
from ingestion.vero import parse_file


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0112038-9", "0112038-9"),   # valid
        (" 0112038-9 ", "0112038-9"),  # whitespace
        ("112038-9", "0112038-9"),    # old 6-digit form gets a leading zero
        ("0112038-8", None),          # wrong check digit
        ("01120389", None),           # missing hyphen
        ("", None),
        (None, None),
    ],
)
def test_business_id(raw, expected):
    assert normalise_business_id(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("1 234 567,89", 1234567.89), ("1234.5", 1234.5), ("-12,5", -12.5), ("1.234,50", 1234.5), ("", None), ("x", None)],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize(
    "headers",
    [
        ["Y-tunnus", "Nimi", "Kotikunta", "Verotettava tulo", "Maksuunpannut verot yhteensä"],
        ["Verovuosi", "Kotikunnan nro", "Kotikunta", "Y-tunnus", "Verovelvollisen nimi",
         "Verotettava tulo", "Maksuunpannun veron määrä"],
        ["Y-tunnus / FO-nummer", "Nimi / Namn", "Verotettava tulo / Beskattningsbar inkomst",
         "Maksuunpantu vero / Debiterad skatt"],
    ],
)
def test_header_layouts_map_required_columns(headers):
    assert missing_required(map_headers(headers)) == set()


def test_code_column_not_mistaken_for_name():
    mapping = map_headers(["Kotikunnan nro", "Kotikunta", "Y-tunnus", "Verotettava tulo", "Maksuunpantu vero"])
    assert mapping[0] == "municipality_code"
    assert mapping[1] == "municipality"


def test_sniff_semicolon_and_comma():
    header, rows = sniff_rows("a;b;c\n1;2;3\n")
    assert header == ["a", "b", "c"] and rows == [["1", "2", "3"]]
    header, rows = sniff_rows("a,b\n1,2\n\n")
    assert header == ["a", "b"] and rows == [["1", "2"]]


def test_parse_file_handles_cp1252(tmp_path: Path):
    p = tmp_path / "vero_2012.csv"
    p.write_bytes("Y-tunnus;Nimi;Kotikunta;Verotettava tulo;Maksuunpannut verot\n0112038-9;Ääkkönen Oy;Jyväskylä;1 000,00;245,00\n".encode("cp1252"))
    df, profile = parse_file(p, 2012, "assessment")
    assert df.loc[0, "municipality"] == "Jyväskylä"
    assert df.loc[0, "taxable_income"] == 1000.0
    assert df.loc[0, "tax_year"] == 2012
    assert {r["canonical_column"] for r in profile} >= {"business_id", "tax_imposed"}


def test_parse_file_rejects_unknown_layout(tmp_path: Path):
    p = tmp_path / "vero_2030.csv"
    p.write_text("foo;bar\n1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="required columns"):
        parse_file(p, 2030, "assessment")


def test_prh_flatten_picks_current_name_and_bankruptcy():
    company = {
        "businessId": {"value": "0112038-9", "registrationDate": "1978-03-15"},
        "names": [
            {"name": "Old Name Oy", "version": 2, "registrationDate": "1978-03-15", "endDate": "2001-01-01"},
            {"name": "New Name Oy", "version": 1, "registrationDate": "2001-01-01", "endDate": None},
        ],
        "companyForms": [{"type": "OY", "version": 1, "descriptions": [{"languageCode": "3", "description": "Limited company"}]}],
        "mainBusinessLine": {"type": "62010", "descriptions": []},
        "companySituations": [{"type": "KONK", "registrationDate": "2020-05-01", "endDate": None}],
        "addresses": [{"type": 1, "postCode": "00100", "postOffices": [{"city": "HELSINKI", "municipalityCode": "091"}]}],
        "registrationDate": "1978-03-15",
        "endDate": None,
    }
    row, events = flatten(company)
    assert row["name"] == "New Name Oy"
    assert row["company_form_desc"] == "Limited company"
    assert row["municipality_code"] == "091"
    assert events == [{"business_id": "0112038-9", "situation": "KONK", "start_date": "2020-05-01", "end_date": None}]
