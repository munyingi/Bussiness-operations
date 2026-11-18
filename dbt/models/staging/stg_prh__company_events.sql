select
    business_id,
    situation,
    case situation
        when 'KONK' then 'bankruptcy'
        when 'SELTILA' then 'liquidation'
        when 'SANE' then 'restructuring'
        else 'other'
    end                                   as situation_name,
    try_cast(start_date as date)          as start_date,
    try_cast(end_date as date)            as end_date
from {{ source('raw', 'prh_company_events') }}
