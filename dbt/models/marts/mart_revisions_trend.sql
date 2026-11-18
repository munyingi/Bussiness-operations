-- Corrections to already published assessments, per tax year.

select
    tax_year,
    count(*)                                   as n_revised_company_years,
    sum(original_tax_imposed)                  as original_tax,
    sum(revised_tax_imposed)                   as revised_tax,
    sum(tax_delta)                             as net_tax_delta,
    count(*) filter (where tax_delta > 0)      as n_increased,
    count(*) filter (where tax_delta < 0)      as n_decreased
from {{ ref('int_assessment_revisions') }}
group by 1
order by 1
