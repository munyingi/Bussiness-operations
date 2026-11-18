-- The pipeline's own report card per tax year: rows, invalid Business IDs,
-- duplicates, match rate to the PRH register and the header layout used.

with rows as (
    select
        tax_year,
        count(*)                                           as source_rows,
        count(*) filter (where not is_valid_business_id)   as invalid_business_ids,
        count(*) - count(distinct business_id)
            - count(*) filter (where not is_valid_business_id) as duplicate_rows
    from {{ ref('stg_vero__assessments') }}
    group by 1
),

match as (
    select
        tax_year,
        count(*)                                       as company_years,
        avg(case when in_trade_register then 1 else 0 end) as share_in_trade_register
    from {{ ref('int_company_years') }}
    group by 1
),

headers as (
    select
        tax_year,
        string_agg(coalesce(canonical_column, '?' || source_header), ' | ' order by column_position) as layout,
        count(*) filter (where is_unmapped)                                               as unmapped_columns
    from {{ ref('stg_vero__header_profile') }}
    where kind = 'assessment'
    group by 1
)

select
    r.tax_year,
    r.source_rows,
    r.invalid_business_ids,
    r.duplicate_rows,
    m.company_years,
    m.share_in_trade_register,
    h.unmapped_columns,
    h.layout,
    dense_rank() over (order by h.layout)  as layout_id
from rows r
left join match m using (tax_year)
left join headers h using (tax_year)
order by r.tax_year
