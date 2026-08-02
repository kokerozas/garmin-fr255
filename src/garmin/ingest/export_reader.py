"""Lectura del export oficial de la cuenta Garmin (ZIP de "Exportar tus datos").

Se lee DIRECTO desde el ZIP (data/raw/export/*.zip), sin descomprimir: el ZIP es
el archivo raw inmutable (D-001). Aporta el historial que el reloj ya no retiene:

- UDSFile_*            → resumen diario: FC reposo REAL, pasos, estrés, Body Battery
- *_sleepData.json     → sueño con etapas y puntaje, desde el inicio de la cuenta
- MetricsMaxMetData_*  → VO2max (lo que el FIT del reloj no exponía, D-012)
- RunRacePredictions_* → predicción de tiempos 5K/10K/21K/42K
- summarizedActivities → resúmenes de TODAS las actividades de la cuenta
                         (incluye las que el reloj ya olvidó; sin series 1s)
"""
from __future__ import annotations

import json
import zipfile
from datetime import date, datetime, timezone


def _date(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s[:10]) if s else None
    except ValueError:
        return None


def _members(z: zipfile.ZipFile, contains: str) -> list[str]:
    return sorted(n for n in z.namelist() if contains in n and n.endswith(".json"))


def read_uds(z: zipfile.ZipFile, member: str) -> list[dict]:
    """Resumen diario universal → filas por fecha."""
    rows = []
    for it in json.loads(z.read(member)):
        d = _date(it.get("calendarDate"))
        if not d:
            continue
        stress = None
        for agg in (it.get("allDayStress") or {}).get("aggregatorList", []):
            if agg.get("type") == "TOTAL" and agg.get("averageStressLevel", -1) >= 0:
                stress = float(agg["averageStressLevel"])
        bb_max = bb_min = None
        for st in (it.get("bodyBattery") or {}).get("bodyBatteryStatList", []):
            if st.get("bodyBatteryStatType") == "HIGHEST":
                bb_max = st.get("statsValue")
            elif st.get("bodyBatteryStatType") == "LOWEST":
                bb_min = st.get("statsValue")
        rows.append(
            {
                "date_local": d,
                "resting_hr": it.get("currentDayRestingHeartRate"),
                "steps": it.get("totalSteps"),
                "stress_avg": stress,
                "body_battery_max": bb_max,
                "body_battery_min": bb_min,
            }
        )
    return rows


def read_sleep(z: zipfile.ZipFile, member: str) -> list[dict]:
    """Sueño por noche (asignado por Garmin a la fecha en que se despierta)."""
    rows = []
    for it in json.loads(z.read(member)):
        if not isinstance(it, dict):
            continue
        d = _date(it.get("calendarDate"))
        if not d:
            continue
        deep = it.get("deepSleepSeconds") or 0
        light = it.get("lightSleepSeconds") or 0
        rem = it.get("remSleepSeconds") or 0
        awake = it.get("awakeSleepSeconds") or 0
        total = deep + light + rem
        scores = it.get("sleepScores") or {}
        score = scores.get("overallScore")
        if score is None and isinstance(scores.get("overall"), dict):
            score = scores["overall"].get("value")
        rows.append(
            {
                "date_local": d,
                "sleep_score": score,
                "sleep_h": round(total / 3600, 2) if total else None,
                "sleep_deep_h": round(deep / 3600, 2) if total else None,
                "sleep_light_h": round(light / 3600, 2) if total else None,
                "sleep_rem_h": round(rem / 3600, 2) if total else None,
                "sleep_awake_h": round(awake / 3600, 2) if total else None,
                "sleep_stress": it.get("avgSleepStress"),
            }
        )
    return rows


def read_maxmet(z: zipfile.ZipFile, member: str) -> list[dict]:
    """VO2max por fecha (medición de Garmin, deporte RUNNING/GENERIC)."""
    rows = []
    for it in json.loads(z.read(member)):
        d = _date(it.get("calendarDate"))
        v = it.get("vo2MaxValue")
        if d and v:
            rows.append({"date_local": d, "vo2max": float(v)})
    return rows


def read_race_predictions(z: zipfile.ZipFile, member: str) -> list[dict]:
    rows = []
    for it in json.loads(z.read(member)):
        d = _date(it.get("calendarDate"))
        if not d:
            continue
        for key, race in (("raceTime5K", "5K"), ("raceTime10K", "10K"),
                          ("raceTimeHalf", "21K"), ("raceTimeMarathon", "42K")):
            v = it.get(key)
            if v:
                rows.append({"date_local": d, "race": race, "seconds": int(v)})
    return rows


def read_summarized_activities(z: zipfile.ZipFile) -> list[dict]:
    """Resúmenes de actividades de toda la cuenta (sin series por segundo)."""
    member = next(
        (n for n in z.namelist() if n.endswith("summarizedActivities.json")), None
    )
    if not member:
        return []
    raw = json.loads(z.read(member))
    items = raw[0].get("summarizedActivitiesExport", []) if raw else []
    rows = []
    for it in items:
        ts_ms = it.get("beginTimestamp")
        if not ts_ms:
            continue
        start = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        dur_s = (it.get("duration") or 0) / 1000.0
        rows.append(
            {
                "garmin_activity_id": it.get("activityId"),
                "sport": str(it.get("activityType") or "").lower() or None,
                "sport_profile": it.get("name"),
                "start_time_utc": start,
                "duration_s": dur_s or None,
                "elapsed_s": (it.get("elapsedDuration") or 0) / 1000.0 or None,
                "distance_m": it.get("distance"),
                "calories": round(it["calories"]) if it.get("calories") else None,
                "avg_hr": round(it["avgHr"]) if it.get("avgHr") else None,
                "max_hr": round(it["maxHr"]) if it.get("maxHr") else None,
                "avg_speed_ms": it.get("avgSpeed"),
                "aerobic_te": it.get("aerobicTrainingEffect"),
                "anaerobic_te": it.get("anaerobicTrainingEffect"),
            }
        )
    return rows


READERS = {
    "UDSFile_": read_uds,
    "_sleepData.json": read_sleep,
    "MetricsMaxMetData_": read_maxmet,
    "RunRacePredictions_": read_race_predictions,
}
