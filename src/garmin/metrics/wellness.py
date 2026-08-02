"""Registro subjetivo y disposición pre-partido (D-015).

Dos piezas que el reloj no puede medir:
- RPE (esfuerzo percibido 0-10, Foster): cómo se SINTIÓ la sesión. Con la duración
  da la carga sRPE (RPE × minutos), la segunda vara junto al TRIMP.
- Molestias 0-10 por zona típica de fútbol: la señal más temprana de lesión.

Y la síntesis operativa: match_readiness() — el semáforo "¿Puedo jugar hoy?"
con 3 factores (carga, recuperación, molestias).
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd

from garmin.db.schema import connect

ZONAS = {
    "d_isquios": "Isquiotibiales",
    "d_cuadriceps": "Cuádriceps",
    "d_gemelos": "Gemelos / sóleo",
    "d_aductores": "Aductores",
    "d_rodilla": "Rodilla",
    "d_tobillo": "Tobillo / pie",
    "d_espalda": "Espalda baja",
}

RPE_ESCALA = ("0 reposo · 1-2 muy fácil · 3-4 algo duro · 5-6 duro · "
              "7-8 muy duro · 9-10 máximo")


def save_log(db_path, *, date_local, activity_id, rpe, duration_min,
             dolores: dict, nota: str) -> None:
    """Guarda (o reemplaza) el registro de una sesión o del día."""
    log_id = f"a:{activity_id}" if activity_id else f"d:{date_local}"
    con = connect(db_path)
    try:
        con.execute("DELETE FROM wellness_log WHERE log_id = ?", [log_id])
        con.execute(
            """INSERT INTO wellness_log
               (log_id, date_local, activity_id, rpe, duration_min,
                d_isquios, d_cuadriceps, d_gemelos, d_aductores,
                d_rodilla, d_tobillo, d_espalda, nota)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                log_id, date_local, activity_id, int(rpe),
                int(duration_min) if duration_min else None,
                *(int(dolores.get(z, 0)) for z in ZONAS),
                (nota or "").strip() or None,
            ],
        )
    finally:
        con.close()


def fetch_logs(db_path, limit: int = 20) -> pd.DataFrame:
    """Últimos registros con su carga sRPE y la actividad asociada."""
    con = connect(db_path)
    try:
        return con.execute(
            """SELECT w.date_local, a.sport, w.rpe, w.duration_min,
                      w.rpe * COALESCE(w.duration_min, 0) AS srpe,
                      w.d_isquios, w.d_cuadriceps, w.d_gemelos, w.d_aductores,
                      w.d_rodilla, w.d_tobillo, w.d_espalda, w.nota
               FROM wellness_log w
               LEFT JOIN activities a USING (activity_id)
               ORDER BY w.date_local DESC, w.created_at DESC
               LIMIT ?""",
            [limit],
        ).df()
    finally:
        con.close()


def pain_status(db_path, dias: int = 7) -> list[dict]:
    """Molestias relevantes recientes: [{zona, nivel_max, veces_alto, ultimo}]."""
    con = connect(db_path)
    try:
        df = con.execute(
            """SELECT * FROM wellness_log
               WHERE date_local >= current_date - INTERVAL (?) DAY
               ORDER BY date_local DESC""",
            [dias],
        ).df()
    finally:
        con.close()
    out = []
    for col, nombre in ZONAS.items():
        if df.empty or col not in df:
            continue
        s = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if s.max() > 0:
            out.append({
                "zona": nombre,
                "nivel_max": int(s.max()),
                "veces_alto": int((s >= 4).sum()),
                "ultimo": int(s.iloc[0]),
            })
    out.sort(key=lambda x: -x["nivel_max"])
    return out


def _factor(estado: str, razon: str) -> dict:
    return {"estado": estado, "razon": razon}  # estado: ok | ojo | alto


def match_readiness(db_path) -> dict:
    """Semáforo '¿Puedo jugar hoy?' — carga, recuperación y molestias."""
    con = connect(db_path)
    try:
        dl = con.execute(
            "SELECT acwr FROM daily_load ORDER BY date_local DESC LIMIT 1"
        ).fetchone()
        last_act = con.execute("SELECT MAX(date_local) FROM activities").fetchone()[0]
        dm = con.execute(
            """SELECT date_local, sleep_h, hrv_last_night, hrv_baseline_lower,
                      COALESCE(resting_hr, hr_min) AS rhr
               FROM daily_metrics ORDER BY date_local DESC LIMIT 35"""
        ).df()
    finally:
        con.close()

    hoy = _dt.date.today()

    # --- Factor 1: carga ------------------------------------------------------
    acwr = dl[0] if dl and dl[0] is not None else None
    dias_sin = (hoy - last_act).days if last_act else None
    if dias_sin is not None and dias_sin >= 10:
        carga = _factor("alto", f"{dias_sin} días sin actividad: cuerpo desacostumbrado")
    elif acwr is not None and not pd.isna(acwr) and acwr >= 1.5:
        carga = _factor("alto", f"ACWR {acwr:.2f} en zona roja")
    elif acwr is not None and not pd.isna(acwr) and acwr >= 1.3:
        carga = _factor("ojo", f"ACWR {acwr:.2f} en precaución")
    elif dias_sin is not None and dias_sin >= 5:
        carga = _factor("ojo", f"{dias_sin} días sin actividad")
    else:
        carga = _factor("ok", "carga dentro de tu banda habitual")

    # --- Factor 2: recuperación ----------------------------------------------
    problemas, sin_dato = [], True
    if not dm.empty:
        sueño = dm["sleep_h"].dropna()
        if not sueño.empty:
            sin_dato = False
            if sueño.iloc[0] < 6.0:
                problemas.append(f"dormiste {sueño.iloc[0]:.1f} h")
        hrv = dm.dropna(subset=["hrv_last_night"])
        if not hrv.empty:
            h = hrv.iloc[0]
            fecha_h = pd.Timestamp(h["date_local"]).date()
            if (hoy - fecha_h).days <= 2 and h["hrv_baseline_lower"] and \
                    h["hrv_last_night"] < h["hrv_baseline_lower"]:
                sin_dato = False
                problemas.append(f"HRV bajo tu banda ({h['hrv_last_night']:.0f} ms)")
        rhr7 = dm["rhr"].dropna().head(7)
        rhr28 = dm["rhr"].dropna().iloc[7:35]
        if len(rhr7) >= 4 and len(rhr28) >= 10:
            sin_dato = False
            if rhr7.mean() > rhr28.mean() + 5:
                problemas.append("FC reposo elevada sobre tu norma")
    if sin_dato:
        recup = _factor("ojo", "sin datos recientes de sueño/HRV: sincroniza el reloj")
    elif len(problemas) >= 2:
        recup = _factor("alto", " y ".join(problemas))
    elif problemas:
        recup = _factor("ojo", problemas[0])
    else:
        recup = _factor("ok", "sueño, HRV y FC reposo en orden")

    # --- Factor 3: molestias --------------------------------------------------
    dolores = pain_status(db_path, dias=7)
    graves = [d for d in dolores if d["nivel_max"] >= 7]
    medios = [d for d in dolores if 4 <= d["nivel_max"] < 7]
    if graves:
        mol = _factor("alto", f"{graves[0]['zona']} con dolor {graves[0]['nivel_max']}/10 reciente")
    elif medios:
        mol = _factor("ojo", f"{medios[0]['zona']} con molestia {medios[0]['nivel_max']}/10")
    elif dolores:
        mol = _factor("ok", "solo molestias leves reportadas")
    else:
        mol = _factor("ok", "sin molestias reportadas (registra tras cada sesión)")

    factores = {"Carga": carga, "Recuperación": recup, "Molestias": mol}
    estados = [f["estado"] for f in factores.values()]
    if "alto" in estados:
        overall = ("alto", "🔴 Alto riesgo hoy — modera minutos o descansa")
    elif "ojo" in estados:
        overall = ("ojo", "🟡 Jugable con cuidado — calienta largo y escucha al cuerpo")
    else:
        overall = ("ok", "🟢 Listo para jugar")
    return {"estado": overall[0], "titulo": overall[1], "factores": factores}
