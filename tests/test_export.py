"""Tests del backfill desde el export de cuenta Garmin (D-013)."""
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.ingest.export_reader import (  # noqa: E402
    read_maxmet,
    read_race_predictions,
    read_sleep,
    read_uds,
)


def _zip_with(name: str, payload) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, json.dumps(payload))
    return zipfile.ZipFile(buf)


def test_uds_extrae_reposo_estres_y_body_battery():
    z = _zip_with("UDSFile_x.json", [{
        "calendarDate": "2024-03-01",
        "currentDayRestingHeartRate": 49,
        "totalSteps": 8000,
        "allDayStress": {"aggregatorList": [
            {"type": "AWAKE", "averageStressLevel": 50},
            {"type": "TOTAL", "averageStressLevel": 33},
        ]},
        "bodyBattery": {"bodyBatteryStatList": [
            {"bodyBatteryStatType": "HIGHEST", "statsValue": 80},
            {"bodyBatteryStatType": "LOWEST", "statsValue": 20},
        ]},
    }])
    (r,) = read_uds(z, "UDSFile_x.json")
    assert r["resting_hr"] == 49 and r["steps"] == 8000
    assert r["stress_avg"] == 33.0  # usa el agregador TOTAL, no AWAKE
    assert r["body_battery_max"] == 80 and r["body_battery_min"] == 20


def test_sleep_convierte_etapas_a_horas_e_ignora_stubs():
    z = _zip_with("s_sleepData.json", [
        {"retro": False},  # stub sin fecha: debe ignorarse
        {"calendarDate": "2024-03-02", "deepSleepSeconds": 3600,
         "lightSleepSeconds": 7200, "remSleepSeconds": 1800,
         "awakeSleepSeconds": 600, "sleepScores": {"overallScore": 78}},
    ])
    rows = read_sleep(z, "s_sleepData.json")
    assert len(rows) == 1
    r = rows[0]
    assert r["sleep_h"] == 3.5 and r["sleep_deep_h"] == 1.0
    assert r["sleep_score"] == 78


def test_maxmet_y_predicciones():
    z1 = _zip_with("MetricsMaxMetData_x.json",
                   [{"calendarDate": "2024-04-01", "vo2MaxValue": 48.0}])
    assert read_maxmet(z1, "MetricsMaxMetData_x.json")[0]["vo2max"] == 48.0

    z2 = _zip_with("RunRacePredictions_x.json",
                   [{"calendarDate": "2024-04-01", "raceTime5K": 1500,
                     "raceTime10K": 3100, "raceTimeHalf": None}])
    rows = read_race_predictions(z2, "RunRacePredictions_x.json")
    assert {(r["race"], r["seconds"]) for r in rows} == {("5K", 1500), ("10K", 3100)}
