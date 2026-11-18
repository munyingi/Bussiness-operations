.PHONY: install sample live dbt test app dbdocs clean

PY ?= python3
DBT = cd dbt && DBT_PROFILES_DIR=. dbt

install:
	$(PY) -m pip install -r requirements.txt

# Synthetic data, no network. Runs in seconds. Good for forks and CI.
sample:
	rm -f data/trends.duckdb
	$(PY) sample_data/generate.py
	$(PY) -m ingestion.run --sample
	$(DBT) build

# Real data from Vero and PRH (needs internet, a few hundred MB).
live:
	rm -f data/trends.duckdb
	$(PY) -m ingestion.run
	$(DBT) build

dbt:
	$(DBT) build

test:
	$(PY) -m pytest -q

app:
	streamlit run app/streamlit_app.py

dbdocs:
	$(DBT) docs generate && $(DBT) docs serve

clean:
	rm -rf data/trends.duckdb dbt/target dbt/logs
