"""Carga externa y fatiga intra-sesión (D-018).

Lo que más importa probar aquí no es que los números salgan, sino que NO salgan
cuando la señal no los soporta: el fútbol se graba a ~2.7 s por muestra y un sprint
dura 2-4 s, así que un conteo de sprints sobre esos datos sería inventado.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.db.schema import connect  # noqa: E402
from garmin.metrics.external import grade_gps, session_external  # noqa: E402
from garmin.metrics.intrasession import rebuild_intrasession  # noqa: E402
from garmin.transform.clean import flag_speed, speed_coverage  # noqa: E402


# --- Limpieza de velocidad ---------------------------------------------------

def test_flag_speed_marca_lo_imposible_sin_borrar():
    df = pd.DataFrame({
        "elapsed_s": [0, 1, 2, 3, 4],
        "speed_ms": [3.0, 3.2, 31.67, 3.1, None],   # 31.67 m/s = 114 km/h, visto en la base real
    })
    out = flag_speed(df)
    assert list(out["speed_flag"]) == [None, None, "fuera_de_rango", None, "sin_dato"]
    assert list(out["speed_valid"]) == [True, True, False, True, False]
    # El dato crudo sigue intacto: se marca, nunca se borra (invariante 2).
    assert out.loc[2, "speed_ms"] == 31.67


def test_flag_speed_detecta_salto_de_aceleracion():
    # 0 → 8 m/s en un segundo son 8 m/s²: por encima del techo humano razonable.
    df = pd.DataFrame({"elapsed_s": [0, 1, 2], "speed_ms": [0.5, 8.5, 8.6]})
    out = flag_speed(df)
    assert out.loc[1, "speed_flag"] == "salto_imposible"


def test_flag_speed_no_contamina_al_vecino_sano():
    """Tras un artefacto se compara contra la última muestra CONFIABLE, no contra él."""
    df = pd.DataFrame({"elapsed_s": [0, 1, 2, 3], "speed_ms": [3.0, 30.0, 3.1, 3.2]})
    out = flag_speed(df)
    assert out.loc[1, "speed_flag"] == "fuera_de_rango"
    assert out.loc[2, "speed_flag"] is None       # 3.1 es normal respecto a 3.0


def test_speed_coverage_y_frame_vacio():
    assert speed_coverage(pd.DataFrame()) == 0.0
    vacio = flag_speed(pd.DataFrame())
    assert "speed_valid" in vacio.columns


# --- El portero de la señal GPS ----------------------------------------------

@pytest.mark.parametrize("dt, gps, esperado", [
    (1.0, True, "alta"),      # perfiles de carrera del FR255
    (1.2, True, "alta"),      # borde inferior
    (1.5, True, "media"),
    (2.0, True, "media"),     # borde
    (2.74, True, "baja"),     # el fútbol real de Jorge
    (1.0, False, "sin_gps"),
    (None, True, "sin_gps"),
])
def test_grade_gps_en_sus_bordes(dt, gps, esperado):
    assert grade_gps(dt, gps) == esperado


# --- Base sintética para los recálculos --------------------------------------

def _base(tmp_path, dt_muestreo: float):
    """Un partido de 40 min con FC que deriva hacia arriba en la segunda mitad."""
    db = tmp_path / "e.duckdb"
    con = connect(db)
    con.execute("INSERT INTO params VALUES ('fc_maxima', 182, 'test', current_timestamp)")
    con.execute("INSERT INTO params VALUES ('fc_reposo', 71, 'test', current_timestamp)")
    n = int(2400 / dt_muestreo)
    t = np.arange(n) * dt_muestreo
    # 1ª mitad a 150 ppm, 2ª a 165: más pulso para la misma velocidad = fatiga.
    hr = np.where(t <= 1200, 150, 165)
    con.execute(
        """INSERT INTO activities
           (activity_id, sport, date_local, duration_s, distance_m, n_samples,
            hr_coverage, trimp, trimp_method, avg_hr)
           VALUES ('p1', 'soccer', DATE '2026-05-01', 2400, 4000, ?, 1.0, 200, 'samples', 157)""",
        [n],
    )
    smp = pd.DataFrame({
        "activity_id": "p1", "elapsed_s": t, "hr": hr, "hr_valid": True,
        "speed_ms": 2.0, "speed_valid": True, "lat": -33.4, "lon": -70.6,
    })
    con.register("s", smp)
    con.execute(
        """INSERT INTO samples (activity_id, elapsed_s, hr, hr_valid, speed_ms,
                                speed_valid, lat, lon)
           SELECT activity_id, elapsed_s, hr, hr_valid, speed_ms, speed_valid, lat, lon
           FROM s"""
    )
    con.unregister("s")
    con.execute("INSERT INTO activity_zones VALUES ('p1', 3, 2400)")
    return db, con


def test_alta_velocidad_solo_con_senal_de_grado_alto(tmp_path):
    """El corazón de la política: con muestreo de fútbol, HSR queda en NULL."""
    db, con = _base(tmp_path, dt_muestreo=2.74)
    try:
        session_external(con)
        row = con.execute(
            "SELECT gps_grade, hsr_m, n_sprints, m_per_min_act FROM activity_external"
        ).fetchone()
        assert row[0] == "baja"
        assert row[1] is None and row[2] is None   # nada de sprints inventados
        assert row[3] is not None                  # los metros por minuto sí se calculan
    finally:
        con.close()


def test_con_senal_de_1hz_si_se_calcula_alta_velocidad(tmp_path):
    db, con = _base(tmp_path, dt_muestreo=1.0)
    try:
        session_external(con)
        row = con.execute("SELECT gps_grade, hsr_m FROM activity_external").fetchone()
        assert row[0] == "alta"
        assert row[1] is not None                  # a 1 Hz sí se permite (aquí da 0: iba a 2 m/s)
    finally:
        con.close()


def test_session_external_es_idempotente(tmp_path):
    db, con = _base(tmp_path, dt_muestreo=1.0)
    try:
        session_external(con)
        primera = con.execute("SELECT * FROM activity_external").df()
        session_external(con)
        segunda = con.execute("SELECT * FROM activity_external").df()
        assert len(primera) == len(segunda) == 1
        pd.testing.assert_frame_equal(primera, segunda)
    finally:
        con.close()


def test_decoupling_detecta_la_deriva_de_la_segunda_mitad(tmp_path):
    """FC sube de 150 a 165 con la misma velocidad → el coste cardíaco sube."""
    db, con = _base(tmp_path, dt_muestreo=1.0)
    try:
        assert rebuild_intrasession(con) == 1
        row = con.execute(
            "SELECT hr1, hr2, decoupling_pct, metodo FROM activity_intrasession"
        ).fetchone()
        assert row[0] == pytest.approx(150, abs=1)
        assert row[1] == pytest.approx(165, abs=1)
        assert row[2] > 5          # más pulso por metro en la 2ª mitad
        assert row[3] == "tiempo"  # 1 solo lap: se parte por tiempo
    finally:
        con.close()


def test_partido_corto_no_entra(tmp_path):
    """Bajo 30 minutos, partir en mitades no dice nada: mejor no calcular."""
    db = tmp_path / "corto.duckdb"
    con = connect(db)
    try:
        con.execute("INSERT INTO params VALUES ('fc_maxima', 182, 't', current_timestamp)")
        con.execute(
            """INSERT INTO activities
               (activity_id, sport, date_local, duration_s, n_samples, hr_coverage)
               VALUES ('c1', 'soccer', DATE '2026-05-01', 600, 600, 1.0)"""
        )
        assert rebuild_intrasession(con) == 0
    finally:
        con.close()
