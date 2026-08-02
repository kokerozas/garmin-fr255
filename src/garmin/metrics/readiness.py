"""Índice compuesto de disposición por z-scores individuales (D-017).

Idea central
------------
No existe un "número de recuperación" universal: lo que para otra persona es una
noche mala puede ser tu noche normal. Por eso **cada variable se compara contra
tu propia historia reciente**: z = (valor de hoy − tu media móvil) / tu desviación
móvil. Un z de −1 significa "una desviación estándar peor que tu normal de los
últimos 60 días", y eso sí es comparable entre variables con unidades distintas
(ppm, horas, ms, puntos).

Por qué se agrupa en DOMINIOS antes de promediar
------------------------------------------------
`sleep_score`, `stress` y Body Battery salen del **mismo motor propietario de
Garmin** y están correlacionados entre sí: promediarlos como si fueran variables
independientes le daría triple peso al bloque Garmin y ninguno al resto. Se
promedia entonces dentro de cada dominio fisiológico y después entre dominios:

- ``autonomico``  FC en reposo (invertida) + HRV nocturno (ln rMSSD)
- ``sueno``       horas dormidas + puntaje de sueño
- ``carga``       TSB de ``daily_load``, normalizado por su propia historia
- ``subjetivo``   índice de Hooper del registro manual (``wellness_log``)

El índice final es el promedio de los dominios **disponibles**, con
``n_dominios`` explícito al lado. Si hay menos de 2 dominios evaluables se
devuelve ``None`` con un motivo: nunca un número inventado ni un dato imputado.

Referencias primarias (D-016)
-----------------------------
- Buchheit, M. (2014). *Monitoring training status with HR measures: do all roads
  lead to Rome?* Frontiers in Physiology 5:73. — Base del uso de FC en reposo y
  HRV como marcadores de estado, siempre por tendencia individual y no por
  valores absolutos ni cortes poblacionales.
- Thornton, H.R., Delaney, J.A., Duthie, G.M. & Dascombe, B.J. (2019).
  *Developing Athlete Monitoring Systems in Team Sports: Data Analysis and
  Visualization.* Int J Sports Physiol Perform 14(6):698-705. — Recomienda
  z-scores individuales sobre líneas base móviles y reportar la incertidumbre
  junto al dato, en vez de un semáforo sin contexto.
- Robertson, S., Bartlett, J.D. & Gastin, P.B. (2017). *Red, Amber, or Green?
  Athlete Monitoring in Team Sport: The Need for Decision-Support Systems.*
  Int J Sports Physiol Perform 12(Suppl 2):S2-73-S2-79. — Advierte
  explícitamente que **no existe estandarización** en cómo se fijan los umbrales
  de "bandera" entre equipos y sistemas; por eso aquí el corte se declara como
  convención, no como hallazgo.
- Saw, A.E., Main, L.C. & Gastin, P.B. (2016). *Monitoring the athlete training
  response: subjective self-reported measures trump commonly used objective
  measures.* Br J Sports Med 50(5):281-291. — Lo subjetivo responde a la carga
  con más sensibilidad que lo objetivo y **no es redundante con ello**: por eso
  el dominio ``subjetivo`` pesa igual que los tres objetivos y no se descuenta.
- Plews, D.J., Laursen, P.B., Stanley, J., Kilding, A.E. & Buchheit, M. (2013).
  *Training adaptation and heart rate variability in elite endurance athletes.*
  Sports Med 43(9):773-781. — El rMSSD se transforma con logaritmo natural antes
  de promediar o normalizar (su distribución es sesgada a la derecha).
- Hooper, S.L. & Mackinnon, L.T. (1995). *Monitoring overtraining in athletes.*
  Sports Med 20(5):321-327. — Índice de bienestar de 4 ítems (sueño, fatiga,
  estrés, dolor muscular) que alimenta el dominio subjetivo.

Limitaciones declaradas
-----------------------
1. **El corte z ≤ −1 es una convención de este proyecto, no un punto de corte
   clínico validado.** Robertson 2017 documenta justamente la ausencia de
   estandarización. Un conteo de banderas **no es un modelo de riesgo
   calibrado**: no predice lesión, solo señala días atípicos para conversarlos.
2. **Falsas alarmas por azar.** Con ~6 variables y un corte de −1 DE, bajo
   normalidad se espera ≈16% de banderas por variable y por día — casi una
   bandera diaria solo por ruido. Agrupar en 4 dominios promedia ese ruido y lo
   reduce, pero **no lo elimina**. Por eso importa la persistencia (varios días
   seguidos), no el día suelto.
3. **Autocorrelación.** El TSB viene de medias exponenciales, así que sus valores
   consecutivos no son independientes; su z mide "qué tan fresco estoy respecto
   de mi propio historial", no una probabilidad.
4. **HRV escaso.** El HRV nocturno existe solo desde 2026-07-18: hasta acumular
   ``min_n`` noches el dominio autonómico se sostiene únicamente en la FC en
   reposo, y así queda reflejado en ``n_dominios`` y en el detalle.
5. Los valores de Garmin (puntaje de sueño, HRV, FC en reposo) son medición de un
   tercero con metodología parcialmente cerrada (D-007): sirven como referencia y
   tendencia, no como verdad.
"""
from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from garmin.db.schema import connect

# --- Parámetros de la línea base móvil ---------------------------------------
# 60 días ≈ dos meses: suficiente para que la media represente "tu normal" sin
# arrastrar una temporada entera. 30 observaciones mínimas para que la DE no sea
# un número inventado con 3 datos.
VENTANA_Z = 60
MIN_N_Z = 30

# Umbrales de bandera. CONVENCIÓN del proyecto (ver limitación 1 del docstring).
UMBRAL_ALERTA = -1.0
UMBRAL_ATENCION = -0.5

# Puerta de validez del rMSSD nocturno: fuera de este rango es artefacto del
# reloj, no fisiología (FR255 mide por muñeca, sin banda).
HRV_MIN_MS, HRV_MAX_MS = 5.0, 300.0

# Cada dominio agrupa variables que miden lo mismo por vías distintas.
DOMINIOS: dict[str, tuple[str, tuple[str, ...]]] = {
    "z_autonomico": ("Autonómico", ("z_rhr", "z_hrv")),
    "z_sueno": ("Sueño", ("z_sleep_h", "z_sleep_score")),
    "z_carga": ("Carga", ("z_tsb",)),
    "z_subjetivo": ("Subjetivo", ("z_hooper",)),
}

# Etiqueta y frase para explicar en lenguaje natural el signo de cada variable.
# El z ya viene orientado: negativo = peor. La frase describe qué pasó de verdad.
_VARIABLES: dict[str, tuple[str, str, str]] = {
    "z_rhr": ("FC en reposo", "más alta que tu normal", "en tu rango habitual"),
    "z_hrv": ("HRV nocturno", "por debajo de tu banda", "en tu banda"),
    "z_sleep_h": ("horas de sueño", "por debajo de tu normal", "en tu normal"),
    "z_sleep_score": ("puntaje de sueño", "peor que tu normal", "en tu normal"),
    "z_tsb": ("balance de carga (TSB)", "más fatiga acumulada que tu normal",
              "en tu normal"),
    "z_hooper": ("bienestar reportado (Hooper)", "peor que tu normal", "en tu normal"),
}


# --- Bloque 1: el z-score móvil ----------------------------------------------
def _rolling_z(
    serie: pd.Series,
    ventana: int = VENTANA_Z,
    min_n: int = MIN_N_Z,
    invertir: bool = False,
) -> pd.Series:
    """z = (x − media móvil) / DE móvil, con el signo orientado a "menos = peor".

    - ``invertir=True`` para variables donde **más es peor** (FC en reposo,
      estrés, índice de Hooper): así un z negativo siempre significa "peor día".
    - **Nunca imputa.** Si falta el dato de un día, ese día queda NaN y además
      se excluye del cálculo de la media/DE de los días vecinos: la ventana
      cuenta observaciones reales, no rellenos.
    - Si en la ventana hay menos de ``min_n`` observaciones válidas, el z es NaN
      (no hay línea base personal todavía; preferimos el hueco al invento).
    - Si la DE es prácticamente cero (variable congelada), el z también es NaN:
      dividir por ~0 produciría z gigantes sin significado.

    La serie debe venir indexada en un calendario diario continuo para que
    "ventana" signifique días y no "filas con dato".
    """
    s = pd.to_numeric(serie, errors="coerce").astype(float)
    rolling = s.rolling(ventana, min_periods=min_n)
    media = rolling.mean()
    de = rolling.std(ddof=1)
    z = (s - media) / de.where(de > 1e-9)
    z = z.replace([np.inf, -np.inf], np.nan)
    return -z if invertir else z


# --- Bloque 2: lectura de las fuentes ----------------------------------------
def _leer_hooper(con) -> pd.DataFrame:
    """Índice de Hooper diario desde wellness_log (D-018), si es que existe.

    Otro módulo es el dueño del registro subjetivo; aquí se lee de forma
    defensiva: si las columnas no existen todavía (base antigua) o no hay filas
    completas, el dominio subjetivo simplemente queda ausente — que es distinto
    de valer cero.
    """
    vacio = pd.DataFrame(columns=["date_local", "hooper"])
    try:
        df = con.execute(
            """SELECT date_local,
                      AVG(hooper_sueno + hooper_fatiga + hooper_estres + hooper_doms)
                        AS hooper
               FROM wellness_log
               WHERE hooper_sueno IS NOT NULL AND hooper_fatiga IS NOT NULL
                 AND hooper_estres IS NOT NULL AND hooper_doms IS NOT NULL
                 AND date_local IS NOT NULL
               GROUP BY date_local ORDER BY date_local"""
        ).df()
    except Exception:  # columnas inexistentes o tabla en otro formato
        return vacio
    return df if not df.empty else vacio


def _fuentes(con) -> pd.DataFrame:
    """Une las fuentes crudas en un calendario diario continuo (sin imputar)."""
    dm = con.execute(
        """SELECT date_local,
                  COALESCE(resting_hr, hr_min) AS rhr,   -- resting_hr manda; hr_min es el respaldo
                  hrv_last_night, sleep_h, sleep_score
           FROM daily_metrics WHERE date_local IS NOT NULL ORDER BY date_local"""
    ).df()
    dl = con.execute(
        """SELECT date_local, tsb FROM daily_load
           WHERE date_local IS NOT NULL ORDER BY date_local"""
    ).df()
    hooper = _leer_hooper(con)

    partes = [d for d in (dm, dl, hooper) if not d.empty]
    if not partes:
        return pd.DataFrame()

    for d in partes:
        d["date_local"] = pd.to_datetime(d["date_local"])

    inicio = min(d["date_local"].min() for d in partes)
    fin = max(d["date_local"].max() for d in partes)
    idx = pd.date_range(inicio, fin, freq="D", name="date_local")

    out = pd.DataFrame(index=idx)
    for d in partes:
        # groupby por si alguna fuente trajera fechas repetidas
        out = out.join(d.groupby("date_local").mean(numeric_only=True))
    for col in ("rhr", "hrv_last_night", "sleep_h", "sleep_score", "tsb", "hooper"):
        if col not in out:
            out[col] = np.nan
    return out


# --- Bloque 3: construcción del índice ---------------------------------------
def build_readiness_frame(
    con, ventana: int = VENTANA_Z, min_n: int = MIN_N_Z
) -> pd.DataFrame:
    """Serie diaria de z por variable, z por dominio, índice y conteos.

    Devuelve además las columnas por variable (``z_rhr``, ``z_hrv``, …) porque
    ``estado_global`` las usa para explicar el porqué de cada dominio.
    """
    src = _fuentes(con)
    if src.empty:
        return pd.DataFrame()

    # HRV: puerta de validez + logaritmo natural (Plews 2013, distribución sesgada).
    hrv = src["hrv_last_night"].where(
        (src["hrv_last_night"] >= HRV_MIN_MS) & (src["hrv_last_night"] <= HRV_MAX_MS)
    )
    ln_hrv = np.log(hrv.where(hrv > 0))

    df = pd.DataFrame(index=src.index)
    df["z_rhr"] = _rolling_z(src["rhr"], ventana, min_n, invertir=True)  # más pulso = peor
    df["z_hrv"] = _rolling_z(ln_hrv, ventana, min_n)
    df["z_sleep_h"] = _rolling_z(src["sleep_h"], ventana, min_n)
    df["z_sleep_score"] = _rolling_z(src["sleep_score"], ventana, min_n)
    df["z_tsb"] = _rolling_z(src["tsb"], ventana, min_n)  # TSB alto = fresco = mejor
    df["z_hooper"] = _rolling_z(src["hooper"], ventana, min_n, invertir=True)  # más molestia = peor

    # Promedio DENTRO del dominio: dos formas de medir lo mismo pesan una sola vez.
    for dom, (_, cols) in DOMINIOS.items():
        df[dom] = df[list(cols)].mean(axis=1)  # NaN solo si ninguna variable tiene dato

    doms = list(DOMINIOS)
    df["n_dominios"] = df[doms].notna().sum(axis=1).astype(int)
    # Con un solo dominio no hay "compuesto" que valga: se deja vacío a propósito.
    df["indice"] = df[doms].mean(axis=1).where(df["n_dominios"] >= 2)
    df["dominios_alerta"] = (df[doms] <= UMBRAL_ALERTA).sum(axis=1).astype(int)
    return df


def rebuild_daily_readiness(con) -> pd.DataFrame:
    """Reconstruye daily_readiness completa (DELETE + INSERT: idempotente).

    Solo se guardan los días con al menos un dominio evaluable; los días sin
    ninguna señal no se escriben (una fila de NULLs no informa nada).
    """
    df = build_readiness_frame(con)
    cols = ["z_autonomico", "z_sueno", "z_carga", "z_subjetivo",
            "indice", "n_dominios", "dominios_alerta"]
    if df.empty:
        con.execute("DELETE FROM daily_readiness")
        return pd.DataFrame(columns=["date_local", *cols])

    out = df[df["n_dominios"] >= 1].copy()
    out = out[cols].round(3).reset_index()
    out["date_local"] = out["date_local"].dt.date

    con.execute("DELETE FROM daily_readiness")
    if not out.empty:
        con.register("dr", out)
        con.execute(
            f"""INSERT INTO daily_readiness (date_local, {', '.join(cols)})
                SELECT date_local, {', '.join(cols)} FROM dr"""
        )
        con.unregister("dr")
    return out


def refresh_readiness(db_path) -> dict:
    """Recalcula daily_readiness y devuelve un resumen del último día con datos."""
    con = connect(db_path)
    try:
        out = rebuild_daily_readiness(con)
    finally:
        con.close()

    if out.empty:
        return {"dias_serie": 0, "fecha": None, "indice": None,
                "n_dominios": 0, "dominios_alerta": 0}

    last = out.iloc[-1]
    indice = None if pd.isna(last["indice"]) else round(float(last["indice"]), 2)
    return {
        "dias_serie": int(len(out)),
        "fecha": last["date_local"],
        "indice": indice,
        "n_dominios": int(last["n_dominios"]),
        "dominios_alerta": int(last["dominios_alerta"]),
    }


# --- Bloque 4: lectura en lenguaje natural -----------------------------------
def _estado(z: float) -> str:
    """alerta / atencion / ok según la CONVENCIÓN de umbrales del proyecto."""
    if z <= UMBRAL_ALERTA:
        return "alerta"
    if z <= UMBRAL_ATENCION:
        return "atencion"
    return "ok"


def _razon(nombre: str, z: float, fila: pd.Series, cols: tuple[str, ...]) -> str:
    """Explica el dominio nombrando las variables que lo empujaron hacia abajo."""
    malas, presentes, faltantes = [], [], []
    for c in cols:
        etiqueta, frase_mal, frase_bien = _VARIABLES[c]
        v = fila.get(c)
        if v is None or pd.isna(v):
            faltantes.append(etiqueta)
            continue
        presentes.append(etiqueta)
        if v <= UMBRAL_ATENCION:
            malas.append(f"{etiqueta} {frase_mal} ({v:+.1f} DE)")

    if malas:
        cuerpo = " y ".join(malas)
    elif presentes:
        cuerpo = f"{' y '.join(presentes)} dentro de tu rango habitual"
    else:
        cuerpo = "sin datos"
    texto = f"{nombre}: {cuerpo}. Promedio del dominio {z:+.1f} DE."
    if faltantes:
        texto += f" (sin dato de {', '.join(faltantes)})"
    return texto


def estado_global(db_path, ventana: int = VENTANA_Z, min_n: int = MIN_N_Z) -> dict:
    """Foto de hoy por dominios, con la razón de cada uno en lenguaje natural.

    Umbrales usados: **alerta** si z ≤ −1, **atención** si −1 < z ≤ −0.5.
    Ese corte de −1 DE es una **convención de este proyecto, no un punto de
    corte clínico validado** (Robertson 2017 documenta la falta de
    estandarización entre sistemas de monitoreo). Y contar banderas **no es un
    modelo de riesgo calibrado**: con ~6 variables aparecen falsas alarmas por
    puro azar (≈16% por variable y día bajo normalidad). Sirve para decidir
    conversar con el cuerpo, no para pronosticar una lesión.

    Devuelve::

        {"fecha", "dias_atras", "indice", "n_dominios" ,
         "dominios_evaluables", "dominios_alerta", "motivo", "resumen",
         "detalle": [{"dominio", "clave", "z", "estado", "razon"}, ...]}
    """
    con = connect(db_path)
    try:
        df = build_readiness_frame(con, ventana, min_n)
    finally:
        con.close()

    vacio = {
        "fecha": None, "dias_atras": None, "indice": None, "n_dominios": 0,
        "dominios_evaluables": 0, "dominios_alerta": 0,
        "motivo": "Todavía no hay historia suficiente para una línea base personal "
                  f"(se necesitan {min_n} días con dato en una ventana de {ventana}).",
        "resumen": "Sin datos suficientes para evaluar disposición.",
        "detalle": [],
    }
    if df.empty:
        return vacio

    con_dato = df[df["n_dominios"] >= 1]
    if con_dato.empty:
        return vacio

    fila = con_dato.iloc[-1]
    fecha = con_dato.index[-1].date()

    detalle = []
    for clave, (nombre, cols) in DOMINIOS.items():
        z = fila[clave]
        if pd.isna(z):
            continue
        z = float(z)
        detalle.append({
            "dominio": nombre,
            "clave": clave,
            "z": round(z, 2),
            "estado": _estado(z),
            "razon": _razon(nombre, z, fila, cols),
        })
    detalle.sort(key=lambda d: d["z"])  # lo más preocupante primero

    n_dom = int(fila["n_dominios"])
    n_alerta = int(fila["dominios_alerta"])
    indice = None if pd.isna(fila["indice"]) else round(float(fila["indice"]), 2)

    motivo = None
    if indice is None:
        evaluables = ", ".join(d["dominio"].lower() for d in detalle) or "ninguno"
        motivo = (f"Solo {n_dom} dominio evaluable ({evaluables}): con menos de 2 "
                  "no se calcula un índice compuesto — un promedio de una sola "
                  "cosa no es un compuesto.")

    if n_alerta >= 2:
        resumen = (f"{n_alerta} de {n_dom} dominios bajo tu normal: patrón que "
                   "conviene mirar, sobre todo si se repite mañana.")
    elif n_alerta == 1:
        peor = detalle[0]["dominio"].lower()
        resumen = (f"Un dominio bajo tu normal ({peor}). Una bandera suelta puede "
                   "ser ruido; lo que importa es si persiste.")
    elif any(d["estado"] == "atencion" for d in detalle):
        resumen = "Todo dentro de rango, con algún dominio rozando el borde bajo."
    else:
        resumen = f"Los {n_dom} dominios evaluables están dentro de tu rango habitual."

    return {
        "fecha": fecha,
        "dias_atras": (_dt.date.today() - fecha).days,
        "indice": indice,
        "n_dominios": n_dom,
        "dominios_evaluables": n_dom,
        "dominios_alerta": n_alerta,
        "motivo": motivo,
        "resumen": resumen,
        "detalle": detalle,
    }
