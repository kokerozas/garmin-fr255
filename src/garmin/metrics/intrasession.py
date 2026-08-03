"""Fatiga intra-partido: coste cardíaco de la 2ª mitad vs la 1ª (D-018).

Mohr, Krustrup & Bangsbo (2003), "Match performance of high-standard soccer players
with special reference to development of fatigue", Journal of Sports Sciences
21(7):519-528, documentaron que el rendimiento de carrera cae en la segunda parte.
Aquí, en vez de medir solo la caída de distancia (poco fiable con GPS de muñeca), se
mide la RELACIÓN interno:externo por mitad — cuánta frecuencia cardíaca cuesta cada
metro por segundo. Si en la segunda mitad se corre menos Y con más pulso por metro,
esa es la firma de la fatiga acumulada.

Por qué importa para el objetivo #1 del proyecto: el tramo final del partido concentra
las lesiones musculares por fatiga, así que los partidos con más decoupling son los
candidatos a mayor riesgo.

CÓMO SE PARTE EL PARTIDO. Por tiempo transcurrido, no por lap: 90 de los 96 partidos
con series tienen un solo lap, o sea que el reloj nunca marcó el medio tiempo. Si la
actividad sí trae dos o más laps útiles se usan esos y se registra metodo='laps'.

LIMITACIONES, que no son menores:
- Son partidos RECREATIVOS: no hay control de sustituciones, de tiempo realmente
  jugado, ni de si el reloj siguió corriendo en el descanso o en el banquillo.
- En fútbol el intervalo entre muestras es ~2.74 s (D-017), así que la velocidad es de
  baja calidad. Cuando no es utilizable se calcula la versión SOLO CARDÍACA (deriva de
  %FCmax entre mitades) y lo que dependa de velocidad queda en NULL.
- Por todo lo anterior, se lee como SERIE LONGITUDINAL contra sí misma. El valor
  absoluto no significa nada ni es comparable con la literatura.

Referencia complementaria: Bangsbo, Mohr & Krustrup (2006), Journal of Sports Sciences
24(7):665-674 (demandas físicas y metabólicas del futbolista de élite).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from garmin.db.schema import connect

DUR_MIN_S = 1800.0       # 30 min: bajo eso partir en mitades no dice nada
COBERTURA_MIN = 0.8      # calidad de FC mínima para confiar en el coste cardíaco
VEL_MIN_MS = 0.5         # bajo esto el cociente coste = %FC/vel explota
DEPORTES = ("soccer",)


def _mitad(df: pd.DataFrame, fc_max: float, fc_rest: float) -> dict | None:
    """Métricas de una mitad: FC ponderada por tiempo, distancia, velocidad y coste."""
    d = df.dropna(subset=["hr"])
    if d.empty:
        return None
    dt = pd.to_numeric(d["elapsed_s"], errors="coerce").diff().clip(lower=0, upper=10).fillna(1)
    total_dt = float(dt.sum())
    if total_dt <= 0:
        return None

    hr = pd.to_numeric(d["hr"], errors="coerce").to_numpy(float)
    hr_media = float(np.average(hr, weights=dt.to_numpy(float)))
    pct_fcmax = hr_media / fc_max if fc_max else None
    # Fracción de reserva cardíaca: normaliza entre atletas y entre días.
    pct_reserva = ((hr_media - fc_rest) / max(fc_max - fc_rest, 1.0)) if fc_max else None

    v = pd.to_numeric(d.get("speed_ms"), errors="coerce") if "speed_ms" in d else None
    if v is not None and "speed_valid" in d and d["speed_valid"].notna().any():
        v = v.where(d["speed_valid"].fillna(False))
    v = v.where((v > 0) & (v <= 9.0)) if v is not None else None
    vel_media = float(v.mean()) if v is not None and v.notna().any() else None
    dist = float(vel_media * total_dt) if vel_media else None

    coste = (pct_reserva / vel_media
             if (pct_reserva is not None and vel_media and vel_media >= VEL_MIN_MS) else None)
    return {"hr": round(hr_media, 1), "pct_fcmax": pct_fcmax, "dist": dist,
            "vel": vel_media, "coste": coste}


def rebuild_intrasession(con) -> int:
    """Reconstruye activity_intrasession. Idempotente; devuelve filas escritas."""
    params = dict(con.execute("SELECT key, value FROM params").fetchall())
    fc_max = float(params.get("fc_maxima") or 190.0)
    fc_rest = float(params.get("fc_reposo") or 55.0)

    marcas = ",".join("?" * len(DEPORTES))
    acts = con.execute(
        f"""SELECT activity_id, duration_s, hr_coverage FROM activities
            WHERE sport IN ({marcas}) AND n_samples > 0
              AND duration_s >= ? AND COALESCE(hr_coverage, 0) >= ?""",
        [*DEPORTES, DUR_MIN_S, COBERTURA_MIN],
    ).df()

    filas = []
    for a in acts.itertuples():
        smp = con.execute(
            """SELECT elapsed_s, hr, hr_valid, speed_ms, speed_valid FROM samples
               WHERE activity_id = ? AND hr_valid ORDER BY elapsed_s""",
            [a.activity_id],
        ).df()
        if len(smp) < 60:
            continue

        corte = smp["elapsed_s"].min() + (smp["elapsed_s"].max() - smp["elapsed_s"].min()) / 2
        m1 = _mitad(smp[smp["elapsed_s"] <= corte], fc_max, fc_rest)
        m2 = _mitad(smp[smp["elapsed_s"] > corte], fc_max, fc_rest)
        if not m1 or not m2:
            continue

        # Con velocidad utilizable, el decoupling es interno:externo. Sin ella, se
        # informa solo la deriva cardíaca, que es lo único defendible con ese dato.
        if m1["coste"] and m2["coste"]:
            decoupling = (m2["coste"] / m1["coste"] - 1) * 100
        elif m1["pct_fcmax"] and m2["pct_fcmax"]:
            decoupling = (m2["pct_fcmax"] / m1["pct_fcmax"] - 1) * 100
        else:
            decoupling = None

        drop = ((m2["dist"] / m1["dist"] - 1) * 100
                if (m1["dist"] and m2["dist"] and m1["dist"] > 0) else None)

        filas.append({
            "activity_id": a.activity_id,
            "hr1": m1["hr"], "hr2": m2["hr"],
            "pct_fcmax1": m1["pct_fcmax"], "pct_fcmax2": m2["pct_fcmax"],
            "dist1_m": m1["dist"], "dist2_m": m2["dist"],
            "vel1_ms": m1["vel"], "vel2_ms": m2["vel"],
            "coste1": m1["coste"], "coste2": m2["coste"],
            "decoupling_pct": None if decoupling is None else round(decoupling, 2),
            "dist_drop_pct": None if drop is None else round(drop, 2),
            "metodo": "tiempo",
        })

    out = pd.DataFrame(filas)
    con.execute("DELETE FROM activity_intrasession")
    if out.empty:
        return 0
    cols = ", ".join(out.columns)
    con.register("intra", out)
    con.execute(f"INSERT INTO activity_intrasession ({cols}) SELECT {cols} FROM intra")
    con.unregister("intra")
    return len(out)


def refresh_intrasession(db_path) -> dict:
    con = connect(db_path)
    try:
        n = rebuild_intrasession(con)
        row = con.execute(
            """SELECT AVG(decoupling_pct), COUNT(coste1)
               FROM activity_intrasession WHERE decoupling_pct IS NOT NULL"""
        ).fetchone()
    finally:
        con.close()
    media = None if not row or row[0] is None else round(float(row[0]), 1)
    return {"partidos": n, "decoupling_medio_pct": media,
            "con_velocidad": int(row[1]) if row and row[1] else 0}


def fetch_intrasession(db_path, limit: int = 60) -> pd.DataFrame:
    """Serie por partido, lista para graficar (viz.fig_decoupling)."""
    con = connect(db_path)
    try:
        return con.execute(
            """SELECT a.date_local, i.decoupling_pct, i.dist_drop_pct,
                      i.pct_fcmax1, i.pct_fcmax2, i.metodo
               FROM activity_intrasession i JOIN activities a USING (activity_id)
               WHERE i.decoupling_pct IS NOT NULL
               ORDER BY a.date_local DESC LIMIT ?""",
            [limit],
        ).df().sort_values("date_local")
    finally:
        con.close()
