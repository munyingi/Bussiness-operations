-- Bitemporal view of the corrections: what was first published for a
-- company-year versus what the latest decision says.

with latest_change as (
    select *
    from {{ ref('stg_vero__changes') }}
    where is_valid_business_id
    qualify row_number() over (
        partition by business_id, tax_year
        order by decision_date desc nulls last
    ) = 1
),

change_counts as (
    select business_id, tax_year, count(*) as n_decisions
    from {{ ref('stg_vero__changes') }}
    where is_valid_business_id
    group by 1, 2
)

select
    c.tax_year,
    c.business_id,
    o.company_name,
    o.industry_section,
    o.taxable_income                                   as original_taxable_income,
    o.tax_imposed                                      as original_tax_imposed,
    c.revised_taxable_income,
    c.revised_tax_imposed,
    c.revised_tax_imposed - o.tax_imposed              as tax_delta,
    c.decision_date                                    as latest_decision_date,
    n.n_decisions,
    o.business_id is null                              as is_orphan_change
from latest_change c
left join {{ ref('int_company_years') }} o
    on o.business_id = c.business_id and o.tax_year = c.tax_year
left join change_counts n
    on n.business_id = c.business_id and n.tax_year = c.tax_year
