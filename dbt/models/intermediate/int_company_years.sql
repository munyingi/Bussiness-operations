-- The core fact: one row per company per tax year, enriched with the PRH
-- register, industry section and statutory rate.

with vero as (
    select
        tax_year,
        business_id,
        any_value(company_name)                      as vero_name,
        upper(trim(any_value(municipality)))         as municipality_key,
        any_value(municipality_code)                 as vero_municipality_code,
        sum(taxable_income)                          as taxable_income,
        sum(tax_imposed)                             as tax_imposed,
        count(*)                                     as source_rows
    from {{ ref('stg_vero__assessments') }}
    where is_valid_business_id
    group by 1, 2
),

prh as (
    select * from {{ ref('stg_prh__companies') }}
),

sections as (
    select * from {{ ref('tol2008_sections') }}
)

select
    v.tax_year,
    v.business_id,
    coalesce(p.company_name, v.vero_name)                         as company_name,
    v.municipality_key,
    upper(left(v.municipality_key, 1)) || lower(substr(v.municipality_key, 2))                          as municipality,
    v.taxable_income,
    v.tax_imposed,
    v.tax_imposed = 0                                             as is_zero_tax,
    case when v.taxable_income > 0 then v.tax_imposed / v.taxable_income end as effective_ratio,
    r.statutory_rate,
    r.regime,
    p.business_id is not null                                     as in_trade_register,
    case
        when p.business_id is null then 'not_in_trade_register'
        when p.is_dissolved then 'dissolved'
        else 'active'
    end                                                           as register_status,
    p.company_form,
    p.industry_code,
    p.industry_division,
    coalesce(s.section, '?')                                      as industry_section,
    coalesce(s.section_name, 'Unknown industry')                  as industry_section_name,
    p.registration_date,
    year(p.registration_date)                                     as registration_year,
    v.tax_year - year(p.registration_date)                        as company_age_years,
    p.end_date,
    v.source_rows
from vero v
left join prh p on p.business_id = v.business_id
left join sections s
    on p.industry_division between s.division_from and s.division_to
left join {{ ref('corporate_tax_rates') }} r on r.tax_year = v.tax_year
