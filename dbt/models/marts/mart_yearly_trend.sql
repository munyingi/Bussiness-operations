-- National corporate tax trend: one row per tax year.

with ranked as (
    select
        tax_year,
        taxable_income,
        tax_imposed,
        statutory_rate,
        in_trade_register,
        row_number() over (partition by tax_year order by tax_imposed desc) as rank_desc,
        count(*) over (partition by tax_year)                               as n
    from {{ ref('int_company_years') }}
),

yearly as (
    select
        tax_year,
        any_value(statutory_rate)                                             as statutory_rate,
        count(*)                                                              as n_taxpayers,
        count(*) filter (where tax_imposed > 0)                               as n_paying,
        sum(taxable_income)                                                   as total_taxable_income,
        sum(tax_imposed)                                                      as total_tax,
        median(taxable_income) filter (where taxable_income > 0)              as median_taxable_income_of_payers,
        sum(tax_imposed) filter (where rank_desc <= greatest(1, n * 0.01))    as top1pct_tax,
        sum(tax_imposed) filter (where rank_desc <= greatest(1, n * 0.10))    as top10pct_tax,
        avg(case when in_trade_register then 1 else 0 end)                    as share_in_trade_register
    from ranked
    group by 1
)

select
    *,
    n_paying / n_taxpayers                                                    as paying_share,
    total_tax / nullif(n_paying, 0)                                           as avg_tax_per_payer,
    top1pct_tax / nullif(total_tax, 0)                                        as top1pct_share,
    top10pct_tax / nullif(total_tax, 0)                                       as top10pct_share,
    total_tax / nullif(lag(total_tax) over (order by tax_year), 0) - 1        as total_tax_yoy,
    n_taxpayers / nullif(lag(n_taxpayers) over (order by tax_year), 0) - 1    as n_taxpayers_yoy
from yearly
order by tax_year
