-- Do young or old companies carry the tax base? Age = tax year minus
-- registration year (PRH). Unknown when the company is not in the register.

select
    tax_year,
    case
        when company_age_years is null then 'unknown'
        when company_age_years <= 2 then '0-2 years'
        when company_age_years <= 5 then '3-5 years'
        when company_age_years <= 10 then '6-10 years'
        when company_age_years <= 20 then '11-20 years'
        else '21+ years'
    end                                               as age_band,
    count(*)                                          as n_taxpayers,
    count(*) filter (where tax_imposed > 0)           as n_paying,
    sum(tax_imposed)                                  as total_tax,
    sum(tax_imposed) / sum(sum(tax_imposed)) over (partition by tax_year) as share_of_national_tax
from {{ ref('int_company_years') }}
group by 1, 2
