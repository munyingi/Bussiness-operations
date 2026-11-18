-- Corporate tax by home municipality and year.

with base as (
    select
        tax_year,
        municipality,
        count(*)                                  as n_taxpayers,
        count(*) filter (where tax_imposed > 0)   as n_paying,
        sum(taxable_income)                       as total_taxable_income,
        sum(tax_imposed)                          as total_tax
    from {{ ref('int_company_years') }}
    where municipality is not null
    group by 1, 2
)

select
    *,
    total_tax / sum(total_tax) over (partition by tax_year)                               as share_of_national_tax,
    total_tax / nullif(lag(total_tax) over (partition by municipality order by tax_year), 0) - 1 as total_tax_yoy,
    rank() over (partition by tax_year order by total_tax desc)                           as national_rank
from base
