"""Carga incremental de monitoreo (Monitor/Sleep/HRV) → daily_metrics.

Mismo principio que la carga de actividades: idempotente por nombre de archivo
(ingest_log) y con upsert por fecha — varios archivos pueden aportar columnas
distintas del mismo día.
"""
from __future__ import annotations

from pathlib import Path

from garmin.db.schema import connect
from garmin.ingest.monitoring_reader import (
    parse_hrv_file,
    parse_monitor_file,
    parse_sleep_file,
)

PARSERS = {
    "monitor": (parse_monitor_file, ["hr_min", "hr_avg", "steps", "stress_avg"]),
    "sleep": (
        parse_sleep_file,
        ["sleep_score", "sleep_h", "sleep_deep_h", "sleep_light_h",
         "sleep_rem_h", "sleep_awake_h", "sleep_stress"],
    ),
    "hrv": (
        parse_hrv_file,
        ["hrv_last_night", "hrv_5min_high", "hrv_baseline_lower",
         "hrv_baseline_upper", "hrv_status"],
    ),
}


def _upsert(con, date_local, values: dict) -> None:
    con.execute(
        "INSERT INTO daily_metrics (date_local) VALUES (?) ON CONFLICT DO NOTHING",
        [date_local],
    )
    cols = [c for c, v in values.items() if v is not None]
    if cols:
        sets = ", ".join(f"{c} = ?" for c in cols)
        con.execute(
            f"UPDATE daily_metrics SET {sets} WHERE date_local = ?",
            [values[c] for c in cols] + [date_local],
        )


def load_monitoring(db_path: str | Path, monitoring_root: str | Path) -> dict:
    """Procesa archivos nuevos de raw/monitoring/{monitor,sleep,hrv}. Reporte resumido."""
    root = Path(monitoring_root)
    con = connect(db_path)
    try:
        seen = {r[0] for r in con.execute("SELECT file_name FROM ingest_log").fetchall()}
        report = {k: {"ok": 0, "errores": 0, "vacios": 0} for k in PARSERS}

        for kind, (parser, cols) in PARSERS.items():
            folder = root / kind
            if not folder.exists():
                continue
            for path in sorted(p for p in folder.iterdir() if p.is_file() and p.name not in seen):
                try:
                    row = parser(path)
                except Exception as exc:
                    con.execute(
                        "INSERT INTO ingest_log (file_name, activity_id, status, detail) "
                        "VALUES (?, NULL, 'error', ?)",
                        [path.name, f"{kind}: {str(exc)[:250]}"],
                    )
                    report[kind]["errores"] += 1
                    continue

                date = row.get("date_local") if row else None
                if not date:
                    status, detail = "vacio", kind
                    report[kind]["vacios"] += 1
                else:
                    _upsert(con, date, {c: row.get(c) for c in cols})
                    status, detail = "ok", f"{kind} {date}"
                    report[kind]["ok"] += 1
                con.execute(
                    "INSERT INTO ingest_log (file_name, activity_id, status, detail) "
                    "VALUES (?, NULL, ?, ?)",
                    [path.name, status, detail],
                )
        return report
    finally:
        con.close()
