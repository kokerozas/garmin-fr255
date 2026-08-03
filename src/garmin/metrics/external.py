"""Carga externa por sesión (D-017/D-018): lo que sufrió el músculo.

El TRIMP mide carga INTERNA (lo que le costó al corazón). La distancia y los metros
por minuto miden carga EXTERNA (el trabajo mecánico). Vanrenterghem et al. (2017,
Sports Medicine 47(11):2135-2142) las formulan como dos vías distintas, y la
distinción importa aquí porque el tejido muscular se lesiona por carga mecánica, no
por frecuencia cardíaca: dos partidos con el mismo TRIMP pueden tener demandas
mecánicas muy distintas.

EL PORTERO: `gps_grade`. Antes de calcular nada hay que saber a qué frecuencia se
grabó la señal. Auditoría sobre la base real (D-017): el perfil "Fútbol" del FR255
graba con Smart Recording, con intervalo mediano de 2.74 s, mientras que los perfiles
de carrera sí están a 1.00 s. Un sprint de fútbol dura 2-4 s: con 2.74 s entre
muestras cae en una o dos muestras y NO se puede reconstruir. Por eso la distancia a
alta velocidad y el conteo de sprints quedan en NULL salvo con grado 'alta'.
Preferimos no dar un número antes que dar uno inventado (D-016).

LIMITACIONES que acompañan a todo lo de este módulo:
- El GPS va en la MUÑECA, no en un pod de 10 Hz en la espalda: el balanceo del brazo
  corrompe la velocidad Doppler (Scott, Scott & Kelly 2016, J Strength Cond Res
  30(5):1470-1490) y los cambios de dirección degradan la distancia (Rawstorn et al.
  2014, PLoS ONE 9(4):e93693).
- El error típico de distancia es 5-7 %: diferencias menores al 10 % entre sesiones
  NO son interpretables.
- Los umbrales de alta velocidad son de la literatura y NO están individualizados.
- Los valores absolutos no son comparables con el fútbol profesional. El ~63 m/min
  observado sugiere que la duración incluye tiempo no jugado, o canchas reducidas.

Referencias adicionales: Casamichana et al. (2013), J Strength Cond Res 27(2):369-374
(relación entre indicadores de carga en fútbol); Akubat et al. (2014), IJSPP
9(3):457-462 (índice de eficiencia externa:interna).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from garmin.db.schema import connect
from garmin.metrics.load import efficiency_index

# Umbrales estándar de la literatura de fútbol. NO individualizados: se documentan
# como tales y solo se aplican cuando la señal los soporta.
HSR_MS = 5.5      # 19.8 km/h — high speed running
SPRINT_MS = 7.0   # 25.2 km/h

# Cortes de calidad de la señal, en segundos entre muestras.
DT_ALTA, DT_MEDIA = 1.2, 2.0

# Zonas Z2..Z5 (≥60 % FCmax) como proxy del tiempo realmente jugado: la duración
# total incluye calentamiento y banca.
ZONAS_ACTIVAS = (2, 3, 4, 5)


def grade_gps(dt_mediano: float | None, tiene_gps: bool) -> str:
    """Grado de la señal: decide qué métricas se permiten calcular."""
    if not tiene_gps or dt_mediano is None or pd.isna(dt_mediano):
        return "sin_gps"
    if dt_mediano <= DT_ALTA:
        return "alta"
    if dt_mediano <= DT_MEDIA:
        return "media"
    return "baja"


def _dt_mediano(elapsed: pd.Series) -> float | None:
    """Intervalo mediano entre muestras. Mide la cadencia real de grabación."""
    d = pd.to_numeric(elapsed, errors="coerce").dropna().diff().dropna()
    d = d[(d > 0) & (d < 60)]          # cortes largos = pausas, no cadencia
    return None if d.empty else float(d.median())


def session_external(con) -> int:
    """Reconstruye activity_external. Idempotente (DELETE + INSERT), devuelve filas."""
    acts = con.execute(
        """SELECT activity_id, distance_m, duration_s, trimp, trimp_method, hr_coverage
           FROM activities WHERE n_samples > 0"""
    ).df()
    if acts.empty:
        con.execute("DELETE FROM activity_external")
        return 0

    activas = con.execute(
        f"""SELECT activity_id, SUM(seconds) AS s
            FROM activity_zones WHERE zone IN {ZONAS_ACTIVAS}
            GROUP BY activity_id"""
    ).df().set_index("activity_id")["s"].to_dict()

    filas = []
    for a in acts.itertuples():
        smp = con.execute(
            """SELECT elapsed_s, speed_ms, speed_valid, lat FROM samples
               WHERE activity_id = ? ORDER BY elapsed_s""",
            [a.activity_id],
        ).df()
        if smp.empty:
            continue

        dt_med = _dt_mediano(smp["elapsed_s"])
        tiene_gps = bool(smp["lat"].notna().any())
        grado = grade_gps(dt_med, tiene_gps)

        # Si la limpieza de velocidad aún no corrió, se usa la velocidad cruda pero
        # acotada al techo plausible: nunca se deja pasar un 114 km/h a los cálculos.
        v = pd.to_numeric(smp["speed_ms"], errors="coerce")
        if "speed_valid" in smp and smp["speed_valid"].notna().any():
            v = v.where(smp["speed_valid"].fillna(False))
        v = v.where((v >= 0) & (v <= 9.0))
        v_validas = v.dropna()

        dur_total_min = (a.duration_s or 0) / 60.0
        dur_activa_min = activas.get(a.activity_id, 0.0) / 60.0
        dist = a.distance_m

        # Percentil 99, no el máximo: el máximo es ruido incluso tras la limpieza.
        v_max = float(np.percentile(v_validas, 99)) if len(v_validas) >= 20 else None

        # Alta velocidad SOLO con señal de grado alto (ver docstring del módulo).
        hsr = sprint = n_sprints = None
        if grado == "alta" and dt_med and len(v_validas) >= 20:
            paso = v.notna() * float(dt_med)
            hsr = float((v.where(v >= HSR_MS).notna() * paso * v.fillna(0)).sum())
            sprint = float((v.where(v >= SPRINT_MS).notna() * paso * v.fillna(0)).sum())
            en_sprint = (v >= SPRINT_MS).fillna(False)
            n_sprints = int((en_sprint & ~en_sprint.shift(1, fill_value=False)).sum())

        filas.append({
            "activity_id": a.activity_id,
            "distance_m": dist,
            "dur_total_min": round(dur_total_min, 1) if dur_total_min else None,
            "dur_activa_min": round(dur_activa_min, 1) if dur_activa_min else None,
            "m_per_min": round(dist / dur_total_min, 1) if dist and dur_total_min else None,
            "m_per_min_act": round(dist / dur_activa_min, 1) if dist and dur_activa_min else None,
            "hsr_m": hsr,
            "sprint_m": sprint,
            "n_sprints": n_sprints,
            "v_max_ms": round(v_max, 2) if v_max else None,
            "eff_index": efficiency_index(dist, a.trimp, a.trimp_method,
                                          a.hr_coverage, a.duration_s),
            "gps_grade": grado,
        })
        con.execute(
            "UPDATE activities SET sample_dt_s = ?, gps_grade = ? WHERE activity_id = ?",
            [dt_med, grado, a.activity_id],
        )

    out = pd.DataFrame(filas)
    con.execute("DELETE FROM activity_external")
    if out.empty:
        return 0
    cols = ", ".join(out.columns)
    con.register("ext", out)
    con.execute(f"INSERT INTO activity_external ({cols}) SELECT {cols} FROM ext")
    con.unregister("ext")
    return len(out)


def refresh_external(db_path) -> dict:
    """Recalcula la carga externa y resume qué se pudo calcular y qué no."""
    con = connect(db_path)
    try:
        n = session_external(con)
        grados = con.execute(
            "SELECT gps_grade, COUNT(*) FROM activity_external GROUP BY 1"
        ).fetchall()
        con_hsr = con.execute(
            "SELECT COUNT(*) FROM activity_external WHERE hsr_m IS NOT NULL"
        ).fetchone()[0]
        con_eff = con.execute(
            "SELECT COUNT(*) FROM activity_external WHERE eff_index IS NOT NULL"
        ).fetchone()[0]
    finally:
        con.close()
    return {
        "sesiones": n,
        "por_grado": {g: c for g, c in grados},
        "con_alta_velocidad": con_hsr,
        "con_eficiencia": con_eff,
    }
