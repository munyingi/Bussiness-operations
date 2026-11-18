-- The 25 largest corporate taxpayers each year, with last year's rank.

with ranked as (
    select
        tax_year,
        business_id,
        company_name,
        industry_section_name,
        municipality,
        tax_imposed,
        taxable_income,
        rank() over (partition by tax_year order by tax_imposed desc) as rank_in_year
    from {{ ref('int_company_years') }}
    where tax_imposed > 0
)

select
    r.*,
    prev.rank_in_year                                         as rank_previous_year,
    r.tax_imposed / sum(r.tax_imposed) over (partition by r.tax_year) as share_of_top25_tax
from ranked r
left join ranked prev on prev.business_id = r.business_id and prev.tax_year = r.tax_year - 1
where r.rank_in_year <= 25
