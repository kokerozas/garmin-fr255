# Registro de decisiones (ADR ligero)

Formato: una entrada por decisión relevante de arquitectura u operación.
Fuente: kickoff con Jorge (2026-08-01), 20 preguntas estratégicas respondidas.

---

## D-001 — Estructura de carpetas del proyecto
- **Estado:** aceptada (2026-08-01)
- **Decisión:** layout tipo data-engineering: `data/` con etapas raw → interim → processed → db (raw inmutable), código en `src/garmin/` separado por responsabilidad (ingest / transform / db / metrics / utils), `dashboard/` aparte, `notebooks/` solo exploración.
- **Racional:** trazabilidad total (todo lo derivado se regenera desde raw), privacidad (data/ fuera de Git) y separación clara entre pipeline y visualización.
- **Excluido a propósito (por ahora):** Docker, CI/CD, orquestadores (Airflow/Prefect), infraestructura cloud. Se incorporan solo si el proyecto lo exige.

## D-002 — Base de datos: DuckDB
- **Estado:** aceptada (2026-08-01, pregunta 9)
- **Decisión:** DuckDB embebida en `data/db/`, con series segundo a segundo + resúmenes por actividad (pregunta 10).
- **Racional:** analítica columnar ideal para samples 1s multideporte, consultas rápidas desde Python/Streamlit, cero servidor que mantener, 100% local (pregunta 11).

## D-003 — Dashboard: Streamlit
- **Estado:** aceptada (2026-08-01, pregunta 18)
- **Decisión:** app Streamlit local con vistas: resumen semanal + carga (con semáforo de riesgo), detalle de actividad; tendencias largas y comparativas en iteraciones siguientes.

## D-004 — Ingesta: híbrida, cadencia semanal
- **Estado:** aceptada (2026-08-01, preguntas 5–7)
- **Decisión:** fase 1 archivos FIT a `data/raw/` con carga de TODO el histórico; fase 2 (post-MVP) automatización vía API no oficial (`garminconnect`/`garth`). Refresco objetivo: semanal.

## D-005 — GitHub como repositorio remoto
- **Estado:** aceptada (2026-08-01)
- **Decisión:** repo privado `kokerozas/garmin-fr255`. Flujo: Claude escribe en el clon local (GitHub Desktop) vía app de escritorio; Jorge hace commit/push. `data/`, `config/settings.yaml` y `.env` excluidos por .gitignore — los datos de salud nunca salen del disco local.

## D-006 — Alcance deportivo: fútbol + multideporte
- **Estado:** aceptada (2026-08-01, preguntas 1–3)
- **Decisión:** se analizan todas las actividades del reloj, con el fútbol como deporte destacado. Objetivo dual: rendimiento + proyecto técnico de portafolio. Prioridad #1 de uso: **prevención de lesiones**.
- **Implicación clave:** la carga de entrenamiento se unifica entre deportes vía métricas basadas en FC (TRIMP), ya que el ritmo no es comparable entre fútbol y running. Registro con reloj solamente (sin banda, pregunta 8) → FC de muñeca: se aplican filtros de picos/artefactos estrictos.

## D-007 — Metodología de métricas: cálculo propio
- **Estado:** aceptada (2026-08-01, preguntas 13–16)
- **Decisión:** métricas recalculadas por nosotros (TRIMP, ATL/CTL/TSB, ratio A:C; luego eficiencia y desacople) con las de Garmin almacenadas como referencia (`aerobic_te`, `anaerobic_te`). Zonas y umbrales **estimados periódicamente desde los datos** (no fijos), con override manual en `config/settings.yaml`. Fisiología completa: carga, FC/zonas/VO2max, HRV, recuperación, sueño y predicción de forma. Biomecánica para economía de carrera + señales de degradación técnica por fatiga.

## D-008 — Calidad de datos: reglas + marcado reversible
- **Estado:** aceptada (2026-08-01, pregunta 19)
- **Decisión:** limpieza automática por reglas (picos FC, rangos imposibles, sin dato), con cada corrección marcada en columnas de auditoría (`hr_valid`, `hr_flag`) y siempre reversible; `data/raw/` jamás se modifica.

## D-009 — Modo de trabajo: MVP iterativo, en pareja
- **Estado:** aceptada (2026-08-01, preguntas 12 y 20)
- **Decisión:** MVP funcional cuanto antes (ingesta manual → DuckDB → Streamlit básico) e iterar por capas. Claude escribe explicando cada pieza para que Jorge domine y pueda mantener el sistema.

## D-010 — Fuente de datos: volcado USB del reloj
- **Estado:** aceptada (2026-08-01)
- **Decisión:** el volcado de la memoria del FR255 (`C:\Users\hp\Claude\Projects\Garmin Connect\GARMIN`) es la fuente inicial. Se extrajo SOLO lo relevante hacia `data/raw/`: Activity → `raw/fit/` (193 actividades, 2024-05-18 → 2026-07-20, 20 MB) · Monitor → `raw/monitoring/monitor/` (46) · Sleep → `raw/monitoring/sleep/` (73) · HRVStatus → `raw/monitoring/hrv/` (10) · Metrics → `raw/monitoring/metrics/` (100). Total: 422 archivos, 23 MB.
- **Excluido:** el resto del volcado (Apps, Backup, Debug, EXPRESS, etc.) es sistema del reloj sin valor analítico y NO entra al proyecto. El volcado se conserva como respaldo hasta validar la primera ingesta; luego puede eliminarse.
- **Nota:** el export completo de la cuenta Garmin queda como opcional, para monitoreo diario profundo (el reloj solo retiene ~46 días de Monitor) y validación del histórico.

## D-011 — MVP v0 construido y verificado
- **Estado:** aceptada (2026-08-02)
- **Componentes:** parser FIT (`fitdecode`), base DuckDB (`activities` 193 · `samples` 243.543 · `laps` · `daily_load` 807 días · `ingest_log` · `params`), limpieza D-008 (1.134 muestras marcadas: sin_dato/fuera_de_rango/pico_artefacto), TRIMP de Banister propio con FCmax/FCrep estimadas desde datos (182/71 ppm), ATL/CTL/TSB (EWMA 7/42d) y ACWR (7d/28d) con semáforo de riesgo, dashboard Streamlit (2 vistas), tests `pytest` (5).
- **Verificación:** 193/193 archivos cargados sin errores; ingesta incremental idempotente por hash; paleta del dashboard validada para accesibilidad (CVD) en modo claro y oscuro; smoke test del servidor Streamlit.
- **Deuda registrada para iterar (D-009):** ingesta de `raw/monitoring/` (sueño, HRV, monitoreo diario), zonas FC y tiempo-en-zona, eficiencia/desacople, tendencias largas y comparativas en el dashboard, `sync.py` con API Garmin (fase 2 D-004), cascadas de picos FC consecutivos en la limpieza.

## D-012 — Iteración 2: recuperación y zonas FC
- **Estado:** aceptada (2026-08-02)
- **Componentes:** ingesta de `raw/monitoring/` → `daily_metrics` (61 días reales: FC continua/mínima 37 días, sueño con puntaje y etapas 50 noches, HRV nocturno 10 días con banda personal); reconstrucción estándar de `timestamp_16`; cada noche se asigna al día en que se despierta; upsert por fecha (varios archivos aportan columnas del mismo día). Tabla `activity_zones`: tiempo en Z1-Z5 (%FCmax de D-007) para 188 actividades. Dashboard: nueva vista **Recuperación** (sueño por etapas, HRV vs banda, FC mínima, estrés) y tiempo-en-zona en Detalle.
- **Excluido:** archivos `Metrics/` (VO2max de Garmin) usan mensajes fuera del perfil FIT público de fitdecode → pospuesto; alternativa natural: obtenerlo vía API en la fase 2 (D-004).
- **Verificación:** pytest 9/9 · pipeline completo idempotente sobre datos reales · capturas del dashboard revisadas.
