"""Lectura de archivos de monitoreo del FR255 (carpetas Monitor/, Sleep/, HRVStatus/).

Cada tipo de archivo aporta piezas de la tabla daily_metrics:
- Monitor:    FC continua (min/media diaria), pasos, estrés medio.
- Sleep:      puntaje de sueño, duración y etapas (profundo/ligero/REM/despierto).
- HRVStatus:  HRV nocturno (RMSSD) con la banda de referencia personal.

Los archivos Metrics/ (VO2max de Garmin) usan mensajes no documentados en el
perfil FIT público — quedan fuera hasta tener mejor perfil (ver D-012).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import fitdecode

TZ_LOCAL = ZoneInfo("America/Santiago")
GARMIN_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)


def _reader(path):
    kwargs = {}
    if hasattr(fitdecode, "CrcCheck"):
        kwargs["check_crc"] = fitdecode.CrcCheck.WARN
    return fitdecode.FitReader(str(path), **kwargs)


def _local_date(ts: datetime):
    return ts.astimezone(TZ_LOCAL).date()


def _epoch_s(ts: datetime) -> int:
    return int((ts - GARMIN_EPOCH).total_seconds())


def parse_monitor_file(path: str | Path) -> dict:
    """Un archivo Monitor ≈ un día. Devuelve métricas agregadas por fecha local.

    Los mensajes 'monitoring' usan timestamp_16 (16 bits relativos): se
    reconstruye contra el último timestamp completo visto (algoritmo FIT estándar).
    """
    hr_points: list[tuple[datetime, int]] = []
    steps_by_type: dict[object, int] = {}
    stress_vals: list[int] = []
    last_full: int | None = None

    with _reader(path) as fr:
        for frame in fr:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            f = {fld.name: fld.value for fld in frame.fields}
            if frame.name == "monitoring":
                ts = f.get("timestamp")
                if ts is not None:
                    last_full = _epoch_s(ts)
                elif f.get("timestamp_16") is not None and last_full is not None:
                    t16 = int(f["timestamp_16"])
                    last_full = last_full + ((t16 - (last_full & 0xFFFF)) & 0xFFFF)
                    ts = GARMIN_EPOCH + timedelta(seconds=last_full)
                hr = f.get("heart_rate")
                if ts is not None and hr:
                    hr_points.append((ts, int(hr)))
                steps = f.get("steps")
                if steps is not None:
                    at = f.get("activity_type")
                    prev = steps_by_type.get(at, 0)
                    steps_by_type[at] = max(prev, int(steps))
            elif frame.name == "stress_level":
                v = f.get("stress_level_value")
                if v is not None and v >= 0:
                    stress_vals.append(int(v))
            elif frame.name == "monitoring_info" and last_full is None:
                ts = f.get("timestamp")
                if ts is not None:
                    last_full = _epoch_s(ts)

    if not hr_points and not stress_vals and not steps_by_type:
        return {}
    # fecha del día: la moda de las fechas locales de los puntos de FC (o del archivo)
    if hr_points:
        dates = {}
        for ts, _ in hr_points:
            d = _local_date(ts)
            dates[d] = dates.get(d, 0) + 1
        date = max(dates, key=dates.get)
        hrs = [h for ts, h in hr_points if _local_date(ts) == date and 25 <= h <= 230]
    else:
        date, hrs = None, []

    return {
        "date_local": date,
        "hr_min": min(hrs) if hrs else None,
        "hr_avg": round(sum(hrs) / len(hrs), 1) if hrs else None,
        "steps": sum(steps_by_type.values()) if steps_by_type else None,
        "stress_avg": round(sum(stress_vals) / len(stress_vals), 1) if stress_vals else None,
    }


def parse_sleep_file(path: str | Path) -> dict:
    """Una noche: puntaje, etapas y duración. La noche se asigna al día en que despiertas."""
    assessment: dict = {}
    levels: list[tuple[datetime, str]] = []
    created = None

    with _reader(path) as fr:
        for frame in fr:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            f = {fld.name: fld.value for fld in frame.fields}
            if frame.name == "sleep_assessment":
                assessment = f
            elif frame.name == "sleep_level":
                ts, lvl = f.get("timestamp"), f.get("sleep_level")
                if ts is not None and lvl is not None:
                    levels.append((ts, str(lvl)))
            elif frame.name == "file_id":
                created = f.get("time_created")

    if not levels and not assessment:
        return {}

    stage_s = {"deep": 0.0, "light": 0.0, "rem": 0.0, "awake": 0.0}
    levels.sort()
    for (t0, lvl), (t1, _) in zip(levels, levels[1:]):
        stage_s[lvl if lvl in stage_s else "awake"] += (t1 - t0).total_seconds()

    end = levels[-1][0] if levels else created
    total_sleep_h = (stage_s["deep"] + stage_s["light"] + stage_s["rem"]) / 3600.0
    return {
        "date_local": _local_date(end) if end else None,
        "sleep_score": assessment.get("overall_sleep_score"),
        "sleep_h": round(total_sleep_h, 2) if levels else None,
        "sleep_deep_h": round(stage_s["deep"] / 3600, 2) if levels else None,
        "sleep_light_h": round(stage_s["light"] / 3600, 2) if levels else None,
        "sleep_rem_h": round(stage_s["rem"] / 3600, 2) if levels else None,
        "sleep_awake_h": round(stage_s["awake"] / 3600, 2) if levels else None,
        "sleep_stress": assessment.get("average_stress_during_sleep"),
        "_created": created,  # para quedarnos con el archivo más reciente por noche
    }


def parse_hrv_file(path: str | Path) -> dict:
    """HRV nocturno (RMSSD en ms) + banda de referencia personal de Garmin."""
    summary: dict = {}
    with _reader(path) as fr:
        for frame in fr:
            if isinstance(frame, fitdecode.FitDataMessage) and frame.name == "hrv_status_summary":
                summary = {fld.name: fld.value for fld in frame.fields}
    if not summary:
        return {}
    ts = summary.get("timestamp")
    return {
        "date_local": _local_date(ts) if ts else None,
        "hrv_last_night": summary.get("last_night_average"),
        "hrv_5min_high": summary.get("last_night_5_min_high"),
        "hrv_baseline_lower": summary.get("baseline_balanced_lower"),
        "hrv_baseline_upper": summary.get("baseline_balanced_upper"),
        "hrv_status": str(summary.get("status")) if summary.get("status") is not None else None,
    }
