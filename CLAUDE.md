# CLAUDE.md — Guía del proyecto para sesiones de Claude

Proyecto: **análisis end-to-end del Garmin Forerunner 255 de Jorge** (fútbol +
multideporte). Prioridad #1: **prevención de lesiones**. Todo el contexto vivo
está en `docs/decisions.md` (D-001…D-016) — leerlo antes de tocar nada.

## Regla suprema del proyecto (D-016)

**Toda métrica, análisis o visualización avanzada sigue un framework científico
publicado. NO SE INVENTA NADA.** Cada métrica nueva se implementa solo si tiene
referencia primaria citada en `docs/metodologia.md`, con sus limitaciones
documentadas. Las guías ℹ️ del dashboard deben reflejar esa metodología.

## Arquitectura (D-001, D-002)

```
data/raw/        FIT del reloj + monitoring + export ZIP de cuenta — INMUTABLE, jamás a git
src/garmin/      ingest/ · transform/ · db/ · metrics/ · viz.py · guides.py
scripts/         ingest.py (pipeline completo, incremental e idempotente)
dashboard/       app.py (Streamlit, 4 vistas)
data/db/         garmin.duckdb (regenerable 100% desde raw)
docs/            decisions.md (ADR) · metodologia.md (ciencia) · data_dictionary.md
tests/           pytest — SIEMPRE en verde antes de entregar
```

## Invariantes que NUNCA se rompen

1. `data/`, `config/settings.yaml` y `.env` jamás llegan a git (datos de salud).
2. Raw inmutable: la limpieza MARCA (`hr_valid`/`hr_flag`), nunca borra ni edita.
3. Esquema: solo migraciones aditivas (`ADD COLUMN IF NOT EXISTS` en `schema.py`).
4. Ingesta idempotente (hash de archivo / nombre en `ingest_log`).
5. Cada decisión relevante se registra en `docs/decisions.md` con número D-XXX.
6. Colores/paleta del dashboard: sistema validado CVD en `viz.py` — no improvisar colores.
7. Unidades SI internas; presentación en min/km, km/h; fechas locales America/Santiago.

## Comandos (Windows, desde la raíz del repo)

```powershell
.venv\Scripts\activate
python scripts\ingest.py        # procesa lo nuevo y recalcula métricas
streamlit run dashboard\app.py  # dashboard en localhost:8501
python -m pytest tests\ -q      # tests (deben quedar 100% verdes)
```

Tras cada cambio de código: reiniciar Streamlit COMPLETO (cerrar la terminal),
porque Streamlit no recarga los módulos importados.

## Contexto del atleta (no re-preguntar)

FR255 solo reloj (sin banda) · FCmax estimada 182 / FCrep 71 (D-007, override en
`config/settings.yaml`) · historial 2023-10 → hoy (243 actividades, 96+ de fútbol)
· HRV nocturno existe SOLO desde 2026-07-18 (verificado, no es bug) · VO2max 45-50.

## Flujo de trabajo humano

Jorge aprende Git/Python en el camino: explicar cada pieza en términos intuitivos
(estilo de las guías ℹ️). Commits descriptivos en español, uno por unidad de
trabajo. Él ejecuta commit/push en GitHub Desktop.
