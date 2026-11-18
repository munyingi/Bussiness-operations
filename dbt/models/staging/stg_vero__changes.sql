-- Corrections to completed assessments. Each row is a decision that replaced
-- the public figures for one company and tax year.

select
    cast(tax_year as integer)                        as tax_year,
    business_id,
    business_id is not null                          as is_valid_business_id,
    coalesce(taxable_income, 0)::decimal(18, 2)      as revised_taxable_income,
    coalesce(tax_imposed, 0)::decimal(18, 2)         as revised_tax_imposed,
    coalesce(
        try_strptime(decision_date, '%Y-%m-%d'),
        try_strptime(decision_date, '%d.%m.%Y')
    )::date                                          as decision_date,
    source_file
from {{ source('raw', 'vero_changes') }}
