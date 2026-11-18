-- Fails if any Vero file is missing a required column after header mapping.
-- This is the guard against silent schema drift in a new year's file.

with required as (
    select unnest(['business_id', 'taxable_income', 'tax_imposed']) as canonical_column
),

files as (
    select distinct source_file from {{ ref('stg_vero__header_profile') }}
)

select f.source_file, r.canonical_column
from files f
cross join required r
left join {{ ref('stg_vero__header_profile') }} h
    on h.source_file = f.source_file and h.canonical_column = r.canonical_column
where h.canonical_column is null
