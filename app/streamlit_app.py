"""Finnish corporate tax and company register trends.

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
# Full warehouse when built locally; otherwise the small committed snapshot
# that GitHub Actions refreshes from the real sources (used on Streamlit Cloud).
DB = Path(os.environ.get("TRENDS_DB") or next(
    (p for p in (ROOT / "data" / "trends.duckdb", ROOT / "data" / "app" / "trends_app.duckdb") if p.exists()),
    ROOT / "data" / "app" / "trends_app.duckdb",
))

st.set_page_config(page_title="Finnish corporate tax trends", layout="wide")


@st.cache_resource
def connect():
    return duckdb.connect(str(DB), read_only=True)


@st.cache_data
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return connect().execute(sql, list(params)).df()


def euro(x) -> str:
    if x is None or pd.isna(x):
        return "n/a"
    for unit, div in (("bn", 1e9), ("m", 1e6), ("k", 1e3)):
        if abs(x) >= div:
            return f"€{x / div:,.1f}{unit}"
    return f"€{x:,.0f}"


def line(df: pd.DataFrame, y: str, title: str, color: str | None = None, fmt: str | None = None):
    enc = {"x": alt.X("tax_year:O", title="Tax year"), "y": alt.Y(f"{y}:Q", title=title, axis=alt.Axis(format=fmt) if fmt else alt.Axis())}
    if color:
        enc["color"] = alt.Color(f"{color}:N", title="")
    return alt.Chart(df).mark_line(point=True).encode(**enc)


if not DB.exists():
    st.error(f"No database at {DB}. Run `make sample` or `make live`, or wait for the Refresh live data workflow to commit data/app/trends_app.duckdb.")
    st.stop()

run = q("select * from raw.pipeline_run")
if not run.empty and run.loc[0, "mode"] == "sample":
    st.warning("**Synthetic sample data.** Names, IDs and figures are invented. Run `make live` for the real data.")

trend = q("select * from marts.mart_yearly_trend order by tax_year")
years = trend.tax_year.tolist()

st.title("Finnish corporate tax and company register trends")
st.caption(
    f"Tax years loaded: {years[0]} to {years[-1]} ({len(years)} years). "
    "Sources: Finnish Tax Administration (Vero) and Finnish Patent and Registration Office (PRH), CC BY 4.0."
)

tabs = st.tabs(["National trend", "Industries", "Municipalities", "Company register", "Top taxpayers", "Data quality", "About"])

with tabs[0]:
    last = trend.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corporate tax imposed", euro(last.total_tax), f"{last.total_tax_yoy:+.1%}" if pd.notna(last.total_tax_yoy) else None)
    c2.metric("Corporate taxpayers", f"{int(last.n_taxpayers):,}", f"{last.n_taxpayers_yoy:+.1%}" if pd.notna(last.n_taxpayers_yoy) else None)
    c3.metric("Share paying any tax", f"{last.paying_share:.0%}")
    c4.metric("Paid by top 1%", f"{last.top1pct_share:.0%}")
    left, right = st.columns(2)
    left.altair_chart(line(trend, "total_tax", "Tax imposed (€)"), width="stretch")
    right.altair_chart(line(trend, "n_taxpayers", "Corporate taxpayers"), width="stretch")
    conc = trend.melt("tax_year", ["top1pct_share", "top10pct_share", "paying_share"], "measure", "share")
    left.altair_chart(line(conc, "share", "Share", color="measure", fmt="%"), width="stretch")
    entry = q("select * from marts.mart_entry_exit_trend order by tax_year")
    right.altair_chart(line(entry.melt("tax_year", ["entrants", "exits"], "flow", "companies"), "companies", "Companies", color="flow"), width="stretch")
    st.caption("The statutory rate fell from 24.5% to 20% in 2014. Taxable income is not the same as profit.")

with tabs[1]:
    ind = q("select * from marts.mart_industry_trend where industry_section <> '?'")
    st.altair_chart(line(ind, "total_tax", "Tax imposed (€)", color="industry_section_name"), width="stretch")
    st.altair_chart(line(ind, "share_of_national_tax", "Share of national corporate tax", color="industry_section_name", fmt="%"), width="stretch")
    pick = st.selectbox("Year", years[::-1], key="ind_year")
    st.dataframe(ind[ind.tax_year == pick].sort_values("total_tax", ascending=False), hide_index=True)

with tabs[2]:
    mun = q("select * from marts.mart_municipality_trend")
    names = mun.groupby("municipality").total_tax.sum().sort_values(ascending=False).index.tolist()
    chosen = st.multiselect("Municipalities", names, default=names[:5])
    st.altair_chart(line(mun[mun.municipality.isin(chosen)], "total_tax", "Tax imposed (€)", color="municipality"), width="stretch")
    pick = st.selectbox("Year", years[::-1], key="mun_year")
    st.dataframe(mun[mun.tax_year == pick].sort_values("national_rank"), hide_index=True)
    st.caption("By home municipality on Vero's list. Municipalities' actual share of corporate tax is distributed by where companies operate.")

with tabs[3]:
    reg = q("select * from marts.mart_registration_trend")
    total = reg.groupby("year", as_index=False)[["registrations", "dissolutions", "bankruptcies_started"]].sum()
    st.altair_chart(
        alt.Chart(total.melt("year", var_name="event", value_name="companies")).mark_line(point=True).encode(
            x=alt.X("year:O", title="Year"), y="companies:Q", color=alt.Color("event:N", title="")),
        width="stretch")
    st.altair_chart(
        alt.Chart(reg[reg.industry_section != "?"]).mark_bar().encode(
            x=alt.X("year:O", title="Year"), y=alt.Y("registrations:Q"), color=alt.Color("industry_section_name:N", title="Industry")),
        width="stretch")
    st.caption("From PRH open data. Companies removed from the register long ago are missing, so older years are undercounted.")
    age = q("select * from marts.mart_company_age_trend")
    st.altair_chart(line(age, "share_of_national_tax", "Share of national tax by company age", color="age_band", fmt="%"), width="stretch")
    form = q("select * from marts.mart_company_form_trend")
    st.altair_chart(line(form, "total_tax", "Tax imposed by company form (€)", color="company_form"), width="stretch")

with tabs[4]:
    pick = st.selectbox("Year", years[::-1], key="top_year")
    top = q("select * from marts.mart_top_taxpayers where tax_year = ? order by rank_in_year", (pick,))
    st.dataframe(top[["rank_in_year", "rank_previous_year", "company_name", "business_id", "industry_section_name",
                      "municipality", "tax_imposed", "taxable_income"]], hide_index=True)

with tabs[5]:
    st.dataframe(q("select * from marts.mart_data_quality"), hide_index=True)
    st.markdown("**Corrections to published figures**")
    st.dataframe(q("select * from marts.mart_revisions_trend"), hide_index=True)
    st.markdown("**How each year's source columns were mapped**")
    st.dataframe(q("select tax_year, column_position, source_header, canonical_column from staging.stg_vero__header_profile order by tax_year, column_position"), hide_index=True)

with tabs[6]:
    st.subheader("About this project")
    st.markdown(
        f"""
This dashboard tracks corporate income tax in Finland and the companies behind it, year by year.
It joins two public datasets on the Business ID (Y-tunnus):

- **Finnish Tax Administration (Vero):** every corporate taxpayer's name, home municipality,
  taxable income and tax imposed, published each November. Tax years loaded here: **{years[0]} to {years[-1]}**.
- **Finnish Patent and Registration Office (PRH):** the Trade Register, with company form,
  industry (TOL 2008), registration and end dates, and bankruptcy and liquidation events.

**How it is built.** A Python ingestion layer downloads the files, maps each year's column names to one
schema (they change between years), validates every Business ID with its check digit and loads everything
into DuckDB. dbt then models one row per company per tax year, joins the register, and builds the trend
tables shown in the other tabs. Tests run on every build, and GitHub Actions refreshes the data from the
original sources.

**Read the numbers carefully.**
- Taxable income is not profit, and zero tax is often legitimate (losses, losses carried forward).
- Housing companies and mutual real estate companies are not in Vero's open data.
- Industry is the company's current industry, applied to every year.
- Municipality is the home municipality on Vero's list, not where the activity happens.
- The register's open data misses companies removed long ago, so older register counts are lower bounds.
- Vero currently publishes tax years 2020 onward online; older years are added when available.

**Sources and licence.** Data: Finnish Tax Administration and Finnish Patent and Registration Office,
CC BY 4.0. Code: MIT licence.

**Author.** Built by Samwel Munyingi.
[GitHub](https://github.com/munyingi/Bussiness-operations) ·
[LinkedIn](https://www.linkedin.com/in/samwel-munyingi-352a88161)
"""
    )
