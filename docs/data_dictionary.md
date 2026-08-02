# Diccionario de datos

Mapa entre los mensajes FIT del Forerunner 255 y las tablas DuckDB (implementado en D-011).

## Fuentes de datos (D-010)

| Origen (reloj) | Destino en el proyecto | Contenido |
|---|---|---|
| `GARMIN/Activity/` | `data/raw/fit/` | Actividades (fútbol, trote, etc.), 1 FIT por sesión |
| `GARMIN/Monitor/` | `data/raw/monitoring/monitor/` | Monitoreo diario: pasos, FC continua, estrés, Body Battery |
| `GARMIN/Sleep/` | `data/raw/monitoring/sleep/` | Sueño |
| `GARMIN/HRVStatus/` | `data/raw/monitoring/hrv/` | Estado HRV nocturno |
| `GARMIN/Metrics/` | `data/raw/monitoring/metrics/` | VO2max y métricas fisiológicas de Garmin |

## Tablas (data/db/garmin.duckdb)

| Tabla | Origen | Contenido |
|---|---|---|
| `activities` | mensaje FIT `session` | 1 fila por actividad: deporte, duración, distancia, FC, TE de Garmin, **TRIMP propio**, calidad FC |
| `samples` | mensajes `record` | Serie ~1 s: FC (+`hr_valid`/`hr_flag` D-008), velocidad, cadencia, altitud, GPS, dinámica de carrera |
| `laps` | mensajes `lap` | Parciales |
| `daily_load` | derivada | Serie diaria: TRIMP, ATL, CTL, TSB, ACWR, semáforo `risk` |
| `daily_metrics` | `raw/monitoring/*` | Por día: FC mínima (proxy reposo), pasos, estrés, sueño (puntaje + etapas), HRV nocturno con banda personal (D-012) |
| `activity_zones` | derivada de `samples` | Tiempo en zonas Z1-Z5 (%FCmax estimada) por actividad (D-012) |
| `params` | derivada | FCmax/FCrep vigentes y su fuente (settings o estimado) |
| `ingest_log` | pipeline | Auditoría por archivo: ok / error / detalle (idempotencia) |

## Convenciones

- Unidades SI internamente (m, s, ppm); min/km y km/h solo en la capa de presentación.
- Timestamps en UTC en la base; `date_local` (America/Santiago) para agrupación diaria.
- `activity_id` = sha1(archivo raw)[:16] — trazabilidad archivo → filas (D-001).
- El deporte se conserva siempre; la carga se compara entre deportes vía TRIMP (D-006).
- Limpieza D-008: el valor crudo nunca se altera; `hr_flag` ∈ {sin_dato, fuera_de_rango, pico_artefacto}.
