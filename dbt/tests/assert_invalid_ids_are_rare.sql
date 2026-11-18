-- Warn-level sanity check: more than 1% invalid Business IDs in a year
-- usually means a parsing problem, not bad source data.
{{ config(severity='warn') }}

select tax_year, source_rows, invalid_business_ids
from {{ ref('mart_data_quality') }}
where invalid_business_ids > 0.01 * source_rows
