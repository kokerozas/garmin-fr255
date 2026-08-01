# garmin-fr255 — Análisis de datos End-to-End (Garmin Forerunner 255)

Solución de análisis de datos de extremo a extremo para el Garmin Forerunner 255:
ingesta y estructuración de archivos FIT/TCX, almacenamiento en una base de datos
optimizada, cálculo de métricas avanzadas de rendimiento y dashboard interactivo
para monitorizar variables biomecánicas y fisiológicas.

**Estado:** kickoff completo — decisiones D-001 a D-009 en `docs/decisions.md`.

## Estructura

```
garmin-fr255/
├── config/                  # Configuración (zonas FC, umbrales, rutas). settings.yaml NO se versiona.
├── data/                    # Datos locales — NUNCA se sube a Git (privacidad de datos de salud)
│   ├── raw/fit/             # Archivos .fit originales del reloj (inmutables)
│   ├── raw/tcx/             # Exportaciones .tcx de Garmin Connect (inmutables)
│   ├── interim/             # Datos parseados, previos a validación (p. ej. parquet)
│   ├── processed/           # Datos limpios y validados, listos para carga
│   └── db/                  # Base de datos local (DuckDB)
├── src/garmin/              # Paquete Python del pipeline
│   ├── ingest/              # Lectura de FIT/TCX y (fase 2) descarga desde Garmin Connect
│   ├── transform/           # Limpieza, normalización, modelado sesión/samples
│   ├── db/                  # Esquema, carga y consultas de la base de datos
│   ├── metrics/             # Métricas derivadas: carga, eficiencia, dinámica de carrera
│   └── utils/               # Utilidades compartidas
├── dashboard/               # Aplicación Streamlit
├── scripts/                 # Puntos de entrada CLI (ingesta incremental, rebuild de la DB)
├── notebooks/               # Exploración y prototipado (no es código de producción)
├── tests/                   # Tests del pipeline y de las métricas
├── docs/                    # Diccionario de datos y registro de decisiones
└── logs/                    # Logs de ejecución — no se versiona
```

## Principios

1. `data/raw/` es inmutable: los archivos del reloj jamás se editan; todo lo derivado se regenera.
2. Todo lo que contiene datos personales o de salud (`data/`, `config/settings.yaml`, `.env`) queda fuera de Git.
3. El código de producción vive en `src/`; los notebooks son solo para explorar.
4. Cada decisión de arquitectura se registra en `docs/decisions.md`.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml   # y ajustar valores
make ingest      # procesar archivos nuevos en data/raw/
make dashboard   # levantar el dashboard
```
