# Diccionario de datos

Mapa entre los mensajes del formato FIT del Forerunner 255 y las tablas de la base
de datos (DuckDB). Se completa durante el diseño de la ingesta.

## Mensajes FIT relevantes (por completar)

| Mensaje FIT | Contenido | Tabla destino (propuesta) |
|---|---|---|
| `session` | Resumen de la actividad (deporte, distancia, tiempo, FC media, VO2max…) | `activities` |
| `record` | Series segundo a segundo (FC, ritmo, cadencia, altitud, potencia…) | `samples` |
| `lap` | Parciales / vueltas | `laps` |
| `event` | Pausas, cambios de deporte | `events` |
| `hrv` | Intervalos R-R (si está habilitado) | `hrv` |
| `monitoring` | Datos diarios (pasos, FC en reposo, sueño, estrés, Body Battery) | `daily_metrics` |

## Convenciones

- Unidades SI internamente (m, s, ppm); conversión a min/km solo en la capa de presentación.
- Timestamps en UTC en la base; zona local (America/Santiago) solo al visualizar.
- `activity_id` = hash estable del archivo raw de origen (trazabilidad archivo → fila).
- El deporte (`sport`/`sub_sport`) se conserva siempre: la carga se compara entre deportes vía TRIMP (D-006).
