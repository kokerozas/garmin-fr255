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

## D-013 — Backfill histórico desde el export de cuenta Garmin
- **Estado:** aceptada (2026-08-02)
- **Fuente:** `data/raw/export/solicitud_datos.zip` (export oficial "Exportar tus datos", 34.7 MB). Se lee DIRECTO del ZIP sin descomprimir: el ZIP es el raw inmutable. Jorge lo había dejado en la raíz del repo → se movió bajo `data/` de inmediato (git no debe ver datos de salud).
- **Backfill:** 1.327 días rellenados en `daily_metrics` (2023-10-25 → 2026-07-21): FC reposo oficial (843 días), sueño con etapas y puntaje (571 noches desde jul-2023), estrés, pasos, Body Battery, VO2max (46 mediciones, rango 45-50). Política de fusión: el export RELLENA nulos, nunca pisa lo que ya midió el reloj. Nueva tabla `race_predictions` (2.956 predicciones 5K/10K/21K/42K).
- **Actividades históricas:** +50 insertadas desde `summarizedActivities.json` (2023-10-25 → 2024-05, era pre-retención del reloj), con dedupe por hora de inicio ±120 s (las 193 del reloj se detectaron y omitieron). Sin series 1s → TRIMP por método `session_avg`. Serie `daily_load` extendida a **1.013 días** (2023-10-25 → hoy).
- **Esquema:** migraciones aditivas idempotentes (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) para `resting_hr`, `vo2max`, `body_battery_max/min`.
- **Dashboard:** Recuperación con selector de rango (90d/6m/1a/Todo), FC en reposo real (COALESCE oficial→proxy), gráfico VO2max.
- **Backlog:** FITs originales antiguos de `Uploaded-Files` (darían series 1s a las 50 históricas), Body Battery y predicciones de carrera como gráficos, `MetricsAcuteTrainingLoad` de Garmin como referencia comparativa vs nuestro ATL.
- **Verificación:** pytest 12/12 · dedupe verificado (0 duplicados) · cobertura por año validada · capturas revisadas.

## D-014 — Guías por panel y motor de recomendaciones
- **Estado:** aceptada (2026-08-02)
- **Guías (src/garmin/guides.py):** botón ℹ️ "¿Cómo leer este panel?" en los 14 paneles de las 3 vistas — qué muestra, cómo se calcula, qué mirar y señales de alerta, en términos técnicos e intuitivos.
- **Recomendaciones (src/garmin/metrics/recommendations.py):** motor de reglas TRANSPARENTES (sin caja negra) sobre el estado actual: ACWR (>1.5 alerta, 1.3-1.5 precaución, <0.8 subcarga), parones (≥10 días → protocolo de regreso gradual), TSB<-25, monotonía de Foster (>2.0), HRV bajo banda personal, sueño reciente <6.5 h, FC reposo +5 ppm sobre norma de 28 días. Cada recomendación cita el dato que la disparó; siempre incluye la regla fija del dolor (el sistema no lo ve) y disclaimer no-médico. Sección "🧭 Recomendaciones de la semana" en Semana y carga.
- **Verificación HRV (pregunta de Jorge):** confirmado con evidencia triple que el HRV existe solo desde 2026-07-18 — 0 archivos HRV en los 140 del export, 0 campos HRV en los JSON de sueño, primer HRVStatus del reloj = 18-jul. No es bug: el dato nació ese día y crece con cada sincronización.
- **Verificación:** pytest 16/16 · recomendaciones probadas sobre estado real (disparó correctamente "regreso gradual, 13 días" y "sueño corto 4.3 h") · capturas revisadas.

## D-015 — Registro subjetivo (RPE + molestias) y tarjeta pre-partido
- **Estado:** aceptada (2026-08-02, alineación de rumbo: preguntas ①③⑤)
- **wellness_log:** RPE 0-10 (Foster) + molestias 0-10 en 7 zonas de fútbol (isquios, cuádriceps, gemelos/sóleo, aductores, rodilla, tobillo/pie, espalda baja) + duración + nota. Upsert por sesión (log_id `a:<actividad>` o `d:<fecha>`). Carga **sRPE = RPE × minutos** como segunda vara junto al TRIMP.
- **Vista "Registrar sesión":** formulario de 30 s (sesiones de los últimos 21 días o registro general) + tabla de últimos registros con sRPE.
- **Motor de recomendaciones ampliado:** dolor ≥7 → alerta (no se juega); misma zona ≥4 en ≥2 registros → molestia recurrente (evitar sprints máximos); molestia ≥4 + ACWR ≥1.3 → combo pre-lesión típico.
- **Tarjeta "¿Puedo jugar hoy?"** al tope de Semana y carga: semáforo global + 3 factores (Carga: ACWR/parones · Recuperación: sueño/HRV/FC reposo · Molestias: registros de 7 días), cada uno con su razón en una línea. Diseñada para leerse en 5 s el día de partido (uso real declarado por Jorge).
- **Verificación:** pytest 19/19 (upsert, sRPE, recurrencia, combos, semáforo en sano/dolor/parón) · smoke test y capturas · con el estado real de Jorge la tarjeta marcó 🔴 por sus 13 días de parón — coherente con las recomendaciones.
