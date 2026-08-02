"""Esquema DuckDB (D-002). Ver docs/data_dictionary.md para el mapeo FIT→tabla."""
from __future__ import annotations

import duckdb

DDL = """
CREATE TABLE IF NOT EXISTS activities (
    activity_id     VARCHAR PRIMARY KEY,   -- sha1 del archivo raw (trazabilidad)
    file_name       VARCHAR,
    sport           VARCHAR,
    sub_sport       VARCHAR,
    sport_profile   VARCHAR,               -- nombre del perfil en el reloj (ej. Fútbol)
    start_time_utc  TIMESTAMP,
    date_local      DATE,                  -- fecha en America/Santiago (agrupación diaria)
    duration_s      DOUBLE,
    elapsed_s       DOUBLE,
    distance_m      DOUBLE,
    calories        INTEGER,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    avg_speed_ms    DOUBLE,
    total_ascent_m  INTEGER,
    total_descent_m INTEGER,
    avg_cadence_rpm DOUBLE,
    aerobic_te      DOUBLE,                -- Training Effect de Garmin (referencia D-007)
    anaerobic_te    DOUBLE,
    n_samples       INTEGER,
    hr_coverage     DOUBLE,                -- calidad FC de la sesión [0-1]
    trimp           DOUBLE,                -- carga propia (D-007)
    trimp_method    VARCHAR,               -- 'samples' | 'session_avg' | NULL
    loaded_at       TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS samples (
    activity_id     VARCHAR,
    ts_utc          TIMESTAMP,
    elapsed_s       DOUBLE,
    hr              INTEGER,
    hr_valid        BOOLEAN,
    hr_flag         VARCHAR,               -- sin_dato | fuera_de_rango | pico_artefacto
    speed_ms        DOUBLE,
    cadence_rpm     DOUBLE,
    altitude_m      DOUBLE,
    distance_m      DOUBLE,
    lat             DOUBLE,
    lon             DOUBLE,
    temp_c          INTEGER,
    vertical_oscillation_mm DOUBLE,
    stance_time_ms  DOUBLE,
    step_length_mm  DOUBLE,
    power_w         DOUBLE
);

CREATE TABLE IF NOT EXISTS laps (
    activity_id     VARCHAR,
    lap_index       INTEGER,
    start_time_utc  TIMESTAMP,
    duration_s      DOUBLE,
    distance_m      DOUBLE,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    avg_speed_ms    DOUBLE
);

CREATE TABLE IF NOT EXISTS ingest_log (
    file_name   VARCHAR,
    activity_id VARCHAR,
    status      VARCHAR,                   -- ok | sin_session | error
    detail      VARCHAR,
    ingested_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS params (
    key         VARCHAR PRIMARY KEY,
    value       DOUBLE,
    source      VARCHAR,                   -- 'estimado_desde_datos' | 'settings'
    computed_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS daily_load (
    date_local   DATE PRIMARY KEY,
    trimp        DOUBLE,
    n_activities INTEGER,
    atl          DOUBLE,   -- carga aguda (EWMA 7 días)
    ctl          DOUBLE,   -- carga crónica (EWMA 42 días)
    tsb          DOUBLE,   -- balance = CTL - ATL
    acwr         DOUBLE,   -- ratio agudo:crónico (7d/28d, promedios móviles)
    risk         VARCHAR   -- baja | optima | precaucion | alta
);
"""


def connect(path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(path))
    con.execute(DDL)
    return con
