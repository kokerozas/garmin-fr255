# garmin-fr255 — Análisis de datos End-to-End (Garmin Forerunner 255)

Solución de análisis de datos de extremo a extremo para el Garmin Forerunner 255:
ingesta y estructuración de archivos FIT/TCX, almacenamiento en una base de datos
optimizada, cálculo de métricas avanzadas de rendimiento y dashboard interactivo
para monitorizar variables biomecánicas y fisiológicas.

**Estado:** MVP v0 funcionando — pipeline FIT → DuckDB → métricas de carga → dashboard Streamlit.
Decisiones D-001 a D-011 en `docs/decisions.md`.

## Estructura

```
garmin-fr255/
├── config/                  # Configuración (zonas FC, umbrales, rutas). settings.yaml NO se versiona.
├── data/                    # Datos locales — NUNCA se sube a Git (privacidad de datos de salud)
│   ├── raw/fit/             # Archivos .fit originales del reloj (inmutables)
│   ├── raw/tcx/             # Exportaciones .tcx de Garmin Connect (inmutables)
│   ├── interim/             # Datos parseados, previos a validación (p. ej. parquet)
│   ├── processed/           # Datos limpios y validados, listos para carga
│   └── db/                  # Base de datos local
├── src/garmin/              # Paquete Python del pipeline
│   ├── ingest/              # Lectura de FIT/TCX y (opcional) descarga desde Garmin Connect
│   ├── transform/           # Limpieza, normalización, modelado sesión/samples
│   ├── db/                  # Esquema, carga y consultas de la base de datos
│   ├── metrics/             # Métricas derivadas: carga, eficiencia, dinámica de carrera
│   └── utils/               # Utilidades compartidas
├── dashboard/               # Aplicación de visualización interactiva
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

## Puesta en marcha

### Windows (primera vez)

1. Instalar Python 3.11+ desde [python.org](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"**.
2. Abrir una terminal en esta carpeta y crear el entorno:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Uso (cada semana, tras dejar los FIT nuevos en data\raw\fit)

```bat
.venv\Scripts\activate
python scripts\ingest.py            & :: procesa lo nuevo y recalcula métricas
streamlit run dashboard\app.py      & :: abre el dashboard en el navegador
```

En Linux/macOS: `make ingest` y `make dashboard` (mismos pasos con `python -m venv .venv && source .venv/bin/activate`).

La ingesta es **incremental e idempotente**: se puede correr mil veces; solo procesa archivos que no ha visto (hash del contenido).
