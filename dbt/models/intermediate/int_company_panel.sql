-- One row per company: how it moves through the 15-year panel.
-- "Entry" = first year it appears in Vero data, "exit" = last year it appears.
-- Appearing in the first or last panel year is censored, not a real entry/exit.

with bounds as (
    select min(tax_year) as panel_start, max(tax_year) as panel_end
    from {{ ref('int_company_years') }}
),

per_company as (
    select
        business_id,
        any_value(company_name)                    as company_name,
        any_value(industry_section)                as industry_section,
        any_value(register_status)                 as register_status,
        any_value(registration_year)               as registration_year,
        min(tax_year)                              as first_year,
        max(tax_year)                              as last_year,
        count(*)                                   as years_present,
        count(*) filter (where not is_zero_tax)    as years_paying,
        sum(tax_imposed)                           as lifetime_tax
    from {{ ref('int_company_years') }}
    group by 1
)

select
    c.*,
    c.first_year > b.panel_start                   as is_observed_entry,
    c.last_year < b.panel_end                      as is_observed_exit,
    c.years_present < (c.last_year - c.first_year + 1) as has_gaps
from per_company c
cross join bounds b
