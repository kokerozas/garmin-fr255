"""Las figuras se construyen sin caerse — incluso con datos vacíos (D-019).

El dashboard muestra paneles cuyo dato puede no existir todavía (HRV desde jul-2026,
wellness_log recién estrenada, actividades sin GPS). Un panel sin datos debe salir
VACÍO, nunca reventar la vista completa: por eso cada figura se prueba dos veces,
con datos y sin ellos.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin import viz  # noqa: E402

N = 40
FECHAS = pd.date_range(dt.date(2026, 1, 1), periods=N, freq="D")


@pytest.fixture
def daily() -> pd.DataFrame:
    return pd.DataFrame({
        "date_local": FECHAS,
        "trimp": [40 + (i % 7) * 12 for i in range(N)],
        "atl": [50.0] * N, "ctl": [45.0] * N, "tsb": [-5.0] * N,
        "acwr": [1.1] * N, "risk": ["optima"] * N,
        "load_7d": [300.0 + i for i in range(N)],
        "load_28d": [1200.0] * N,
        "load_7d_pct": [i / N for i in range(N)],
    })


@pytest.fixture
def dm() -> pd.DataFrame:
    return pd.DataFrame({
        "date_local": FECHAS,
        "fc_reposo": [52 + (i % 5) for i in range(N)],
        "rhr_band_lo": [50.0] * N, "rhr_band_hi": [55.0] * N, "rhr_ref": [52.5] * N,
        "sleep_h": [6.0 + (i % 3) * 0.5 for i in range(N)],
        "stress_avg": [30.0] * N,
    })


@pytest.fixture
def samples() -> pd.DataFrame:
    return pd.DataFrame({
        "elapsed_s": range(N), "hr": [140] * N, "hr_valid": [True] * N,
        "lat": [-33.4 + i * 1e-4 for i in range(N)],
        "lon": [-70.6 + i * 1e-4 for i in range(N)],
        "altitude_m": [500 + i * 2 for i in range(N)],
        "distance_m": [i * 100 for i in range(N)],
        "speed_ms": [3.0] * N,
    })


VACIO = pd.DataFrame()


def test_calendario_con_y_sin_datos(daily):
    assert viz.fig_calendar_load(daily).data
    viz.fig_calendar_load(VACIO)  # no debe lanzar


def test_serie_con_banda_marca_lo_que_sale_de_banda(dm):
    fig = viz.fig_serie_con_banda(dm, "fc_reposo", "rhr_band_lo", "rhr_band_hi",
                                  "FC reposo", "ppm", ref="rhr_ref")
    nombres = [tr.name for tr in fig.data]
    assert "tu banda habitual" in nombres
    assert "fuera de tu banda" in nombres  # la serie sintética supera 55 ppm
    viz.fig_serie_con_banda(VACIO, "fc_reposo", "a", "b", "t", "ppm")


def test_carga_absoluta_dibuja_percentil(daily):
    fig = viz.fig_carga_absoluta(daily)
    assert any("ercentil" in (tr.name or "") for tr in fig.data)
    viz.fig_carga_absoluta(VACIO)


def test_dumbbell_ordena_y_colorea_por_severidad():
    zonas = [
        {"zona": "Isquiotibiales", "actual": 8, "promedio": 3.0},
        {"zona": "Rodilla", "actual": 2, "promedio": 1.0},
        {"zona": "Aductores", "actual": 5, "promedio": 4.0},
    ]
    fig = viz.fig_molestias_dumbbell(zonas)
    hoy = [tr for tr in fig.data if tr.name == "hoy"][0]
    # El eje Y va de menor a mayor molestia: el peor queda arriba del gráfico.
    assert list(hoy.y) == ["Rodilla", "Aductores", "Isquiotibiales"]
    assert hoy.marker.color[-1] == viz.STATUS["alta"]        # 8/10 → rojo
    assert hoy.marker.color[0] == viz.STATUS["optima"]       # 2/10 → verde
    viz.fig_molestias_dumbbell([])


def test_carga_vs_recuperacion_es_2d(daily):
    df = pd.DataFrame({"x": [1.0, 1.4], "y": [0.3, -1.2], "color": [0, 6],
                       "size": [50, 80], "fecha": ["2026-01-01", "2026-01-02"]})
    fig = viz.fig_carga_vs_recuperacion(df)
    assert fig.data[0].type == "scatter"       # 2D, no scatter3d
    viz.fig_carga_vs_recuperacion(VACIO)


def test_sparkline_y_bullet_toleran_vacio():
    assert viz.fig_sparkline([1, 2, 3]).data
    viz.fig_sparkline([])
    assert viz.fig_bullet(52.0, 50.0, 55.0, 52.5, "ppm").data
    viz.fig_bullet(None, None, None, None)     # sin dato → figura vacía, sin excepción


def test_small_multiples_ignora_columnas_ausentes(dm):
    fig = viz.fig_small_multiples(dm, [("sleep_h", "Sueño"), ("no_existe", "X")])
    assert len(fig.data) == 1
    viz.fig_small_multiples(VACIO, [("sleep_h", "Sueño")])


def test_decoupling(daily):
    df = pd.DataFrame({"date_local": FECHAS[:5], "decoupling_pct": [2.0, 5.0, -1.0, 8.0, 3.0]})
    assert viz.fig_decoupling(df).data
    viz.fig_decoupling(VACIO)


# --- La regla del 3D (D-019) -------------------------------------------------

def test_ruta_3d_no_exagera_el_relieve(samples):
    """aspectmode='data' es la garantía de que una loma no parezca el Everest."""
    fig = viz.fig_route_3d(samples)
    assert fig.layout.scene.aspectmode == "data"
    assert fig.data[0].type == "scatter3d"
    viz.fig_route_3d(VACIO)


def test_perfil_2d_acompana_al_3d(samples):
    assert viz.fig_elevation_profile(samples).data
    viz.fig_elevation_profile(VACIO)


def test_scatter3d_declara_que_es_exploracion():
    """El 3D de datos abstractos existe, pero rotulado: no se leen valores de ahí."""
    df = pd.DataFrame({"x": [1.0, 1.2], "y": [0.5, -0.3], "z": [2, 5]})
    fig = viz.fig_scatter3d_exploracion(df)
    textos = " ".join(a.text for a in fig.layout.annotations)
    assert "2D" in textos and "exploración" in textos.lower()
    viz.fig_scatter3d_exploracion(VACIO)


def test_parcoords_orden_de_ejes_fijo():
    df = pd.DataFrame({"carga": [1.0, 1.3], "recup": [0.2, -0.8], "mol": [0, 5]})
    cols = [("carga", "Carga"), ("recup", "Recuperación"), ("mol", "Molestia")]
    fig = viz.fig_parcoords(df, cols)
    assert [d.label for d in fig.data[0].dimensions] == ["Carga", "Recuperación", "Molestia"]
    viz.fig_parcoords(VACIO, cols)


# --- Sistema de color --------------------------------------------------------

def test_tokens_claros_intactos():
    """La paleta clara está validada para daltonismo: si cambia, es un bug."""
    t = viz.theme(dark=False)
    assert t["surface"] == "#fcfcfb" and t["ink"] == "#0b0b0b" and t["grid"] == "#e1e0d9"
    assert viz.SLOTS[0] == "#2a78d6"


def test_tema_oscuro_cambia_el_papel_pero_no_los_slots(daily):
    claro = viz.fig_calendar_load(daily, dark=False)
    oscuro = viz.fig_calendar_load(daily, dark=True)
    assert claro.layout.paper_bgcolor != oscuro.layout.paper_bgcolor
    assert viz.theme(True)["surface"] == "#14140f"


def test_rangeselector_se_puede_anadir(daily):
    fig = viz.add_rangeselector(viz.fig_daily_load(daily))
    assert fig.layout.xaxis.rangeslider.visible is True
