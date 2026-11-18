-- PRH Trade Register companies. Note: the open data covers companies in the
-- Trade Register only. Associations, foundations and many entities that
-- dissolved long ago are not here, which is why the Vero join is a LEFT join.

select
    business_id,
    nullif(trim(name), '')                                       as company_name,
    company_form,
    company_form_desc,
    industry_code,
    industry_desc,
    try_cast(left(industry_code, 2) as integer)                  as industry_division,
    try_cast(registration_date as date)                          as registration_date,
    try_cast(business_id_registration_date as date)              as business_id_registration_date,
    try_cast(end_date as date)                                   as end_date,
    end_date is not null                                         as is_dissolved,
    status,
    trade_register_status,
    post_code,
    city,
    lpad(municipality_code, 3, '0')                              as municipality_code,
    try_cast(last_modified as timestamp)                         as last_modified
from {{ source('raw', 'prh_companies') }}
where business_id is not null
