{# Generic test: the combination of columns is unique. Kept local so the
   project needs no dbt packages (forks run with zero setup). #}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
