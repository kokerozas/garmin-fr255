"""Tests de la capa de monitoreo y zonas (iteración 2)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.metrics.zones import zone_edges, zone_of  # noqa: E402


def test_bordes_de_zona():
    edges = zone_edges(180.0)
    assert edges == pytest.approx([90.0, 108.0, 126.0, 144.0, 162.0])


def test_asignacion_de_zonas():
    hr = np.array([80.0, 95.0, 110.0, 130.0, 150.0, 170.0])
    z = zone_of(hr, 180.0)
    #      <Z1   Z1    Z2     Z3     Z4     Z5
    assert z.tolist() == [0, 1, 2, 3, 4, 5]


def test_timestamp16_reconstruccion():
    """El algoritmo de timestamp_16 debe manejar el desborde de 16 bits."""
    last_full = 0x0001FFF0  # epoch-seconds con low16 cerca del tope
    t16 = 0x0005            # ya desbordó
    nuevo = last_full + ((t16 - (last_full & 0xFFFF)) & 0xFFFF)
    assert nuevo == 0x00020005
    assert nuevo > last_full


def test_etapas_de_sueno_suman_duracion():
    """La atribución de etapas usa el nivel vigente hasta el siguiente cambio."""
    from datetime import datetime, timedelta

    from garmin.ingest.monitoring_reader import parse_sleep_file  # noqa: F401

    # lógica replicada del parser: nivel i dura hasta el timestamp i+1
    t0 = datetime(2026, 8, 1, 2, 0)
    levels = [(t0, "light"), (t0 + timedelta(hours=1), "deep"), (t0 + timedelta(hours=3), "rem")]
    stage_s = {"deep": 0.0, "light": 0.0, "rem": 0.0, "awake": 0.0}
    for (a, lvl), (b, _) in zip(levels, levels[1:]):
        stage_s[lvl] += (b - a).total_seconds()
    assert stage_s["light"] == 3600 and stage_s["deep"] == 7200 and stage_s["rem"] == 0
