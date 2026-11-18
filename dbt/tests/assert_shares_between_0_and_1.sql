select tax_year, top1pct_share, top10pct_share, paying_share
from {{ ref('mart_yearly_trend') }}
where top1pct_share not between 0 and 1
   or top10pct_share not between 0 and 1
   or paying_share not between 0 and 1
   or top1pct_share > top10pct_share
