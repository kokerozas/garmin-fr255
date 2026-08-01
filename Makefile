.PHONY: ingest rebuild dashboard test

# Atajos operativos del proyecto. Se implementaran junto con el pipeline.

ingest:      ## Procesar archivos nuevos de data/raw/ hacia la base de datos
	@echo "Pendiente: scripts/ingest.py"

rebuild:     ## Reconstruir la base de datos completa desde data/raw/
	@echo "Pendiente: scripts/rebuild_db.py"

dashboard:   ## Levantar el dashboard Streamlit
	@echo "Pendiente: dashboard/app.py"

test:        ## Ejecutar tests
	@echo "Pendiente: pytest"
