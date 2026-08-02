"""Limpieza D-008: reglas automáticas con marcado reversible.

Nunca se borra ni se sobreescribe el dato original: cada muestra conserva su
valor crudo y recibe columnas de auditoría (hr_valid, hr_flag) que explican
por qué se descarta del cálculo. Crítico con FC de muñeca en fútbol (D-006).
"""
from __future__ import annotations

import pandas as pd

HR_MIN, HR_MAX = 30, 230      # rango fisiológicamente plausible (ppm)
SPIKE_BPM_PER_S = 30          # salto máximo creíble entre muestras consecutivas


def flag_heart_rate(samples: pd.DataFrame) -> pd.DataFrame:
    """Agrega hr_valid / hr_flag a la serie de muestras. Devuelve copia."""
    df = samples.copy()
    if df.empty or "hr" not in df.columns:
        df["hr_valid"] = pd.Series(dtype=bool)
        df["hr_flag"] = pd.Series(dtype=object)
        return df

    hr = pd.to_numeric(df["hr"], errors="coerce")
    flag = pd.Series([None] * len(df), dtype=object)

    missing = hr.isna()
    flag[missing] = "sin_dato"

    out_of_range = (~missing) & ((hr < HR_MIN) | (hr > HR_MAX))
    flag[out_of_range] = "fuera_de_rango"

    # Picos: cambio demasiado brusco respecto a la ÚLTIMA muestra confiable
    # (si comparáramos contra la anterior cruda, un artefacto contaminaría al vecino sano).
    base = hr.mask(missing | out_of_range)
    ref_hr = base.shift(1).ffill()
    if "elapsed_s" in df.columns:
        t = pd.to_numeric(df["elapsed_s"], errors="coerce")
        ref_t = t.where(base.notna()).shift(1).ffill()
        dt = (t - ref_t).clip(lower=1)
    else:
        dt = 1.0
    spike = base.notna() & ref_hr.notna() & ((base - ref_hr).abs() / dt > SPIKE_BPM_PER_S)
    flag[spike] = "pico_artefacto"

    df["hr_valid"] = flag.isna()
    df["hr_flag"] = flag
    return df


def hr_coverage(samples: pd.DataFrame) -> float:
    """Proporción de muestras con FC utilizable (calidad de la sesión)."""
    if samples.empty or "hr_valid" not in samples.columns:
        return 0.0
    return float(samples["hr_valid"].mean())
