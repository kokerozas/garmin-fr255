"""Tests del motor de recomendaciones (D-014) sobre una base sintética."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.db.schema import connect  # noqa: E402
from garmin.metrics.recommendations import build_recommendations  # noqa: E402


def _base(tmp_path, dias_sin_actividad: int, acwr: float):
    db = tmp_path / "t.duckdb"
    con = connect(db)
    hoy = dt.date.today()
    ultima = hoy - dt.timedelta(days=dias_sin_actividad)
    con.execute(
        "INSERT INTO activities (activity_id, sport, start_time_utc, date_local, duration_s) "
        "VALUES ('x', 'soccer', current_timestamp, ?, 3600)", [ultima],
    )
    for i in range(30):
        d = hoy - dt.timedelta(days=29 - i)
        con.execute(
            "INSERT INTO daily_load (date_local, trimp, n_activities, atl, ctl, tsb, acwr, risk) "
            "VALUES (?, ?, 1, 20.0, 15.0, -5.0, ?, 'optima')",
            [d, 20.0, acwr],
        )
    con.close()
    return db


def test_paron_largo_dispara_alerta(tmp_path):
    recs = build_recommendations(_base(tmp_path, dias_sin_actividad=14, acwr=0.5))
    niveles = {r["nivel"] for r in recs}
    assert "alerta" in niveles
    assert any("Regreso gradual" in r["titulo"] for r in recs)


def test_acwr_rojo_dispara_alerta(tmp_path):
    recs = build_recommendations(_base(tmp_path, dias_sin_actividad=1, acwr=1.8))
    assert any("ACWR" in r["titulo"] and r["nivel"] == "alerta" for r in recs)


def test_estado_sano_da_ok_y_siempre_incluye_regla_del_dolor(tmp_path):
    recs = build_recommendations(_base(tmp_path, dias_sin_actividad=1, acwr=1.0))
    assert any(r["nivel"] == "ok" for r in recs)
    assert any("dolor" in r["titulo"].lower() for r in recs)


def test_orden_por_severidad(tmp_path):
    recs = build_recommendations(_base(tmp_path, dias_sin_actividad=14, acwr=1.8))
    niveles = [r["nivel"] for r in recs]
    assert niveles.index("alerta") == 0  # lo más grave siempre primero
