-- Corporate tax by company form (OY, OYJ, OK ...) and year.

select
    tax_year,
    coalesce(company_form, 'not in Trade Register')  as company_form,
    count(*)                                          as n_taxpayers,
    count(*) filter (where tax_imposed > 0)           as n_paying,
    sum(taxable_income)                               as total_taxable_income,
    sum(tax_imposed)                                  as total_tax,
    sum(tax_imposed) / sum(sum(tax_imposed)) over (partition by tax_year) as share_of_national_tax
from {{ ref('int_company_years') }}
group by 1, 2
