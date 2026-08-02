"""Tests de las métricas núcleo (correr con: python -m pytest tests/ -q)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garmin.metrics.load import classify_acwr, trimp_from_hr, trimp_session_avg  # noqa: E402
from garmin.transform.clean import flag_heart_rate  # noqa: E402


def test_trimp_crece_con_intensidad():
    dt = np.ones(600)  # 10 min
    suave = trimp_from_hr(np.full(600, 120.0), dt, 190, 60)
    fuerte = trimp_from_hr(np.full(600, 170.0), dt, 190, 60)
    assert 0 < suave < fuerte


def test_trimp_cero_en_reposo():
    dt = np.ones(60)
    assert trimp_from_hr(np.full(60, 60.0), dt, 190, 60) == 0.0


def test_trimp_fallback_consistente_con_integracion():
    """Con FC constante, integrar muestras ≈ usar el promedio de la sesión."""
    dt = np.ones(1800)
    integ = trimp_from_hr(np.full(1800, 150.0), dt, 190, 60)
    prom = trimp_session_avg(150.0, 1800.0, 190, 60)
    assert abs(integ - prom) / prom < 0.01


def test_semaforo_acwr():
    assert classify_acwr(0.5) == "baja"
    assert classify_acwr(1.0) == "optima"
    assert classify_acwr(1.4) == "precaucion"
    assert classify_acwr(2.0) == "alta"
    assert classify_acwr(None) is None


def test_limpieza_marca_sin_borrar():
    df = pd.DataFrame(
        {
            "elapsed_s": [0, 1, 2, 3, 4],
            "hr": [140, None, 250, 145, 60],  # None=sin dato, 250=rango, 60=pico (-85 en 1s)
        }
    )
    out = flag_heart_rate(df)
    assert list(out["hr_flag"]) == [None, "sin_dato", "fuera_de_rango", None, "pico_artefacto"]
    assert out["hr_valid"].tolist() == [True, False, False, True, False]
    # el dato crudo sigue intacto (D-008: marcar, no borrar)
    assert out.loc[2, "hr"] == 250
