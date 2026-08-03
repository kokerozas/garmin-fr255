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

## D-016 — REGLA TRANSVERSAL: rigor científico, nada inventado
- **Estado:** aceptada (2026-08-02, declarada por Jorge para TODO el proyecto)
- **Regla:** toda métrica, análisis o visualización avanzada sigue un framework científico publicado. Cada métrica se implementa SOLO con referencia primaria + limitaciones documentadas en `docs/metodologia.md` (creado en esta decisión: Banister/Morton TRIMP · Williams EWMA · Hulin/Gabbett ACWR con críticas de Impellizzeri · Foster monotonía y sRPE · ACSM/Seiler zonas · Plews/Buchheit HRV y FC reposo · Milewski/von Rosen sueño · Saw/Clarsen autorreporte). Los valores de Garmin se tratan como mediciones de tercero (referencia, no verdad). Las guías ℹ️ deben ser consistentes con la metodología.
- **Auditoría retroactiva:** todas las métricas ya implementadas (D-007, D-011, D-012, D-014, D-015) quedaron mapeadas a su literatura — ninguna era inventada.
- **Además:** se creó `CLAUDE.md` en la raíz: guía del proyecto para cualquier sesión de Claude (Cowork, Claude Code CLI o web) con arquitectura, invariantes, comandos y esta regla como suprema. El repo queda auto-descriptivo.
## D-017 — HALLAZGOS DE AUDITORÍA: lo que los datos reales dijeron
- **Estado:** aceptada (2026-08-02, auditoría de `garmin.duckdb` sobre las 10 tablas)
- **Por qué existe esta entrada:** antes de implementar métricas nuevas se auditó la base real. Tres hallazgos
  cambiaron el diseño de la iteración y deben quedar registrados aunque no sean "código".
- **① El perfil Fútbol NO graba a 1 Hz.** Intervalo mediano entre muestras = **2.74 s** (mín 2.04, máx 25.9);
  cero de las 96 sesiones de fútbol baja de 1.5 s. El reloj está en *Smart Recording* para ese perfil, mientras
  que "Carrera" y "Trail" sí están a 1.00 s exacto. Consecuencia: un sprint de fútbol dura 2-4 s y cae dentro de
  1-2 muestras — **no se puede reconstruir**. Las métricas de alta velocidad (HSR, conteo de sprints,
  aceleraciones) quedan DESHABILITADAS por diseño, no por falta de código. Los 96 partidos históricos no son
  reparables: el reloj descartó las muestras en origen.
  **Acción para Jorge:** en el reloj, *Configuración > Sistema > Grabación de datos > Cada segundo*. Desde ese
  día las sesiones nuevas se graban a 1 Hz y esas métricas se activan solas.
- **② La velocidad cruda tiene ruido puro.** En fútbol el percentil 99 es 12.12 m/s (43.6 km/h) y el máximo
  31.67 m/s (**114 km/h**). Se implementa limpieza `speed_valid`/`speed_flag` espejo de la de FC (D-008): se
  MARCA, jamás se borra.
- **③ Déficit de sueño crónico.** Media del último año: **5.41 ± 1.63 h** (n=169), con 82 % de noches bajo 7 h
  y 94 % bajo 8 h. Es el hallazgo de salud más accionable del proyecto y el de mejor respaldo en la literatura
  (Milewski 2014: <8 h → 1.7× lesiones). Cautela: el sueño de reloj de muñeca *sobreestima* frente a
  polisomnografía, así que 5.4 h medidas son probablemente menos de 5.4 h reales.
- **Otros:** `wellness_log` con 0 filas (D-015 construido pero sin uso aún) · 90 de 96 partidos con un solo lap
  (no hay marcador de medio tiempo: las mitades se parten por tiempo) · `laps.avg_speed_ms` 100 % vacía.

## D-018 — Métricas nuevas: el reencuadre científico de la carga y la recuperación
- **Estado:** aceptada (2026-08-02, tras investigación de literatura 2013-2025 con 73 hallazgos referenciados)
- **① El ACWR baja de categoría (el cambio conceptual más importante).** Impellizzeri et al. (2021,
  *Sports Medicine* 51(3):581-592) sustituyeron la carga crónica por valores **aleatorios** y el ACWR siguió
  asociándose con lesión igual de bien: la asociación no venía del cociente. Lolli et al. (2019, BJSM) muestran
  el acoplamiento matemático, y el único ECA existente (Dalen-Lorentsen 2021, BJSM, 482 futbolistas juveniles,
  10 meses) no encontró diferencia al planificar con ACWR. **Decisión:** la carga aguda ABSOLUTA de 7 días y su
  **percentil personal** pasan a primer plano; el ACWR se conserva como señal descriptiva secundaria, con su
  guía ℹ️ reescrita. No se elimina — se le quita el rol de oráculo.
- **② Cambio semana-a-semana y cargas acumuladas** 14/21/28 d (Rogalski 2013; Cross 2016), con el umbral de
  "2 DE" individualizado contra la propia variabilidad de Jorge en vez de importar los AU de rugby.
- **③ Bandas personales en vez de umbrales importados.** La regla "+5 ppm de FC en reposo" se jubila: con la DE
  real de Jorge (3.6 ppm) equivalía a 1.4 DE, entre 3 y 5 veces más insensible que el estándar. Se reemplaza por
  el *smallest worthwhile change* = media 28 d ± 0.5 × DE (Hopkins 2000; Buchheit 2014).
- **④ Deuda de sueño acumulada** 7/14/28 d (Milewski 2014; von Rosen 2017), con una regla dura: **una noche sin
  dato no es deuda cero** — se exige mínimo de noches válidas y se muestra el % de cobertura junto al número.
- **⑤ Índice de disposición por dominios** (autonómico / sueño / carga / subjetivo) con z-scores individuales
  (Buchheit 2014; Thornton 2019; Robertson 2017). Se agrupa por dominio ANTES de promediar porque `sleep_score`,
  estrés y Body Battery salen del mismo motor propietario de Garmin y promediarlos como iguales le daría triple
  peso a ese bloque. Nunca se imputa: si falta un dato, baja `n_dominios`. **Un conteo de banderas no es un
  modelo de riesgo calibrado**, y así se declara en la interfaz.
- **⑥ Carga externa con portero.** `gps_grade` (alta/media/baja/sin_gps) decide qué se calcula: distancia y
  m/min siempre; HSR y sprints solo con grado alto. Índice de eficiencia metros/TRIMP (Akubat 2014), con la
  desviación declarada de usar TRIMP de Banister en lugar del iTRIMP original.
- **⑦ Fatiga intra-partido** (Mohr 2003): coste cardíaco de la 2ª mitad vs la 1ª, partido por tiempo porque no
  hay marcador de descanso. Serie longitudinal contra sí misma, nunca valor absoluto.
- **⑧ Registro subjetivo validado:** dRPE piernas/respiración (Los Arcos 2014; McLaren 2017) — el **único canal
  disponible para estimar carga neuromuscular** con este hardware, porque la FC de muñeca es ciega a las
  aceleraciones y frenadas que rompen isquios y aductores. Más Hooper de 4 ítems (Hooper 1995) y OSTRC-H2
  condicional a las zonas ya marcadas (Clarsen 2013). Los ítems se analizan por separado con z-scores, **nunca
  sumados en un índice único** (Duignan 2020). Lista de exclusión deliberada: no se pregunta lo que el reloj ya
  mide mejor (horas de sueño, FC de reposo, pasos, duración).
- **Criterio de adherencia como requisito de diseño:** <30 segundos o se abandona (Saw 2015). El tiempo de
  registro se mide y se grafica; si sube, el formulario está creciendo demasiado.
- **Toda la ciencia, con limitaciones, en `docs/metodologia.md`.**

## D-019 — Sistema de visualización: jerarquía, bandas personales y la regla del 3D
- **Estado:** aceptada (2026-08-02, respuesta a la pregunta de Jorge sobre gráficas 3D)
- **La regla del 3D, en tres líneas:**
  1. Dato **abstracto** (carga, HRV, molestias) → **2D siempre**.
  2. Dato **intrínsecamente espacial** (ruta GPS con altitud) → **3D justificado** para entender la FORMA,
     nunca para leer valores, y siempre con su equivalente 2D de lectura al lado.
  3. Todo gráfico 3D lleva rótulo visible de exploración y **jamás alimenta el motor de recomendaciones ni la
     tarjeta "¿Puedo jugar hoy?"**.
- **Racional, con los matices que la evidencia exige.** Cleveland & McGill (1984) ordenaron experimentalmente
  los canales perceptuales: posición > longitud > ángulo > área > volumen. El 3D mueve el dato desde "posición"
  hacia "volumen y profundidad", y añade oclusión, distorsión de perspectiva y texto inclinado (Munzner 2014).
  Sedlmair, Munzner & Tory (2013) compararon 816 scatterplots y concluyeron que el scatter 3D interactivo
  "rara vez ayuda y a menudo perjudica". **Pero no es dogma:** Zacks et al. (1998) concluyen que las advertencias
  sobre las claves 3D "pueden estar exageradas" frente al efecto del contexto gráfico, y Siegrist (1996) no
  halló pérdida de precisión en barras 3D (sí en quesos 3D). Y St. John et al. (2001), con seis experimentos,
  mostraron que el 3D **sí gana** cuando la tarea es comprender una forma tridimensional real.
  **Conclusión honesta: el 3D no es un crimen, es un impuesto** — cuesta tiempo de lectura y algo de precisión,
  y hay que preguntarse qué compra a cambio. Para carga y recuperación no compra nada; para un cerro, sí.
- **Casos concretos resueltos:** superficie 3D de carga×tiempo **descartada** (la carga en el tiempo es
  univariada: obliga a inventar un segundo eje) → se reemplaza por **heatmap de calendario** (van Wijk & van
  Selow 1999), que codifica las mismas variables con ambas dimensiones temporales en posición.
  Scatter 3D carga-recuperación-molestias → se implementa como **juguete de exploración rotulado**, y su
  alternativa 2D honesta es el scatter con color y tamaño (4 variables, las 2 más importantes en posición).
  Ruta GPS con altitud → **3D implementado**, con `aspectmode='data'` para no exagerar el relieve y su perfil 2D
  al lado.
- **Radar descartado para las 7 zonas de molestias** → **dot plot ordenado (dumbbell)**: el radar compara mal
  longitudes en ángulos distintos, su orden de ejes es arbitrario y el área crece con el CUADRADO del valor
  (Few 2005; Cleveland & McGill 1984). El dumbbell usa posición sobre escala común y además muestra el cambio
  respecto al promedio de 28 días.
- **Jerarquía del reporte** (Buchheit 2017, *"Want to see my report, coach?"*): lo accionable arriba, el detalle
  abajo. Bandas de referencia individuales (media móvil ± SWC) como patrón visual central del monitoreo n=1.
- **Librería: se mantiene Plotly** y se activa la interactividad que ya tenía sin usarse (rangeselector,
  rangeslider, `on_select` para drill-down). No se añaden Altair ni ECharts: romperían el sistema de paleta CVD
  centralizado en `viz.py` a cambio de una ganancia marginal.
- **Tema claro y oscuro:** los tokens de color dejan de estar fijos en modo claro; los valores validados CVD del
  modo claro se conservan intactos.

## D-020 — Estado de la iteración: qué quedó construido y verificado
- **Estado:** aceptada (2026-08-03)
- **Backend nuevo:** `metrics/recovery.py` (banda SWC de FC en reposo, deuda de sueño, Ln rMSSD con puerta de
  validez) · `metrics/readiness.py` (z-scores por dominio) · `metrics/load.py` ampliado (carga absoluta,
  percentil personal, cambio semana a semana, monotonía/strain diarios, índice de eficiencia) ·
  `metrics/wellness.py` ampliado (dRPE, Hooper, OSTRC-H2 condicional, adherencia, 4º factor en la tarjeta).
- **Visualización:** `viz.py` pasa de 9 a 21 figuras y gana tema claro/oscuro. Nuevas: heatmap de calendario,
  serie con banda personal, carga absoluta con percentil, dumbbell de molestias, scatter carga-recuperación,
  sparkline, bullet, small multiples, decoupling, ruta 3D, perfil de altitud, scatter 3D de exploración,
  coordenadas paralelas, y el helper de rangeselector.
- **Dashboard:** reorganizado de 4 a 6 vistas siguiendo la jerarquía de Buchheit — **Hoy** (solo lo accionable),
  **Carga**, **Recuperación**, **Registrar** (3 pestañas: post-sesión, matinal, semanal), **Explorar** (los 3D,
  rotulados) y **Detalle**. El botón ℹ️ deja de quedar huérfano: cada gráfico se renderiza junto a su guía.
- **Guías:** de 14 a 34. Reescritas `acwr` (explica su degradación), `fc_reposo` (banda personal) y `sueno`
  (deuda acumulada con los números reales de Jorge).
- **Carga externa y fatiga intra-partido:** `transform/clean.py` gana `flag_speed()` (espejo de la limpieza de
  FC: marca `fuera_de_rango` sobre 9 m/s y `salto_imposible` sobre 6 m/s², comparando siempre contra la última
  muestra confiable) · `metrics/external.py` con `gps_grade` como portero · `metrics/intrasession.py` con el
  decoupling por mitades partidas por tiempo.
- **Verificación:** `pytest` **61/61 en verde** (eran 19) · pipeline completo idempotente sobre datos reales:
  809 días con banda personal de FC, 985 con índice de disposición, 521 ventanas con deuda de sueño calculable,
  193 sesiones con carga externa y 75 partidos con decoupling (media **+4.1 %**, o sea que la segunda mitad
  cuesta en promedio un 4 % más de pulso por metro) · **smoke test de las 6 vistas** contra la base real ·
  **dashboard levantado en navegador** y recorrido vista por vista, incluida la ruta 3D de una actividad con
  677 m de desnivel.
- **La política del portero, comprobada con los datos:** de 193 sesiones con series, solo **41 tienen señal de
  grado alto** (los perfiles de carrera, a 1 Hz); 86 de grado medio, 43 de grado bajo y 23 sin GPS. La distancia
  a alta velocidad se calcula únicamente en esas 41. En la vista de Carga, cuando el rango elegido no contiene
  ninguna sesión de grado alto, el dashboard lo dice explícitamente y explica cómo arreglarlo en el reloj.
- **Dos bugs que solo aparecieron al renderizar** (y que ningún test unitario habría cachado): el cuarto factor
  de la tarjeta devuelve el estado `sin_datos`, que no existía en el diccionario de emojis; y `bool(nan)` es
  `True` en Python, así que la guarda `if hoy.wow_flag:` dejaba pasar los nulos que DuckDB entrega como NaN.
  Ambos corregidos de forma defensiva. Moraleja registrada: para una app de Streamlit, levantar el navegador es
  parte de la verificación, no un lujo.
- **Pendiente para la próxima iteración:** Sleep Regularity Index (exige releer `sleepStartTimestampGMT` /
  `sleepEndTimestampGMT` desde el export — las columnas ya están migradas) · test submáximo estandarizado con
  HRex, que necesita que Jorge adopte un protocolo de 4 minutos · `sync.py` con la API de Garmin (fase 2 D-004).

