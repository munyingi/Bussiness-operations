"""Shared helpers: paths, config, downloads, Business ID validation, CSV sniffing."""

from __future__ import annotations

import csv
import io
import logging
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "data" / "trends.duckdb"
SAMPLE_DIR = ROOT / "sample_data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("trends")


def load_config() -> dict:
    with open(ROOT / "config" / "sources.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def download(url: str, dest: Path, retries: int = 3, timeout: int = 120) -> Path:
    """Download url to dest, skipping if it already exists. Retries with backoff."""
    if dest.exists() and dest.stat().st_size > 0:
        log.info("cached %s", dest.name)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                tmp.rename(dest)
            log.info("downloaded %s", dest.name)
            return dest
        except requests.RequestException as exc:
            log.warning("attempt %s/%s failed for %s: %s", attempt, retries, url, exc)
            time.sleep(2**attempt)
    raise RuntimeError(f"could not download {url}")


# Finnish Business ID (Y-tunnus): 7 digits, hyphen, check digit.
_WEIGHTS = (7, 9, 10, 5, 8, 4, 2)


def business_id_check_digit(seven_digits: str) -> int | None:
    remainder = sum(int(d) * w for d, w in zip(seven_digits, _WEIGHTS)) % 11
    if remainder == 0:
        return 0
    if remainder == 1:
        return None  # no valid check digit exists for this base
    return 11 - remainder


def normalise_business_id(value: str | None) -> str | None:
    """Return 'NNNNNNN-C' if value is a valid Y-tunnus, else None.

    Older IDs are sometimes written with 6 digits; those get a leading zero.
    """
    if value is None:
        return None
    s = str(value).strip().replace(" ", "")
    if "-" not in s or len(s) < 8:
        return None
    base, _, check = s.partition("-")
    if not (base.isdigit() and check.isdigit() and len(check) == 1):
        return None
    base = base.zfill(7)
    if len(base) != 7:
        return None
    expected = business_id_check_digit(base)
    if expected is None or expected != int(check):
        return None
    return f"{base}-{check}"


def write_raw_table(df, table: str, warehouse: Path | None = None) -> int:
    """Replace raw.<table> in the DuckDB warehouse with df. Returns row count."""
    import duckdb

    path = warehouse or WAREHOUSE
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema if not exists raw")
        con.register("df_in", df)
        con.execute(f"create or replace table raw.{table} as select * from df_in")
        n = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
    finally:
        con.close()
    log.info("raw.%s: %s rows", table, n)
    return n


def read_text_any_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"cannot decode {path}")


def sniff_rows(text: str) -> tuple[list[str], list[list[str]]]:
    """Detect the delimiter and return (header, rows)."""
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    return rows[0], rows[1:]


def parse_number(value: str | None) -> float | None:
    """Parse Finnish-style numbers: '1 234,56', '1234.56', '-12,5', '' -> None."""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "").replace(" ", "")
    if s in ("", "-", "."):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
