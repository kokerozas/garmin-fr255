"""Backfill desde el export oficial de la cuenta Garmin (D-013).

Política de fusión: el export RELLENA, nunca pisa — para cada día y columna,
si ya existe un valor (p. ej. del monitoreo del reloj, más granular), se respeta;
solo se completan los nulos. Idempotente por miembro del ZIP (ingest_log).

Actividades históricas: los resúmenes del export se insertan SOLO si no existe
ya una actividad con inicio a ±2 minutos (evita duplicar las que vinieron del
reloj, aunque el archivo binario difiera). Sin series 1s → TRIMP por método
'session_avg' (lo calcula metrics.load tras la carga).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from garmin.db.schema import connect
from garmin.ingest.export_reader import READERS, read_summarized_activities

DAILY_COLS = [
    "resting_hr", "steps", "stress_avg", "body_battery_max", "body_battery_min",
    "sleep_score", "sleep_h", "sleep_deep_h", "sleep_light_h", "sleep_rem_h",
    "sleep_awake_h", "sleep_stress", "vo2max",
]


def _fill_daily(con, rows: list[dict]) -> int:
    """Upsert 'rellenador': COALESCE(existente, nuevo) por columna."""
    n = 0
    for r in rows:
        d = r.get("date_local")
        if not d:
            continue
        con.execute(
            "INSERT INTO daily_metrics (date_local) VALUES (?) ON CONFLICT DO NOTHING", [d]
        )
        cols = [c for c in DAILY_COLS if r.get(c) is not None]
        if cols:
            sets = ", ".join(f"{c} = COALESCE({c}, ?)" for c in cols)
            con.execute(
                f"UPDATE daily_metrics SET {sets} WHERE date_local = ?",
                [r[c] for c in cols] + [d],
            )
            n += 1
    return n


def _load_summarized(con, z: zipfile.ZipFile) -> dict:
    """Inserta actividades históricas no presentes (dedupe por inicio ±120 s)."""
    existing = [
        r[0].timestamp()
        for r in con.execute(
            "SELECT start_time_utc FROM activities WHERE start_time_utc IS NOT NULL"
        ).fetchall()
    ]
    existing.sort()

    def is_dup(ts: float) -> bool:
        import bisect

        i = bisect.bisect_left(existing, ts)
        for j in (i - 1, i):
            if 0 <= j < len(existing) and abs(existing[j] - ts) <= 120:
                return True
        return False

    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Santiago")
    rows = read_summarized_activities(z)
    ins = dup = 0
    for r in rows:
        ts = r["start_time_utc"].timestamp()
        if is_dup(ts):
            dup += 1
            continue
        aid = f"gc{r['garmin_activity_id']}"
        con.execute(
            """INSERT OR IGNORE INTO activities
               (activity_id, file_name, sport, sub_sport, sport_profile, start_time_utc,
                date_local, duration_s, elapsed_s, distance_m, calories, avg_hr, max_hr,
                avg_speed_ms, aerobic_te, anaerobic_te, n_samples, hr_coverage)
               VALUES (?, 'summarizedActivities.json', ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0)""",
            [
                aid, r["sport"], r["sport_profile"], r["start_time_utc"],
                r["start_time_utc"].astimezone(tz).date(), r["duration_s"],
                r["elapsed_s"], r["distance_m"], r["calories"], r["avg_hr"],
                r["max_hr"], r["avg_speed_ms"], r["aerobic_te"], r["anaerobic_te"],
            ],
        )
        existing.insert(0, ts)
        existing.sort()
        ins += 1
    return {"insertadas": ins, "duplicadas_omitidas": dup, "total_export": len(rows)}


def load_export(db_path: str | Path, export_dir: str | Path) -> dict:
    """Procesa cada *.zip de data/raw/export. Idempotente por miembro del ZIP."""
    export_dir = Path(export_dir)
    zips = sorted(export_dir.glob("*.zip")) if export_dir.exists() else []
    if not zips:
        return {}

    con = connect(db_path)
    try:
        seen = {r[0] for r in con.execute("SELECT file_name FROM ingest_log").fetchall()}
        report: dict = {"dias_rellenados": 0}

        for zp in zips:
            z = zipfile.ZipFile(zp)
            for pattern, reader in READERS.items():
                for member in (n for n in z.namelist() if pattern in n and n.endswith(".json")):
                    key = f"export:{zp.name}:{Path(member).name}"
                    if key in seen:
                        continue
                    try:
                        rows = reader(z, member)
                        if pattern == "RunRacePredictions_":
                            for r in rows:
                                con.execute(
                                    """INSERT INTO race_predictions
                                       SELECT ?, ?, ? WHERE NOT EXISTS
                                       (SELECT 1 FROM race_predictions
                                        WHERE date_local = ? AND race = ?)""",
                                    [r["date_local"], r["race"], r["seconds"],
                                     r["date_local"], r["race"]],
                                )
                        else:
                            report["dias_rellenados"] += _fill_daily(con, rows)
                        status, detail = "ok", f"{len(rows)} filas"
                    except Exception as exc:
                        status, detail = "error", str(exc)[:250]
                    con.execute(
                        "INSERT INTO ingest_log (file_name, activity_id, status, detail) "
                        "VALUES (?, NULL, ?, ?)",
                        [key, status, detail],
                    )

            akey = f"export:{zp.name}:summarizedActivities"
            if akey not in seen:
                report["actividades"] = _load_summarized(con, z)
                con.execute(
                    "INSERT INTO ingest_log (file_name, activity_id, status, detail) "
                    "VALUES (?, NULL, 'ok', ?)",
                    [akey, str(report["actividades"])],
                )
        return report
    finally:
        con.close()
