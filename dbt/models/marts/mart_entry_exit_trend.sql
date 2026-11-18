-- Companies entering and leaving the corporate tax data each year.
-- Entry cannot be measured in the first panel year, nor exit in the last,
-- so those cells are null rather than zero.

with years as (select distinct tax_year from {{ ref('int_company_years') }}),
bounds as (select min(tax_year) as first_y, max(tax_year) as last_y from years)

select
    y.tax_year,
    case when y.tax_year > any_value(b.first_y)
         then count(*) filter (where p.first_year = y.tax_year and p.is_observed_entry) end as entrants,
    case when y.tax_year < any_value(b.last_y)
         then count(*) filter (where p.last_year = y.tax_year and p.is_observed_exit) end   as exits,
    entrants - exits                                                                         as net_entry
from years y
cross join bounds b
cross join {{ ref('int_company_panel') }} p
group by 1
order by 1
