-- Company register trend from PRH: registrations, dissolutions and
-- bankruptcies started, per year and industry. PRH open data holds companies
-- currently in the Trade Register (incl. those with an end date), so counts
-- for older years are lower bounds.

with sections as (select * from {{ ref('tol2008_sections') }}),

companies as (
    select p.*, coalesce(s.section, '?') as industry_section, coalesce(s.section_name, 'Unknown industry') as industry_section_name
    from {{ ref('stg_prh__companies') }} p
    left join sections s on p.industry_division between s.division_from and s.division_to
),

registrations as (
    select year(registration_date) as year, industry_section, industry_section_name, count(*) as registrations
    from companies where registration_date is not null group by 1, 2, 3
),

dissolutions as (
    select year(end_date) as year, industry_section, industry_section_name, count(*) as dissolutions
    from companies where end_date is not null group by 1, 2, 3
),

bankruptcies as (
    select year(e.start_date) as year, c.industry_section, c.industry_section_name, count(distinct e.business_id) as bankruptcies_started
    from {{ ref('stg_prh__company_events') }} e
    join companies c using (business_id)
    where e.situation = 'KONK' and e.start_date is not null
    group by 1, 2, 3
)

select
    year,
    industry_section,
    industry_section_name,
    coalesce(r.registrations, 0)                                   as registrations,
    coalesce(d.dissolutions, 0)                                    as dissolutions,
    coalesce(b.bankruptcies_started, 0)                            as bankruptcies_started,
    coalesce(r.registrations, 0) - coalesce(d.dissolutions, 0)     as net_change
from registrations r
full outer join dissolutions d using (year, industry_section, industry_section_name)
full outer join bankruptcies b using (year, industry_section, industry_section_name)
where year >= 2000
