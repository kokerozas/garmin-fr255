# Diccionario de datos

Mapa entre los mensajes FIT del Forerunner 255 y las tablas DuckDB (implementado en D-011).

## Fuentes de datos (D-010)

| Origen (reloj) | Destino en el proyecto | Contenido |
|---|---|---|
| `GARMIN/Activity/` | `data/raw/fit/` | Actividades (fútbol, trote, etc.), 1 FIT por sesión |
| `GARMIN/Monitor/` | `data/raw/monitoring/monitor/` | Monitoreo diario: pasos, FC continua, estrés, Body Battery |
| `GARMIN/Sleep/` | `data/raw/monitoring/sleep/` | Sueño |
| `GARMIN/HRVStatus/` | `data/raw/monitoring/hrv/` | Estado HRV nocturno |
| `GARMIN/Metrics/` | `data/raw/monitoring/metrics/` | (no parseable; el VO2max llega por el export, D-013) |
| Export de cuenta (ZIP) | `data/raw/export/` | Historial completo de bienestar + resúmenes de actividades de toda la cuenta |

## Tablas (data/db/garmin.duckdb)

| Tabla | Origen | Contenido |
|---|---|---|
| `activities` | mensaje FIT `session` | 1 fila por actividad: deporte, duración, distancia, FC, TE de Garmin, **TRIMP propio**, calidad FC |
| `samples` | mensajes `record` | Serie ~1 s: FC (+`hr_valid`/`hr_flag` D-008), velocidad, cadencia, altitud, GPS, dinámica de carrera |
| `laps` | mensajes `lap` | Parciales |
| `daily_load` | derivada | Serie diaria: TRIMP, ATL, CTL, TSB, ACWR, semáforo `risk` |
| `daily_metrics` | `raw/monitoring/*` + `raw/export/*.zip` | Por día: FC reposo oficial + mínima proxy, pasos, estrés, Body Battery, sueño (puntaje + etapas), HRV nocturno, VO2max (D-012, D-013) |
| `activity_zones` | derivada de `samples` | Tiempo en zonas Z1-Z5 (%FCmax estimada) por actividad (D-012) |
| `params` | derivada | FCmax/FCrep vigentes y su fuente (settings o estimado) |
| `race_predictions` | `raw/export/*.zip` | Predicción diaria de tiempos 5K/10K/21K/42K (D-013) |
| `wellness_log` | registro manual | 1 fila por sesión o día: dRPE, molestias por zona, Hooper, tiempo de registro (D-015, D-018) |
| `ingest_log` | pipeline | Auditoría por archivo: ok / error / detalle (idempotencia) |

### Tablas añadidas en D-018

| Tabla | Origen | Contenido |
|---|---|---|
| `daily_recovery` | derivada de `daily_metrics` | Banda personal de FC en reposo (media 28 d ± 0.5·DE), estado y días consecutivos fuera; deuda de sueño 7/14/28 d con su cobertura; Ln rMSSD móvil |
| `daily_readiness` | derivada | z-scores por dominio (autonómico, sueño, carga, subjetivo), índice compuesto, `n_dominios` y dominios en alerta |
| `activity_external` | derivada de `samples` | Carga externa por sesión: distancia, m/min total y activo, velocidad pico, índice de eficiencia, `gps_grade` |
| `activity_intrasession` | derivada de `samples` | Fatiga intra-partido: FC, distancia y coste cardíaco por mitad; `decoupling_pct` |
| `ostrc_log` | registro manual | Cuestionario OSTRC-H2 semanal por zona: q1-q4 y severidad 0-100 |

### Columnas añadidas en D-018 (migraciones aditivas)

| Tabla | Columnas | Para qué |
|---|---|---|
| `activities` | `sample_dt_s`, `gps_grade` | Intervalo mediano de muestreo y grado de la señal GPS — el "portero" que decide qué métricas externas se permiten (D-017) |
| `samples` | `speed_valid`, `speed_flag` | Limpieza de velocidad, espejo de la de FC. `speed_flag` ∈ {sin_dato, sin_gps, fuera_de_rango, salto_imposible} |
| `daily_load` | `load_7d/14d/21d/28d`, `load_7d_pct`, `wow_change`, `wow_flag`, `monotonia`, `strain` | Carga absoluta y su percentil personal (ahora la métrica principal), cambio semana a semana con bandera individualizada, monotonía y strain como serie diaria |
| `daily_metrics` | `sleep_start_utc`, `sleep_end_utc` | Horarios de sueño (habilitan medir regularidad circadiana) |
| `wellness_log` | `rpe_legs`, `rpe_breath`, `hooper_sueno/fatiga/estres/doms`, `segundos_registro` | RPE diferencial, cuestionario Hooper matinal y cronómetro de adherencia |

## Convenciones

- Unidades SI internamente (m, s, ppm); min/km y km/h solo en la capa de presentación.
- Timestamps en UTC en la base; `date_local` (America/Santiago) para agrupación diaria.
- `activity_id` = sha1(archivo raw)[:16] — trazabilidad archivo → filas (D-001).
- El deporte se conserva siempre; la carga se compara entre deportes vía TRIMP (D-006).
- Limpieza D-008: el valor crudo nunca se altera; `hr_flag` ∈ {sin_dato, fuera_de_rango, pico_artefacto}.
- **Nulo ≠ cero.** Una noche sin dato de sueño no es deuda cero, y un día sin registro
  subjetivo no es "sin molestias". Las métricas derivadas exigen un mínimo de
  observaciones válidas por ventana y devuelven nulo por debajo de ese mínimo, en vez
  de un número optimista (D-018).
- Las tablas derivadas se reconstruyen completas en cada ingesta (DELETE + INSERT):
  son 100 % regenerables desde `raw`, igual que el resto de la base.
