.PHONY: ingest rebuild dashboard test

ingest:      ## Procesar archivos nuevos de data/raw/ → DuckDB → métricas
	python scripts/ingest.py

rebuild:     ## Reconstruir la base completa desde data/raw/
	rm -f data/db/garmin.duckdb && python scripts/ingest.py

dashboard:   ## Levantar el dashboard Streamlit
	streamlit run dashboard/app.py

test:        ## Ejecutar tests
	python -m pytest tests/ -q
