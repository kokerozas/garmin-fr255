"""Tests del registro subjetivo y la tarjeta pre-partido (D-015)."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.db.schema import connect  # noqa: E402
from garmin.metrics.recommendations import build_recommendations  # noqa: E402
from garmin.metrics.wellness import (  # noqa: E402
    fetch_logs,
    match_readiness,
    pain_status,
    save_log,
)


def _db(tmp_path, acwr=1.0, dias_sin=1):
    db = tmp_path / "w.duckdb"
    con = connect(db)
    hoy = dt.date.today()
    con.execute(
        "INSERT INTO activities (activity_id, sport, start_time_utc, date_local, duration_s) "
        "VALUES ('act1', 'soccer', current_timestamp, ?, 5400)",
        [hoy - dt.timedelta(days=dias_sin)],
    )
    for i in range(30):
        con.execute(
            "INSERT INTO daily_load VALUES (?, 20.0, 1, 20.0, 18.0, -2.0, ?, 'optima')",
            [hoy - dt.timedelta(days=29 - i), acwr],
        )
    con.close()
    return db


def test_guardar_es_upsert_y_calcula_srpe(tmp_path):
    db = _db(tmp_path)
    hoy = dt.date.today()
    save_log(db, date_local=hoy, activity_id="act1", rpe=6, duration_min=90,
             dolores={"d_isquios": 2}, nota="primera")
    save_log(db, date_local=hoy, activity_id="act1", rpe=8, duration_min=90,
             dolores={"d_isquios": 3}, nota="corregida")
    logs = fetch_logs(db)
    assert len(logs) == 1  # reemplazó, no duplicó
    assert logs.iloc[0]["rpe"] == 8 and logs.iloc[0]["srpe"] == 720


def test_dolor_recurrente_y_grave_disparan_reglas(tmp_path):
    db = _db(tmp_path)
    hoy = dt.date.today()
    save_log(db, date_local=hoy - dt.timedelta(days=3), activity_id=None, rpe=5,
             duration_min=60, dolores={"d_isquios": 5}, nota="")
    save_log(db, date_local=hoy, activity_id="act1", rpe=5,
             duration_min=60, dolores={"d_isquios": 5, "d_rodilla": 8}, nota="")

    estado = pain_status(db, dias=7)
    zonas = {d["zona"]: d for d in estado}
    assert zonas["Isquiotibiales"]["veces_alto"] == 2
    assert zonas["Rodilla"]["nivel_max"] == 8

    recs = build_recommendations(db)
    titulos = " | ".join(r["titulo"] for r in recs)
    assert "rodilla" in titulos.lower() and "recurrente" in titulos.lower()


def test_readiness_semaforo(tmp_path):
    # sano → verde (o amarillo por falta de datos de sueño, nunca rojo)
    db = _db(tmp_path, acwr=1.0, dias_sin=1)
    rd = match_readiness(db)
    assert rd["estado"] in ("ok", "ojo")
    assert rd["factores"]["Carga"]["estado"] == "ok"

    # dolor 8 → rojo por molestias
    save_log(db, date_local=dt.date.today(), activity_id="act1", rpe=5,
             duration_min=60, dolores={"d_tobillo": 8}, nota="")
    rd2 = match_readiness(db)
    assert rd2["factores"]["Molestias"]["estado"] == "alto"
    assert rd2["estado"] == "alto"

    # parón largo → factor carga en alto
    db2 = _db(tmp_path.joinpath("b2"), acwr=0.3, dias_sin=15) if False else None
    dbb = tmp_path / "b2"
    dbb.mkdir()
    db3 = _db(dbb, acwr=0.3, dias_sin=15)
    rd3 = match_readiness(db3)
    assert rd3["factores"]["Carga"]["estado"] == "alto"
