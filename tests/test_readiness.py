"""Tests del índice compuesto de disposición (D-017).

Todo con datos SINTÉTICOS: nunca se toca la base real de Jorge.
Correr con: .venv\\Scripts\\python.exe -m pytest tests/test_readiness.py -q
"""
import datetime as _dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.db.schema import connect  # noqa: E402
from garmin.metrics.readiness import (  # noqa: E402
    UMBRAL_ALERTA,
    _rolling_z,
    build_readiness_frame,
    estado_global,
    rebuild_daily_readiness,
    refresh_readiness,
)


# --- 1. El z-score móvil ------------------------------------------------------
# Ventana [4, 5, 5, 7, 9]: media 6, DE muestral 2  →  z del último = (9-6)/2 = 1.5
SERIE_BASE = [2, 4, 4, 4, 5, 5, 7, 9]


def test_z_con_media_y_de_conocidas():
    z = _rolling_z(pd.Series(SERIE_BASE, dtype=float), ventana=5, min_n=5)
    assert z.iloc[-1] == pytest.approx(1.5)


def test_invertir_cambia_el_signo():
    """En FC en reposo o estrés, "más alto" es peor: el z debe salir negativo."""
    normal = _rolling_z(pd.Series(SERIE_BASE, dtype=float), ventana=5, min_n=5)
    invertido = _rolling_z(pd.Series(SERIE_BASE, dtype=float), ventana=5, min_n=5,
                           invertir=True)
    assert invertido.iloc[-1] == pytest.approx(-1.5)
    assert invertido.iloc[-1] == pytest.approx(-normal.iloc[-1])


def test_dato_faltante_se_excluye_y_no_se_imputa():
    """El día sin dato queda NaN y NO contamina la media de los vecinos."""
    # Misma ventana efectiva que SERIE_BASE ([4,5,5,7,9]) pero con un hueco:
    con_hueco = pd.Series([3, 4, np.nan, 5, 5, 7, 9], dtype=float)
    z = _rolling_z(con_hueco, ventana=6, min_n=5)
    assert np.isnan(z.iloc[2])                      # el día sin dato no inventa z
    assert z.iloc[-1] == pytest.approx(1.5)         # idéntico a la serie sin hueco
    # Si se hubiera imputado (p.ej. con 0 o con la media) el resultado cambiaría:
    imputado = _rolling_z(con_hueco.fillna(0.0), ventana=6, min_n=5)
    assert imputado.iloc[-1] != pytest.approx(1.5)


def test_sin_historia_suficiente_devuelve_nan():
    z = _rolling_z(pd.Series(SERIE_BASE, dtype=float), ventana=6, min_n=6)
    assert np.isnan(z.iloc[4])   # solo 5 observaciones acumuladas
    assert not np.isnan(z.iloc[5])


def test_variable_congelada_no_produce_z_infinito():
    """DE ~ 0: dividir por casi cero daría un z gigante sin significado."""
    z = _rolling_z(pd.Series([50.0] * 40), ventana=30, min_n=30)
    assert z.iloc[-1] != z.iloc[-1] or np.isnan(z.iloc[-1])  # NaN, no ±inf


# --- 2. Base sintética --------------------------------------------------------
def _crear_db(tmp_path, dias=120, con_sueno=True, con_carga=True,
              con_rhr=True, dia_malo=False):
    """Crea una DuckDB de juguete con series diarias plausibles pero inventadas."""
    rng = np.random.default_rng(7)
    fin = _dt.date.today()
    fechas = [fin - _dt.timedelta(days=i) for i in range(dias - 1, -1, -1)]

    rhr = np.round(rng.normal(52, 3.5, dias))
    sleep_h = np.round(rng.normal(6.5, 0.8, dias), 2)
    sleep_score = np.round(rng.normal(70, 8, dias))
    tsb = np.round(rng.normal(0, 8, dias), 2)
    if dia_malo:  # último día claramente fuera de su propia normalidad
        rhr[-1] = 70
        sleep_h[-1] = 2.5
        sleep_score[-1] = 30

    con = connect(tmp_path / "test.duckdb")
    for i, f in enumerate(fechas):
        con.execute(
            """INSERT INTO daily_metrics (date_local, resting_hr, sleep_h, sleep_score)
               VALUES (?, ?, ?, ?)""",
            [f,
             int(rhr[i]) if con_rhr else None,
             float(sleep_h[i]) if con_sueno else None,
             int(sleep_score[i]) if con_sueno else None],
        )
        if con_carga:
            con.execute(
                "INSERT INTO daily_load (date_local, trimp, n_activities, tsb) "
                "VALUES (?, 0, 0, ?)", [f, float(tsb[i])],
            )
    return con


def test_dominios_disponibles_y_promedio(tmp_path):
    con = _crear_db(tmp_path)
    try:
        df = build_readiness_frame(con)
        fila = df.iloc[-1]
        # Sin HRV ni Hooper: quedan autonómico (solo FC reposo), sueño y carga.
        assert fila["n_dominios"] == 3
        assert np.isnan(fila["z_subjetivo"])
        # El dominio sueño es el promedio de sus dos variables, no dos votos.
        assert fila["z_sueno"] == pytest.approx(
            np.mean([fila["z_sleep_h"], fila["z_sleep_score"]])
        )
        # El índice es el promedio de los dominios disponibles.
        assert fila["indice"] == pytest.approx(
            np.mean([fila["z_autonomico"], fila["z_sueno"], fila["z_carga"]])
        )
    finally:
        con.close()


def test_menos_de_dos_dominios_devuelve_none(tmp_path):
    """Solo sueño disponible → nada de índice inventado, y un motivo explícito."""
    con = _crear_db(tmp_path, con_carga=False, con_rhr=False)
    try:
        rebuild_daily_readiness(con)
        df = build_readiness_frame(con)
        assert df.iloc[-1]["n_dominios"] == 1
        assert np.isnan(df.iloc[-1]["indice"])
    finally:
        con.close()

    est = estado_global(tmp_path / "test.duckdb")
    assert est["indice"] is None
    assert est["dominios_evaluables"] == 1
    assert "2" in est["motivo"]  # explica que hacen falta al menos 2 dominios


def test_dia_malo_levanta_banderas(tmp_path):
    con = _crear_db(tmp_path, dia_malo=True)
    try:
        fila = build_readiness_frame(con).iloc[-1]
        assert fila["z_autonomico"] <= UMBRAL_ALERTA   # FC reposo disparada
        assert fila["z_sueno"] <= UMBRAL_ALERTA        # noche pésima
        assert fila["dominios_alerta"] >= 2
    finally:
        con.close()

    est = estado_global(tmp_path / "test.duckdb")
    assert est["dominios_alerta"] >= 2
    assert est["detalle"][0]["estado"] == "alerta"
    assert "DE" in est["detalle"][0]["razon"]         # razón en lenguaje natural


def test_rebuild_es_idempotente(tmp_path):
    con = _crear_db(tmp_path)
    try:
        rebuild_daily_readiness(con)
        primera = con.execute(
            "SELECT * FROM daily_readiness ORDER BY date_local").df()
        rebuild_daily_readiness(con)
        segunda = con.execute(
            "SELECT * FROM daily_readiness ORDER BY date_local").df()
        assert len(primera) == len(segunda) > 0
        pd.testing.assert_frame_equal(primera, segunda)
    finally:
        con.close()


def test_refresh_devuelve_resumen(tmp_path):
    con = _crear_db(tmp_path)
    con.close()
    res = refresh_readiness(tmp_path / "test.duckdb")
    assert res["dias_serie"] > 0
    assert res["n_dominios"] == 3
    assert isinstance(res["indice"], float)


def test_base_vacia_no_revienta(tmp_path):
    con = connect(tmp_path / "vacia.duckdb")
    try:
        out = rebuild_daily_readiness(con)
        assert out.empty
    finally:
        con.close()
    est = estado_global(tmp_path / "vacia.duckdb")
    assert est["indice"] is None and est["detalle"] == []
