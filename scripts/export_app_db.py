"""Write a small DuckDB file with only what the dashboard reads.

The full warehouse (raw rows for every company and year) is too big for
GitHub and Streamlit Community Cloud. The dashboard only needs the marts,
the header profile and the run metadata, which fit in a few MB.

    python scripts/export_app_db.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "trends.duckdb"
DST = ROOT / "data" / "app" / "trends_app.duckdb"


def main() -> None:
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.unlink(missing_ok=True)
    con = duckdb.connect(str(DST))
    con.execute(f"attach '{SRC}' as src (read_only)")
    for schema in ("marts", "staging", "raw"):
        con.execute(f"create schema if not exists {schema}")
    marts = [r[0] for r in con.execute(
        "select table_name from duckdb_tables() where database_name = 'src' and schema_name = 'marts'").fetchall()]
    for t in marts:
        con.execute(f"create table marts.{t} as select * from src.marts.{t}")
    con.execute("create table staging.stg_vero__header_profile as select * from src.staging.stg_vero__header_profile")
    con.execute("create table raw.pipeline_run as select * from src.raw.pipeline_run")
    con.execute("detach src")
    con.close()
    print(f"wrote {DST.relative_to(ROOT)} ({DST.stat().st_size / 1e6:.1f} MB, {len(marts)} marts)")


if __name__ == "__main__":
    main()
