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

CREATE TABLE IF NOT EXISTS daily_metrics (
    date_local        DATE PRIMARY KEY,
    hr_min            INTEGER,   -- FC mínima del día (proxy de FC en reposo)
    hr_avg            DOUBLE,
    steps             INTEGER,
    stress_avg        DOUBLE,    -- 0-100 (solo valores válidos)
    sleep_score       INTEGER,   -- 0-100 (puntaje Garmin)
    sleep_h           DOUBLE,    -- horas dormidas (profundo+ligero+REM)
    sleep_deep_h      DOUBLE,
    sleep_light_h     DOUBLE,
    sleep_rem_h       DOUBLE,
    sleep_awake_h     DOUBLE,
    sleep_stress      DOUBLE,
    hrv_last_night    DOUBLE,    -- RMSSD ms
    hrv_5min_high     DOUBLE,
    hrv_baseline_lower DOUBLE,
    hrv_baseline_upper DOUBLE,
    hrv_status        VARCHAR
);

CREATE TABLE IF NOT EXISTS activity_zones (
    activity_id VARCHAR,
    zone        INTEGER,          -- 1..5 (% de FCmax: 50-60-70-80-90-100)
    seconds     DOUBLE
);

CREATE TABLE IF NOT EXISTS wellness_log (
    log_id       VARCHAR PRIMARY KEY,   -- 'a:<activity_id>' o 'd:<fecha>' (general)
    date_local   DATE,
    activity_id  VARCHAR,               -- NULL si es registro general del día
    rpe          INTEGER,               -- esfuerzo percibido 0-10 (Foster)
    duration_min INTEGER,               -- minutos (de la actividad, o manual)
    d_isquios    INTEGER,               -- molestias 0-10 por zona (fútbol)
    d_cuadriceps INTEGER,
    d_gemelos    INTEGER,
    d_aductores  INTEGER,
    d_rodilla    INTEGER,
    d_tobillo    INTEGER,
    d_espalda    INTEGER,
    nota         VARCHAR,
    created_at   TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS race_predictions (
    date_local DATE,
    race       VARCHAR,   -- 5K | 10K | 21K | 42K
    seconds    INTEGER
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

-- Serie derivada de recuperación (D-017): bandas personales, no umbrales importados.
CREATE TABLE IF NOT EXISTS daily_recovery (
    date_local     DATE PRIMARY KEY,
    rhr_7d         DOUBLE,   -- media móvil 7d de FC en reposo
    rhr_ref        DOUBLE,   -- media móvil 28d (referencia personal)
    rhr_band_lo    DOUBLE,   -- referencia ± 0.5·DE  (SWC de Hopkins 2000)
    rhr_band_hi    DOUBLE,
    rhr_state      VARCHAR,  -- bajo_banda | dentro | sobre_banda
    rhr_days_out   INTEGER,  -- días consecutivos sobre la banda
    sleep_debt_7d  DOUBLE,   -- horas de déficit acumulado (Milewski 2014)
    sleep_debt_14d DOUBLE,
    sleep_debt_28d DOUBLE,
    sleep_cov_7d   DOUBLE,   -- % de noches con dato en la ventana (honestidad del dato)
    sleep_7d       DOUBLE,   -- media móvil 7d de horas dormidas
    sleep_ref      DOUBLE,   -- media móvil 28d
    ln_rmssd_7d    DOUBLE,   -- Ln rMSSD media móvil 7d (Plews & Buchheit 2013)
    ln_rmssd_cv    DOUBLE    -- coeficiente de variación de Ln rMSSD
);

-- Índice compuesto de disposición por z-scores individuales (D-017).
CREATE TABLE IF NOT EXISTS daily_readiness (
    date_local        DATE PRIMARY KEY,
    z_autonomico      DOUBLE,   -- FC reposo (invertida) + HRV
    z_sueno           DOUBLE,   -- horas + puntaje
    z_carga           DOUBLE,   -- TSB normalizado
    z_subjetivo       DOUBLE,   -- Hooper (cuando exista registro)
    indice            DOUBLE,   -- promedio de los dominios disponibles
    n_dominios        INTEGER,  -- cuántos pudieron evaluarse (nunca se imputa)
    dominios_alerta   INTEGER   -- cuántos por debajo del umbral
);

-- Carga externa por sesión (D-017). Solo se puebla si la señal GPS lo permite.
CREATE TABLE IF NOT EXISTS activity_external (
    activity_id     VARCHAR PRIMARY KEY,
    distance_m      DOUBLE,
    dur_total_min   DOUBLE,
    dur_activa_min  DOUBLE,   -- tiempo en Z2..Z5 (proxy de tiempo jugado)
    m_per_min       DOUBLE,   -- sobre duración total
    m_per_min_act   DOUBLE,   -- sobre duración activa
    hsr_m           DOUBLE,   -- distancia sobre umbral alto (NULL si gps_grade no lo permite)
    sprint_m        DOUBLE,
    n_sprints       INTEGER,
    v_max_ms        DOUBLE,   -- velocidad pico válida (tras limpieza)
    eff_index       DOUBLE,   -- metros por unidad de TRIMP (Akubat 2014)
    gps_grade       VARCHAR   -- alta | media | baja | sin_gps
);

-- Fatiga intra-sesión: 1ª vs 2ª mitad (Mohr 2003), D-017.
CREATE TABLE IF NOT EXISTS activity_intrasession (
    activity_id     VARCHAR PRIMARY KEY,
    hr1             DOUBLE,   -- FC media 1ª mitad
    hr2             DOUBLE,
    pct_fcmax1      DOUBLE,
    pct_fcmax2      DOUBLE,
    dist1_m         DOUBLE,
    dist2_m         DOUBLE,
    vel1_ms         DOUBLE,
    vel2_ms         DOUBLE,
    coste1          DOUBLE,   -- %FCreserva por m/s (coste cardíaco)
    coste2          DOUBLE,
    decoupling_pct  DOUBLE,   -- (coste2/coste1 - 1)·100
    dist_drop_pct   DOUBLE,   -- caída de distancia 2ª vs 1ª
    metodo          VARCHAR   -- 'tiempo' (mitades por tiempo) | 'laps'
);

-- Vigilancia de problemas por sobrecarga, OSTRC-H2 (Clarsen 2013/2020). D-018.
CREATE TABLE IF NOT EXISTS ostrc_log (
    week_start   DATE,
    zone         VARCHAR,
    q1           INTEGER,   -- participación   0/8/17/25
    q2           INTEGER,   -- volumen         0/6/13/19/25
    q3           INTEGER,   -- rendimiento     0/6/13/19/25
    q4           INTEGER,   -- síntomas        0/8/17/25
    severity     INTEGER,   -- suma 0-100
    created_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (week_start, zone)
);
"""


# Migraciones aditivas para bases creadas con esquemas anteriores (D-013)
MIGRATIONS = [
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS resting_hr INTEGER",
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS vo2max DOUBLE",
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS body_battery_max INTEGER",
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS body_battery_min INTEGER",
    # --- D-017: calidad de la señal externa y carga absoluta ---
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS sample_dt_s DOUBLE",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS gps_grade VARCHAR",
    "ALTER TABLE samples ADD COLUMN IF NOT EXISTS speed_valid BOOLEAN",
    "ALTER TABLE samples ADD COLUMN IF NOT EXISTS speed_flag VARCHAR",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS load_7d DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS load_14d DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS load_21d DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS load_28d DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS load_7d_pct DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS wow_change DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS wow_flag VARCHAR",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS monotonia DOUBLE",
    "ALTER TABLE daily_load ADD COLUMN IF NOT EXISTS strain DOUBLE",
    # --- D-017: regularidad del sueño (necesita los timestamps del export) ---
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS sleep_start_utc TIMESTAMP",
    "ALTER TABLE daily_metrics ADD COLUMN IF NOT EXISTS sleep_end_utc TIMESTAMP",
    # --- D-018: registro subjetivo ampliado ---
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS rpe_legs INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS rpe_breath INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS hooper_sueno INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS hooper_fatiga INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS hooper_estres INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS hooper_doms INTEGER",
    "ALTER TABLE wellness_log ADD COLUMN IF NOT EXISTS segundos_registro DOUBLE",
]


def connect(path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(path))
    con.execute(DDL)
    for mig in MIGRATIONS:
        con.execute(mig)
    return con
