"""Zonas de FC (D-007) y tiempo-en-zona por actividad.

Zonas clásicas por %FCmax (la FCmax es la estimada desde datos o la de settings):
  Z1 50-60% · Z2 60-70% · Z3 70-80% · Z4 80-90% · Z5 90-100%+
El tiempo bajo el 50% no se asigna a ninguna zona (actividad muy suave/pausas).
"""
from __future__ import annotations

import numpy as np

from garmin.metrics.load import estimate_hr_params

ZONE_PCTS = [0.5, 0.6, 0.7, 0.8, 0.9]  # bordes inferiores de Z1..Z5


def zone_edges(fc_max: float) -> list[float]:
    return [p * fc_max for p in ZONE_PCTS]


def zone_of(hr: np.ndarray, fc_max: float) -> np.ndarray:
    """Zona 1..5 por muestra (0 = bajo Z1)."""
    edges = zone_edges(fc_max)
    z = np.zeros(len(hr), dtype=int)
    for i, lo in enumerate(edges, start=1):
        z[hr >= lo] = i
    return z


def compute_zone_times(con) -> int:
    """Calcula tiempo-en-zona para actividades que aún no lo tienen. Devuelve cuántas."""
    fc_max, _, _ = estimate_hr_params(con)
    pending = [
        r[0]
        for r in con.execute(
            """SELECT a.activity_id FROM activities a
               WHERE a.n_samples > 0
                 AND NOT EXISTS (SELECT 1 FROM activity_zones z
                                 WHERE z.activity_id = a.activity_id)"""
        ).fetchall()
    ]
    n = 0
    for aid in pending:
        df = con.execute(
            """SELECT elapsed_s, hr FROM samples
               WHERE activity_id = ? AND hr_valid ORDER BY elapsed_s""",
            [aid],
        ).df()
        if len(df) < 2:
            continue
        dt = df["elapsed_s"].diff().clip(lower=0, upper=10).fillna(1).to_numpy()
        zones = zone_of(df["hr"].to_numpy(float), fc_max)
        for z in range(1, 6):
            secs = float(dt[zones == z].sum())
            if secs > 0:
                con.execute(
                    "INSERT INTO activity_zones VALUES (?, ?, ?)", [aid, z, secs]
                )
        n += 1
    return n
