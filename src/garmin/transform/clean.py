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


# Velocidad: mismos principios que la FC, distinta física (D-017).
SPEED_MAX_MS = 9.0        # 32.4 km/h — techo plausible para este atleta
ACCEL_MAX_MS2 = 6.0       # la aceleración humana máxima ronda 10 m/s²; 6 deja margen


def flag_speed(samples: pd.DataFrame, v_max: float = SPEED_MAX_MS) -> pd.DataFrame:
    """Agrega speed_valid / speed_flag, espejo de flag_heart_rate. Devuelve copia.

    Necesario porque la velocidad cruda del reloj tiene ruido puro: en fútbol el
    percentil 99 es 12.12 m/s (43.6 km/h) y el máximo 31.67 m/s (114 km/h). El GPS va
    en la MUÑECA y el balanceo del brazo corrompe la velocidad Doppler; además los
    cambios de dirección degradan la medida (Rawstorn et al. 2014, PLoS ONE 9(4)).
    Igual que con la FC, se MARCA y nunca se borra (invariante 2).
    """
    df = samples.copy()
    if df.empty or "speed_ms" not in df.columns:
        df["speed_valid"] = pd.Series(dtype=bool)
        df["speed_flag"] = pd.Series(dtype=object)
        return df

    v = pd.to_numeric(df["speed_ms"], errors="coerce")
    flag = pd.Series([None] * len(df), dtype=object, index=df.index)

    missing = v.isna()
    flag[missing] = "sin_dato"

    out_of_range = (~missing) & ((v < 0) | (v > v_max))
    flag[out_of_range] = "fuera_de_rango"

    # Salto imposible: se compara contra la última muestra CONFIABLE, no contra la
    # anterior cruda, para que un artefacto no contamine a su vecino sano.
    base = v.mask(missing | out_of_range)
    ref_v = base.shift(1).ffill()
    if "elapsed_s" in df.columns:
        t = pd.to_numeric(df["elapsed_s"], errors="coerce")
        ref_t = t.where(base.notna()).shift(1).ffill()
        dt = (t - ref_t).clip(lower=1)
    else:
        dt = 1.0
    salto = base.notna() & ref_v.notna() & ((base - ref_v).abs() / dt > ACCEL_MAX_MS2)
    flag[salto] = "salto_imposible"

    # Sin GPS es una anotación de contexto, no invalida el valor por sí sola: el
    # firmware también deriva velocidad del acelerómetro.
    if {"lat", "lon"} <= set(df.columns):
        sin_gps = df["lat"].isna() | df["lon"].isna()
        flag[sin_gps & flag.isna()] = "sin_gps"

    df["speed_valid"] = flag.isna() | (flag == "sin_gps")
    df["speed_flag"] = flag
    return df


def speed_coverage(samples: pd.DataFrame) -> float:
    """Proporción de muestras con velocidad utilizable."""
    if samples.empty or "speed_valid" not in samples.columns:
        return 0.0
    return float(samples["speed_valid"].mean())
