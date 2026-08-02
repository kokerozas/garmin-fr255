"""Motor de recomendaciones para prevención (D-014).

Reglas TRANSPARENTES (sin caja negra) evaluadas sobre el estado actual:
carga (ACWR, TSB, parones, monotonía) + recuperación (HRV, sueño, FC reposo).
Cada recomendación incluye el dato que la disparó, para que sea verificable
en los paneles. Basado en literatura de ciencias del deporte (Gabbett 2016:
ACWR y regreso tras parones; Foster 1998: monotonía; consenso sueño-lesión).

NO es consejo médico: el sistema ve la carga, no el cuerpo. El dolor manda.
"""
from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from garmin.db.schema import connect

# niveles: ok < info < atencion < alerta  (el dashboard los colorea)
_ORDER = {"alerta": 0, "atencion": 1, "info": 2, "ok": 3}


def _rec(nivel: str, titulo: str, detalle: str) -> dict:
    return {"nivel": nivel, "titulo": titulo, "detalle": detalle}


def build_recommendations(db_path) -> list[dict]:
    con = connect(db_path)
    try:
        hoy = con.execute(
            "SELECT ctl, atl, tsb, acwr, risk FROM daily_load ORDER BY date_local DESC LIMIT 1"
        ).fetchone()
        last7 = [
            r[0]
            for r in con.execute(
                "SELECT trimp FROM daily_load ORDER BY date_local DESC LIMIT 7"
            ).fetchall()
        ]
        last_act = con.execute("SELECT MAX(date_local) FROM activities").fetchone()[0]
        media_cronica = con.execute(
            """SELECT AVG(trimp) FROM
               (SELECT trimp FROM daily_load ORDER BY date_local DESC LIMIT 28)"""
        ).fetchone()[0]

        dm = con.execute(
            """SELECT date_local, hrv_last_night, hrv_baseline_lower,
                      COALESCE(resting_hr, hr_min) AS rhr, sleep_h
               FROM daily_metrics ORDER BY date_local DESC LIMIT 90"""
        ).df()
    finally:
        con.close()

    recs: list[dict] = []
    ctl, atl, tsb, acwr = (hoy[0], hoy[1], hoy[2], hoy[3]) if hoy else (0, 0, 0, None)
    dias_sin = (_dt.date.today() - last_act).days if last_act else None

    # --- 1. Parón (tu patrón histórico más frecuente) --------------------------
    if dias_sin is not None and dias_sin >= 10:
        recs.append(_rec(
            "alerta",
            f"Regreso gradual: llevas {dias_sin} días sin actividad",
            f"Tu forma (CTL {ctl:.0f}) decayó durante el parón y tu cuerpo perdió "
            "tolerancia a la carga. El mayor riesgo de lesión muscular está en el "
            "PRIMER partido a fondo tras semanas quietas (es exactamente cuando tu "
            "ACWR histórico salta a rojo). Plan: 2-3 sesiones suaves esta semana "
            "(trote/caminata Z2, 30-45 min) ANTES del próximo partido completo, y en "
            "ese partido considera no jugar los 90 minutos.",
        ))
    elif dias_sin is not None and dias_sin >= 5:
        recs.append(_rec(
            "info",
            f"{dias_sin} días sin actividad",
            "Retoma con una sesión moderada antes de volver a intensidad de partido.",
        ))

    # --- 2. Semáforo ACWR ------------------------------------------------------
    if acwr is not None and not np.isnan(acwr):
        if acwr >= 1.5:
            tope = (media_cronica or 0) * 1.1
            recs.append(_rec(
                "alerta",
                f"Carga disparada: ACWR {acwr:.2f} (zona roja)",
                f"Esta semana llevas ~{acwr:.1f}× tu base crónica. Los próximos 3-5 "
                "días son la ventana de mayor riesgo: recorta volumen e intensidad "
                f"(dosis diaria ≤ {tope:.0f} TRIMP) y prioriza dormir.",
            ))
        elif acwr >= 1.3:
            recs.append(_rec(
                "atencion",
                f"ACWR {acwr:.2f}: precaución",
                "Estás escalando la carga más rápido de lo que tu base absorbe. Una "
                "sesión suave o un descanso esta semana te devuelve a la banda verde.",
            ))
        elif acwr < 0.8 and (dias_sin or 0) < 10:
            recs.append(_rec(
                "info",
                f"Subcarga (ACWR {acwr:.2f})",
                "Estás entrenando bajo tu base: no es peligroso hoy, pero erosiona la "
                "tolerancia futura. Agrega una dosis moderada para sostener la forma.",
            ))

    # --- 3. Balance TSB --------------------------------------------------------
    if tsb is not None and tsb < -25:
        recs.append(_rec(
            "atencion",
            f"Fatiga acumulada alta (TSB {tsb:+.0f})",
            "Llevas varios días cargando por sobre tu forma. Un día de descanso o "
            "regenerativo evita que la fatiga se convierta en lesión o enfermedad.",
        ))

    # --- 4. Monotonía (Foster) -------------------------------------------------
    if last7 and len(last7) == 7:
        arr = np.array([x or 0.0 for x in last7], dtype=float)
        if arr.sum() > 0 and arr.std() > 0:
            monotonia = arr.mean() / arr.std()
            if monotonia > 2.0:
                recs.append(_rec(
                    "info",
                    f"Semana monótona (índice {monotonia:.1f})",
                    "Dosis muy parejas todos los días elevan el 'strain' total. "
                    "Alterna días fuertes con días claramente suaves.",
                ))

    # --- 5. Recuperación: HRV, sueño, FC reposo -------------------------------
    if not dm.empty:
        hoy_d = _dt.date.today()

        hrv_row = dm.dropna(subset=["hrv_last_night"])
        if not hrv_row.empty:
            h = hrv_row.iloc[0]
            fecha_h = pd.Timestamp(h["date_local"]).date()
            if (hoy_d - fecha_h).days <= 3 and h["hrv_baseline_lower"] and \
                    h["hrv_last_night"] < h["hrv_baseline_lower"]:
                recs.append(_rec(
                    "atencion",
                    f"HRV bajo tu banda ({h['hrv_last_night']:.0f} ms)",
                    "Recuperación incompleta esta noche: si toca entrenar, que sea "
                    "suave; si toca partido, calienta más largo y escucha al cuerpo.",
                ))

        sueño3 = dm["sleep_h"].dropna().head(3)
        if len(sueño3) >= 2 and sueño3.mean() < 6.5:
            recs.append(_rec(
                "atencion",
                f"Sueño corto: {sueño3.mean():.1f} h de media reciente",
                "Dormir <7 h sostenido multiplica el riesgo de lesión y frena la "
                "adaptación. Es tu palanca de prevención más barata: apunta a 7.5-8 h.",
            ))

        rhr7 = dm["rhr"].dropna().head(7)
        rhr28 = dm["rhr"].dropna().iloc[7:35]
        if len(rhr7) >= 4 and len(rhr28) >= 10 and rhr7.mean() > rhr28.mean() + 5:
            recs.append(_rec(
                "atencion",
                f"FC reposo elevada ({rhr7.mean():.0f} vs {rhr28.mean():.0f} ppm)",
                "Tu pulso basal lleva días sobre tu norma: fatiga acumulada, mal "
                "sueño o infección incubando. Baja la intensidad hasta que vuelva.",
            ))

    # --- 5b. Molestias del registro subjetivo (D-015) --------------------------
    try:
        from garmin.metrics.wellness import pain_status

        for d in pain_status(db_path, dias=10):
            if d["nivel_max"] >= 7:
                recs.append(_rec(
                    "alerta",
                    f"Dolor significativo en {d['zona'].lower()} ({d['nivel_max']}/10)",
                    "Un 7+ no se juega: reposo relativo de la zona, y si persiste "
                    "más de 72 h o reaparece al cargar, evaluación profesional.",
                ))
            elif d["veces_alto"] >= 2:
                recs.append(_rec(
                    "atencion",
                    f"Molestia recurrente en {d['zona'].lower()} ({d['nivel_max']}/10, "
                    f"{d['veces_alto']} registros)",
                    "La repetición es la señal: evita sprints máximos y cambios de "
                    "dirección bruscos hasta que baje de 3, y refuerza el trabajo "
                    "excéntrico suave de la zona.",
                ))
            elif d["nivel_max"] >= 4 and acwr is not None and not np.isnan(acwr) and acwr >= 1.3:
                recs.append(_rec(
                    "atencion",
                    f"Molestia en {d['zona'].lower()} + carga en escalada (ACWR {acwr:.2f})",
                    "La combinación molestia + subida de carga es el escenario típico "
                    "pre-lesión: recorta la próxima dosis.",
                ))
    except Exception:
        pass  # sin registros subjetivos aún: el resto del motor sigue funcionando

    # --- 6. Todo en orden ------------------------------------------------------
    if not any(r["nivel"] in ("alerta", "atencion") for r in recs):
        recs.append(_rec(
            "ok",
            "Sin señales de riesgo hoy",
            "Mantén el patrón protector: 2-3 dosis por semana, mezcla de intensidades "
            "y el ACWR ondulando en la banda verde.",
        ))

    # --- 7. Regla fija sobre el dolor (el sistema no lo ve) --------------------
    recs.append(_rec(
        "info",
        "Sobre el dolor: el sistema no lo ve — tú sí",
        "Dolor agudo o punzante durante el juego = parar, hielo y evaluar. Molestia "
        "que persiste >72 h, reaparece al cargar o altera tu técnica = kinesiólogo/"
        "traumatólogo. Nunca 'aguantes' jugando: estos números previenen, no curan.",
    ))

    recs.sort(key=lambda r: _ORDER.get(r["nivel"], 9))
    return recs
