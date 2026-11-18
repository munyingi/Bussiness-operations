-- Companies entering and leaving the corporate tax data each year.
-- The first and last years of the panel are censored and show no entry/exit.

with years as (select distinct tax_year from {{ ref('int_company_years') }})

select
    y.tax_year,
    count(*) filter (where p.first_year = y.tax_year and p.is_observed_entry) as entrants,
    count(*) filter (where p.last_year = y.tax_year and p.is_observed_exit)   as exits,
    entrants - exits                                                          as net_entry
from years y
cross join {{ ref('int_company_panel') }} p
group by 1
order by 1
