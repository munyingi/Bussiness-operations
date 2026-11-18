-- Corporate tax by industry (TOL 2008 section) and year. Industry comes from
-- the PRH register, so taxpayers not in the Trade Register show as '?'.

with base as (
    select
        tax_year,
        industry_section,
        industry_section_name,
        count(*)                                     as n_taxpayers,
        count(*) filter (where tax_imposed > 0)      as n_paying,
        sum(taxable_income)                          as total_taxable_income,
        sum(tax_imposed)                             as total_tax
    from {{ ref('int_company_years') }}
    group by 1, 2, 3
)

select
    *,
    n_paying / n_taxpayers                                                              as paying_share,
    total_tax / sum(total_tax) over (partition by tax_year)                             as share_of_national_tax,
    total_tax / nullif(lag(total_tax) over (partition by industry_section order by tax_year), 0) - 1 as total_tax_yoy
from base
