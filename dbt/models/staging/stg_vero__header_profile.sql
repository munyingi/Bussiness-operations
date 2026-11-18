select
    source_file,
    kind,
    cast(tax_year as integer)   as tax_year,
    column_position,
    source_header,
    canonical_column,
    canonical_column is null    as is_unmapped
from {{ source('raw', 'vero_header_profile') }}
