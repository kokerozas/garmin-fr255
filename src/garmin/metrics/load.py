"""Métricas de carga de entrenamiento (D-006, D-007).

- TRIMP de Banister por sesión, integrado muestra a muestra sobre FC válida.
  Unifica la carga entre deportes (fútbol, running, etc.) porque solo usa FC.
- FCmax / FCreposo estimadas desde los propios datos (percentiles robustos),
  con override manual desde config/settings.yaml si el atleta los define.
- Serie diaria: ATL (EWMA 7d), CTL (EWMA 42d), TSB = CTL-ATL,
  y ACWR (promedio 7d / promedio 28d) con semáforo de riesgo de lesión.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from garmin.db.schema import connect
from garmin.utils.config import load_settings

# Coeficientes de Banister (hombre). Documentado en docs/decisions.md D-007.
_B_A, _B_B = 0.64, 1.92

RISK_BANDS = [
    (0.0, 0.8, "baja"),         # subcarga: pierde forma, riesgo al volver a subir
    (0.8, 1.3, "optima"),       # sweet spot
    (1.3, 1.5, "precaucion"),
    (1.5, float("inf"), "alta"),
]


def classify_acwr(acwr: float | None) -> str | None:
    if acwr is None or (isinstance(acwr, float) and math.isnan(acwr)):
        return None
    for lo, hi, label in RISK_BANDS:
        if lo <= acwr < hi:
            return label
    return None


def estimate_hr_params(con) -> tuple[float, float, str]:
    """(fc_max, fc_reposo, fuente). Settings manda; si no, percentiles de los datos."""
    cfg = load_settings().get("atleta", {})
    fc_max, fc_rest = cfg.get("fc_maxima"), cfg.get("fc_reposo")
    if fc_max and fc_rest:
        return float(fc_max), float(fc_rest), "settings"

    row = con.execute(
        """SELECT quantile_cont(hr, 0.997), quantile_cont(hr, 0.01)
           FROM samples WHERE hr_valid"""
    ).fetchone()
    est_max = float(row[0]) if row and row[0] else 190.0
    est_rest = float(row[1]) if row and row[1] else 55.0
    return (
        float(fc_max) if fc_max else est_max,
        float(fc_rest) if fc_rest else est_rest,
        "estimado_desde_datos",
    )


def trimp_from_hr(hr: np.ndarray, dt_s: np.ndarray, fc_max: float, fc_rest: float) -> float:
    """TRIMP de Banister integrado: sum( dt_min * HRr * a * e^(b*HRr) )."""
    span = max(fc_max - fc_rest, 1.0)
    hrr = np.clip((hr - fc_rest) / span, 0.0, 1.0)
    return float(np.sum((dt_s / 60.0) * hrr * _B_A * np.exp(_B_B * hrr)))


def trimp_session_avg(avg_hr: float, duration_s: float, fc_max: float, fc_rest: float) -> float:
    """Fallback cuando no hay serie de FC utilizable: usa FC media de la sesión."""
    span = max(fc_max - fc_rest, 1.0)
    hrr = min(max((avg_hr - fc_rest) / span, 0.0), 1.0)
    return (duration_s / 60.0) * hrr * _B_A * math.exp(_B_B * hrr)


def compute_trimp(con, min_coverage: float = 0.3) -> int:
    """Calcula TRIMP para actividades que aún no lo tienen. Devuelve cuántas."""
    fc_max, fc_rest, source = estimate_hr_params(con)
    con.execute(
        "INSERT OR REPLACE INTO params VALUES ('fc_maxima', ?, ?, current_timestamp)",
        [fc_max, source],
    )
    con.execute(
        "INSERT OR REPLACE INTO params VALUES ('fc_reposo', ?, ?, current_timestamp)",
        [fc_rest, source],
    )

    pending = con.execute(
        """SELECT activity_id, avg_hr, duration_s, hr_coverage
           FROM activities WHERE trimp IS NULL"""
    ).fetchall()

    n = 0
    for aid, avg_hr, duration_s, coverage in pending:
        trimp, method = None, None
        if coverage and coverage >= min_coverage:
            df = con.execute(
                """SELECT elapsed_s, hr FROM samples
                   WHERE activity_id = ? AND hr_valid ORDER BY elapsed_s""",
                [aid],
            ).df()
            if len(df) > 1:
                dt = df["elapsed_s"].diff().clip(lower=0, upper=10).fillna(1).to_numpy()
                trimp = trimp_from_hr(df["hr"].to_numpy(float), dt, fc_max, fc_rest)
                method = "samples"
        if trimp is None and avg_hr and duration_s:
            trimp = trimp_session_avg(float(avg_hr), float(duration_s), fc_max, fc_rest)
            method = "session_avg"
        if trimp is not None:
            con.execute(
                "UPDATE activities SET trimp = ?, trimp_method = ? WHERE activity_id = ?",
                [round(trimp, 1), method, aid],
            )
            n += 1
    return n


def rebuild_daily_load(con) -> pd.DataFrame:
    """Reconstruye la tabla daily_load completa desde activities."""
    daily = con.execute(
        """SELECT date_local, SUM(trimp) AS trimp, COUNT(*) AS n_activities
           FROM activities
           WHERE date_local IS NOT NULL AND trimp IS NOT NULL
           GROUP BY date_local ORDER BY date_local"""
    ).df()
    if daily.empty:
        return daily

    daily["date_local"] = pd.to_datetime(daily["date_local"])
    idx = pd.date_range(daily["date_local"].min(), pd.Timestamp.today().normalize(), freq="D")
    s = daily.set_index("date_local").reindex(idx)
    s["trimp"] = s["trimp"].fillna(0.0)
    s["n_activities"] = s["n_activities"].fillna(0).astype(int)

    s["atl"] = s["trimp"].ewm(span=7, adjust=False).mean()
    s["ctl"] = s["trimp"].ewm(span=42, adjust=False).mean()
    s["tsb"] = s["ctl"] - s["atl"]

    acute = s["trimp"].rolling(7, min_periods=7).mean()
    chronic = s["trimp"].rolling(28, min_periods=28).mean()
    s["acwr"] = np.where(chronic > 1e-9, acute / chronic, np.nan)
    s["risk"] = [classify_acwr(v if not pd.isna(v) else None) for v in s["acwr"]]

    out = s.reset_index().rename(columns={"index": "date_local"})
    out["date_local"] = out["date_local"].dt.date
    con.execute("DELETE FROM daily_load")
    con.register("dl", out)
    con.execute(
        """INSERT INTO daily_load
           SELECT date_local, trimp, n_activities, atl, ctl, tsb, acwr, risk FROM dl"""
    )
    con.unregister("dl")
    return out


def refresh_all(db_path) -> dict:
    """TRIMP pendientes + reconstrucción de daily_load. Reporte resumido."""
    con = connect(db_path)
    try:
        n_trimp = compute_trimp(con)
        daily = rebuild_daily_load(con)
        last = daily.iloc[-1] if not daily.empty else None
        return {
            "trimp_calculados": n_trimp,
            "dias_serie": int(len(daily)),
            "acwr_hoy": None if last is None or pd.isna(last["acwr"]) else round(float(last["acwr"]), 2),
            "riesgo_hoy": None if last is None else last["risk"],
        }
    finally:
        con.close()
