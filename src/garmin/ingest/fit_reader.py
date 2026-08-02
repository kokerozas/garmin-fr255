"""Lectura de archivos FIT del Forerunner 255.

Convierte un .fit en estructuras tabulares:
- activity: resumen de la sesión (1 fila)
- samples:  serie temporal (1 fila por registro, ~1 s)
- laps:     parciales/vueltas

Principio D-001: el archivo raw jamás se modifica; aquí solo se lee.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import fitdecode
import pandas as pd

SEMICIRCLE = 180.0 / 2**31  # conversión de semicírculos Garmin a grados


def file_hash(path: str | Path) -> str:
    """activity_id estable: sha1 del contenido del archivo (trazabilidad D-001)."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _get(fields: dict, *names, default=None):
    """Primer campo presente y no-nulo de la lista (p. ej. enhanced_speed > speed)."""
    for n in names:
        v = fields.get(n)
        if v is not None:
            return v
    return default


def parse_fit(path: str | Path) -> dict:
    """Parsea un FIT de actividad. Devuelve dict con activity, samples, laps.

    Lanza excepción si el archivo está corrupto (el loader la captura y registra).
    """
    path = Path(path)
    session: dict = {}
    records: list[dict] = []
    laps: list[dict] = []

    kwargs = {}
    if hasattr(fitdecode, "CrcCheck"):  # tolerar CRC dañado sin abortar
        kwargs["check_crc"] = fitdecode.CrcCheck.WARN

    with fitdecode.FitReader(str(path), **kwargs) as reader:
        for frame in reader:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            if frame.name == "record":
                f = {fld.name: fld.value for fld in frame.fields}
                lat = f.get("position_lat")
                lon = f.get("position_long")
                records.append(
                    {
                        "ts_utc": f.get("timestamp"),
                        "hr": f.get("heart_rate"),
                        "speed_ms": _get(f, "enhanced_speed", "speed"),
                        "cadence_rpm": (
                            (f.get("cadence") or 0) + (f.get("fractional_cadence") or 0.0)
                        )
                        if f.get("cadence") is not None
                        else None,
                        "altitude_m": _get(f, "enhanced_altitude", "altitude"),
                        "distance_m": f.get("distance"),
                        "lat": lat * SEMICIRCLE if lat is not None else None,
                        "lon": lon * SEMICIRCLE if lon is not None else None,
                        "temp_c": f.get("temperature"),
                        "vertical_oscillation_mm": f.get("vertical_oscillation"),
                        "stance_time_ms": f.get("stance_time"),
                        "step_length_mm": f.get("step_length"),
                        "power_w": f.get("power"),
                    }
                )
            elif frame.name == "session":
                s = {fld.name: fld.value for fld in frame.fields}
                if not session:  # nos quedamos con la primera sesión (multisesión: raro)
                    session = s
            elif frame.name == "lap":
                f = {fld.name: fld.value for fld in frame.fields}
                laps.append(
                    {
                        "lap_index": len(laps),
                        "start_time_utc": f.get("start_time"),
                        "duration_s": f.get("total_timer_time"),
                        "distance_m": f.get("total_distance"),
                        "avg_hr": f.get("avg_heart_rate"),
                        "max_hr": f.get("max_heart_rate"),
                        "avg_speed_ms": _get(f, "enhanced_avg_speed", "avg_speed"),
                    }
                )

    if not session:
        raise ValueError("FIT sin mensaje 'session' (no es un archivo de actividad)")

    activity = {
        "file_name": path.name,
        "sport": str(session.get("sport")) if session.get("sport") is not None else None,
        "sub_sport": str(session.get("sub_sport")) if session.get("sub_sport") is not None else None,
        "sport_profile": session.get("sport_profile_name"),
        "start_time_utc": session.get("start_time"),
        "duration_s": session.get("total_timer_time"),
        "elapsed_s": session.get("total_elapsed_time"),
        "distance_m": session.get("total_distance"),
        "calories": session.get("total_calories"),
        "avg_hr": session.get("avg_heart_rate"),
        "max_hr": session.get("max_heart_rate"),
        "avg_speed_ms": _get(session, "enhanced_avg_speed", "avg_speed"),
        "total_ascent_m": session.get("total_ascent"),
        "total_descent_m": session.get("total_descent"),
        "avg_cadence_rpm": session.get("avg_cadence"),
        "aerobic_te": session.get("total_training_effect"),
        "anaerobic_te": session.get("total_anaerobic_training_effect"),
    }

    samples = pd.DataFrame(records)
    if not samples.empty and samples["ts_utc"].notna().any():
        samples = samples.dropna(subset=["ts_utc"]).sort_values("ts_utc").reset_index(drop=True)
        t0 = samples["ts_utc"].iloc[0]
        samples["elapsed_s"] = (samples["ts_utc"] - t0).dt.total_seconds()

    return {"activity": activity, "samples": samples, "laps": pd.DataFrame(laps)}
