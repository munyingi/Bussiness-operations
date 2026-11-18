-- One row per source row of the Vero corporate tax files, typed and cleaned.
-- Rows with an invalid Business ID are kept and flagged, not dropped, so the
-- data quality mart can report them.

select
    cast(tax_year as integer)                               as tax_year,
    business_id,
    business_id_raw,
    business_id is not null                                 as is_valid_business_id,
    nullif(trim(name), '')                                  as company_name,
    nullif(trim(municipality), '')                          as municipality,
    lpad(nullif(trim(municipality_code), ''), 3, '0')       as municipality_code,
    coalesce(taxable_income, 0)::decimal(18, 2)             as taxable_income,
    coalesce(tax_imposed, 0)::decimal(18, 2)                as tax_imposed,
    prepayments::decimal(18, 2)                             as prepayments,
    residual_tax::decimal(18, 2)                            as residual_tax,
    tax_refund::decimal(18, 2)                              as tax_refund,
    source_file
from {{ source('raw', 'vero_assessments') }}
