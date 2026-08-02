"""Carga incremental de archivos FIT a DuckDB.

Idempotente: cada archivo se identifica por el hash de su contenido; si ya está
en la base (o falló antes), se salta. Volver a ejecutar solo procesa lo nuevo.
"""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from garmin.db.schema import connect
from garmin.ingest.fit_reader import file_hash, parse_fit
from garmin.transform.clean import flag_heart_rate, hr_coverage

TZ_LOCAL = ZoneInfo("America/Santiago")

SAMPLE_COLS = [
    "activity_id", "ts_utc", "elapsed_s", "hr", "hr_valid", "hr_flag",
    "speed_ms", "cadence_rpm", "altitude_m", "distance_m", "lat", "lon",
    "temp_c", "vertical_oscillation_mm", "stance_time_ms", "step_length_mm", "power_w",
]
LAP_COLS = [
    "activity_id", "lap_index", "start_time_utc", "duration_s",
    "distance_m", "avg_hr", "max_hr", "avg_speed_ms",
]


def _date_local(ts) -> object:
    if ts is None or pd.isna(ts):
        return None
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(TZ_LOCAL).date()


def load_directory(db_path: str | Path, fit_dir: str | Path) -> dict:
    """Procesa todos los .fit nuevos de fit_dir. Devuelve reporte resumido."""
    fit_dir = Path(fit_dir)
    con = connect(db_path)
    try:
        seen = {r[0] for r in con.execute("SELECT file_name FROM ingest_log").fetchall()}
        files = sorted(p for p in fit_dir.glob("*.fit") if p.name not in seen)
        report = {"nuevos": len(files), "ok": 0, "errores": 0, "saltados": len(seen)}

        for path in files:
            aid = file_hash(path)
            try:
                parsed = parse_fit(path)
            except Exception as exc:  # archivo corrupto o no-actividad: registrar y seguir
                con.execute(
                    "INSERT INTO ingest_log (file_name, activity_id, status, detail) VALUES (?, ?, 'error', ?)",
                    [path.name, aid, str(exc)[:300]],
                )
                report["errores"] += 1
                continue

            act = parsed["activity"]
            samples = flag_heart_rate(parsed["samples"])
            act_row = {
                **act,
                "activity_id": aid,
                "date_local": _date_local(act.get("start_time_utc")),
                "n_samples": int(len(samples)),
                "hr_coverage": hr_coverage(samples),
                "trimp": None,          # se calcula en metrics.load (D-007)
                "trimp_method": None,
            }
            adf = pd.DataFrame([act_row])
            con.register("adf", adf)
            con.execute(
                """INSERT INTO activities (activity_id, file_name, sport, sub_sport, sport_profile,
                     start_time_utc, date_local, duration_s, elapsed_s, distance_m, calories,
                     avg_hr, max_hr, avg_speed_ms, total_ascent_m, total_descent_m,
                     avg_cadence_rpm, aerobic_te, anaerobic_te, n_samples, hr_coverage, trimp, trimp_method)
                   SELECT activity_id, file_name, sport, sub_sport, sport_profile,
                     start_time_utc, date_local, duration_s, elapsed_s, distance_m, calories,
                     avg_hr, max_hr, avg_speed_ms, total_ascent_m, total_descent_m,
                     avg_cadence_rpm, aerobic_te, anaerobic_te, n_samples, hr_coverage, trimp, trimp_method
                   FROM adf"""
            )
            con.unregister("adf")

            if not samples.empty:
                sdf = samples.copy()
                sdf["activity_id"] = aid
                for col in SAMPLE_COLS:
                    if col not in sdf.columns:
                        sdf[col] = None
                sdf = sdf[SAMPLE_COLS]
                con.register("sdf", sdf)
                con.execute(f"INSERT INTO samples SELECT {', '.join(SAMPLE_COLS)} FROM sdf")
                con.unregister("sdf")

            lap_df = parsed["laps"]
            if not lap_df.empty:
                lap_df = lap_df.copy()
                lap_df["activity_id"] = aid
                for col in LAP_COLS:
                    if col not in lap_df.columns:
                        lap_df[col] = None
                lap_df = lap_df[LAP_COLS]
                con.register("ldf", lap_df)
                con.execute(f"INSERT INTO laps SELECT {', '.join(LAP_COLS)} FROM ldf")
                con.unregister("ldf")

            con.execute(
                "INSERT INTO ingest_log (file_name, activity_id, status, detail) VALUES (?, ?, 'ok', ?)",
                [path.name, aid, f"{act.get('sport')} {len(samples)} muestras"],
            )
            report["ok"] += 1

        return report
    finally:
        con.close()
