"""Registro subjetivo ampliado y disposición pre-partido (D-015, D-018).

El FR255 se lleva en la muñeca: mide MUY bien lo cardiovascular (FC → TRIMP) y
es CIEGO a la carga mecánica del fútbol (aceleraciones, frenadas, cambios de
dirección) — que es justamente la que rompe isquios y aductores. Por eso lo
subjetivo no es un adorno: es el único canal disponible para estimar la carga
neuromuscular con este hardware.

Cuatro instrumentos, todos publicados (D-016: aquí no se inventa nada):

1. **dRPE (RPE diferenciado)** — se separa el esfuerzo percibido en
   *piernas* (mecánico/neuromuscular) y *respiración* (cardiorrespiratorio).
   Carga = RPE × minutos (sRPE de Foster) calculada por separado para cada uno.
   - Foster et al. (2001), *A new approach to monitoring exercise training*,
     J Strength Cond Res 15(1):109-115 — sRPE.
   - Los Arcos et al. (2014), *Rating of Muscular and Respiratory Perceived
     Exertion in Professional Soccer Players*, J Strength Cond Res
     28(11):3280-3288 — tras PARTIDO el RPE muscular supera al respiratorio
     (7.4 vs 6.4): un diferencial positivo de ~1 punto es lo ESPERABLE en
     fútbol, no una anomalía.
   - McLaren et al. (2017), *The relationships between internal and external
     measures of training load…*, JSAMS 20(3):290-295 — el dRPE se relaciona
     con dimensiones de carga distintas.
   **Jerarquía decidida de antemano (para no elegir a posteriori la métrica que
   nos conviene): sRPE-piernas manda para riesgo de lesión muscular; TRIMP
   manda para condición aeróbica.** Se conserva el `rpe` global para no romper
   el histórico previo a D-018.

2. **Hooper** — 4 ítems matinales 1-7 (calidad de sueño, fatiga, estrés, dolor
   muscular). ⚠️ ESCALA INVERTIDA: **7 = PEOR**, 1 = mejor. Es la fuente de
   error de registro más común de este cuestionario.
   - Hooper et al. (1995), *Markers for monitoring overtraining and recovery*,
     Med Sci Sports Exerc 27(1):106-112.
   - Duignan et al. (2020), *Single-Item Self-Report Measures of Team-Sport
     Athlete Wellbeing…*, J Athl Train 55(9):944-953 — **el sumatorio de los 4
     ítems NO tiene propiedades de medición aceptables**: por eso aquí NO existe
     un "índice Hooper". Se trabaja ítem por ítem, con z-score contra la línea
     base móvil individual, y se decide por CONTEO de ítems en rojo.
   - Saw, Main & Gastin (2016), BJSM 50(5):281-291 — las medidas subjetivas
     responden a la carga con más sensibilidad que muchas objetivas.
   - Referencia del uso de desviaciones estándar individuales como unidad de
     cambio: Hopkins (2000), Sports Med 30(1):1-15. **Limitación:** los cortes
     concretos (1.0 DE = ámbar, 1.5 DE = rojo) son convención de monitoreo, no
     puntos de corte validados; por eso siempre se muestra el valor crudo al
     lado del z.

3. **OSTRC-H2 semanal CONDICIONAL** — 4 preguntas de recuerdo de 7 días, pero
   SOLO para las zonas cuya molestia media semanal fue ≥3/10. Contestar el
   cuestionario completo para las 7 zonas serían 28 preguntas por semana:
   abandono garantizado.
   - Clarsen, Myklebust & Bahr (2013), BJSM 47(8):495-502 (OSTRC-O).
   - Clarsen et al. (2020), BJSM — revisión OSTRC-H2.
   - **Limitación (Franke et al., 2021):** el cambio mínimo DETECTABLE del
     severity score a nivel individual es ~35 puntos, MAYOR que el cambio
     mínimo importante (~18.5). En una sola persona solo son fiables los saltos
     GRANDES: moverse 10-20 puntos es ruido, no mejoría ni empeoramiento.

4. **Adherencia como métrica de primera clase** — un cuestionario perfecto que
   no se contesta vale cero. `wellness_log` arrancó con 0 filas, así que el
   criterio de diseño es brutal: **<30 s o se abandona**. Por eso el formulario
   cronometra (`segundos_registro`) y aquí se mide el cumplimiento.
   - Saw, Main & Gastin (2015), *Monitoring athletes through self-report:
     factors influencing implementation success…*, J Sports Sci Med 14(1):137-146.

Y la síntesis operativa: `match_readiness()` — el semáforo "¿Puedo jugar hoy?"
con 4 factores (carga, recuperación, molestias, estado subjetivo), más el
contexto de McLean et al. (2010), IJSPP 5(3):367-383: tras un partido de fútbol
la fatiga perceptual y neuromuscular sigue deprimida hasta ~48-72 h. Eso es
FISIOLOGÍA ESPERABLE, no una alarma — se muestra como contexto.

NO es consejo médico: el sistema ve números, no tejidos. El dolor manda.
"""
from __future__ import annotations

import datetime as _dt

import numpy as np
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

# --- dRPE: dos preguntas, dos dimensiones distintas de la misma sesión -------
RPE_LEGS_TEXTO = "Piernas (cuánto te pesaron: impactos, frenadas, cambios de dirección)"
RPE_BREATH_TEXTO = "Respiración (cuánto te faltó el aire / te latió el corazón)"

# ---------------------------------------------------------------------------
# Hooper 1995 — OJO: 1 = lo mejor, 7 = lo PEOR. Escala invertida a propósito.
# ---------------------------------------------------------------------------
HOOPER_ITEMS = {
    "hooper_sueno": "Calidad del sueño",
    "hooper_fatiga": "Fatiga",
    "hooper_estres": "Estrés",
    "hooper_doms": "Dolor muscular",
}

HOOPER_ESCALA = {
    "hooper_sueno": "1 muy buena · 4 normal · 7 muy mala",
    "hooper_fatiga": "1 muy fresco · 4 normal · 7 agotado",
    "hooper_estres": "1 muy relajado · 4 normal · 7 muy estresado",
    "hooper_doms": "1 sin dolor · 4 normal · 7 muy dolorido",
}

HOOPER_AVISO_INVERSION = (
    "⚠️ En Hooper el 7 es SIEMPRE lo peor (peor sueño, más fatiga, más estrés, "
    "más dolor). Es al revés que las notas del colegio: aquí subir es mala noticia."
)

# Ventana de la línea base individual y mínimo de observaciones para confiar.
_VENTANA_BASE_DIAS = 30
_MIN_OBS_BASE = 14
# Cortes en desviaciones estándar personales (convención, ver docstring).
_Z_AMBAR, _Z_ROJO = 1.0, 1.5

# ---------------------------------------------------------------------------
# OSTRC-H2 (Clarsen 2013/2020) — puntuación oficial, no se toca.
# ---------------------------------------------------------------------------
OSTRC_PREGUNTAS = [
    {
        "clave": "q1",
        "texto": "En los últimos 7 días, ¿pudiste participar normalmente por esta zona?",
        "opciones": [
            ("Participación completa, sin molestias", 0),
            ("Participación completa, pero con molestias", 8),
            ("Participación reducida por la molestia", 17),
            ("No pude participar por la molestia", 25),
        ],
    },
    {
        "clave": "q2",
        "texto": "¿Cuánto redujiste tu volumen de entrenamiento/juego por esta zona?",
        "opciones": [
            ("Nada", 0),
            ("Un poco", 6),
            ("Moderadamente", 13),
            ("Bastante", 19),
            ("No pude entrenar ni jugar", 25),
        ],
    },
    {
        "clave": "q3",
        "texto": "¿Cuánto afectó esta zona a tu rendimiento?",
        "opciones": [
            ("Nada", 0),
            ("Un poco", 6),
            ("Moderadamente", 13),
            ("Bastante", 19),
            ("No pude entrenar ni jugar", 25),
        ],
    },
    {
        "clave": "q4",
        "texto": "¿Cuánta molestia o dolor sentiste en esta zona?",
        "opciones": [
            ("Ninguna", 0),
            ("Leve", 8),
            ("Moderada", 17),
            ("Severa", 25),
        ],
    },
]

OSTRC_VALORES = {q["clave"]: [v for _, v in q["opciones"]] for q in OSTRC_PREGUNTAS}

# Umbral de molestia media semanal que dispara el cuestionario para una zona.
OSTRC_UMBRAL_ZONA = 3.0
# "Moderada o peor" en Q2/Q3 = problema sustancial (Clarsen 2013).
_OSTRC_SUSTANCIAL = 13

OSTRC_LIMITACION = (
    "Franke et al. (2021): a nivel individual el cambio mínimo detectable del "
    "severity es ~35 puntos (el cambio mínimo importante es ~18.5). Traducción: "
    "moverse 10-20 puntos de una semana a otra es RUIDO. Solo los saltos grandes "
    "significan algo cuando el dato es de una sola persona."
)


# ===========================================================================
# Utilidades internas
# ===========================================================================
def _entero_en_rango(nombre: str, valor, lo: int, hi: int):
    """None se respeta como 'no registrado'. Fuera de rango = error explícito."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return None
    v = int(valor)
    if not lo <= v <= hi:
        raise ValueError(f"{nombre} debe estar entre {lo} y {hi} (recibido {v})")
    return v


def _zona_clave(zona: str) -> str:
    """Acepta la clave técnica ('d_isquios') o el nombre visible ('Isquiotibiales')."""
    if zona in ZONAS:
        return zona
    for clave, nombre in ZONAS.items():
        if nombre.lower() == str(zona).strip().lower():
            return clave
    raise ValueError(f"zona desconocida: {zona!r}")


def _lunes(fecha: _dt.date) -> _dt.date:
    """Inicio de la semana ISO (lunes) de esa fecha."""
    return fecha - _dt.timedelta(days=fecha.weekday())


# ===========================================================================
# 1. Registro de sesión (dRPE) y registro matinal (Hooper)
# ===========================================================================
def save_log(db_path, *, date_local, activity_id, rpe=None, duration_min=None,
             dolores: dict | None = None, nota: str = "",
             rpe_legs=None, rpe_breath=None, hooper: dict | None = None,
             segundos_registro=None) -> None:
    """Guarda (o reemplaza) el registro de una sesión o del día.

    Compatible hacia atrás: los parámetros de D-018 (`rpe_legs`, `rpe_breath`,
    `hooper`, `segundos_registro`) son opcionales y por defecto None.

    `dolores` es un dict {clave_zona: 0-10}. Una zona AUSENTE del dict se guarda
    como NULL, no como 0: "no lo registré" y "no me duele" son cosas distintas
    y mezclarlas contamina las medias que disparan el OSTRC.
    """
    dolores = dolores or {}
    hooper = hooper or {}
    log_id = f"a:{activity_id}" if activity_id else f"d:{date_local}"

    vals_dolor = [_entero_en_rango(z, dolores.get(z), 0, 10) for z in ZONAS]
    vals_hooper = [_entero_en_rango(h, hooper.get(h), 1, 7) for h in HOOPER_ITEMS]

    con = connect(db_path)
    try:
        con.execute("DELETE FROM wellness_log WHERE log_id = ?", [log_id])
        con.execute(
            """INSERT INTO wellness_log
               (log_id, date_local, activity_id, rpe, duration_min,
                d_isquios, d_cuadriceps, d_gemelos, d_aductores,
                d_rodilla, d_tobillo, d_espalda, nota,
                rpe_legs, rpe_breath,
                hooper_sueno, hooper_fatiga, hooper_estres, hooper_doms,
                segundos_registro)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                log_id, date_local, activity_id,
                _entero_en_rango("rpe", rpe, 0, 10),
                int(duration_min) if duration_min else None,
                *vals_dolor,
                (nota or "").strip() or None,
                _entero_en_rango("rpe_legs", rpe_legs, 0, 10),
                _entero_en_rango("rpe_breath", rpe_breath, 0, 10),
                *vals_hooper,
                float(segundos_registro) if segundos_registro is not None else None,
            ],
        )
    finally:
        con.close()


def save_hooper(db_path, *, date_local, hooper: dict,
                segundos_registro=None) -> None:
    """Registro matinal Hooper del día (log_id 'h:<fecha>', upsert).

    Va en su propia fila para que el chequeo de la mañana y el registro de la
    sesión de la tarde no se pisen entre sí. Recuerda: 7 = PEOR.
    """
    log_id = f"h:{date_local}"
    vals = [_entero_en_rango(h, hooper.get(h), 1, 7) for h in HOOPER_ITEMS]
    con = connect(db_path)
    try:
        con.execute("DELETE FROM wellness_log WHERE log_id = ?", [log_id])
        con.execute(
            """INSERT INTO wellness_log
               (log_id, date_local, hooper_sueno, hooper_fatiga,
                hooper_estres, hooper_doms, segundos_registro)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [log_id, date_local, *vals,
             float(segundos_registro) if segundos_registro is not None else None],
        )
    finally:
        con.close()


def fetch_logs(db_path, limit: int = 20) -> pd.DataFrame:
    """Últimos registros con sus cargas sRPE derivadas y la actividad asociada.

    Columnas nuevas (D-018): rpe_legs/rpe_breath, srpe_legs/srpe_breath y
    `drpe_diff` = piernas − respiración (positivo = pesaron más las piernas,
    lo típico tras partido según Los Arcos 2014).
    """
    con = connect(db_path)
    try:
        return con.execute(
            """SELECT w.date_local, a.sport, w.rpe, w.duration_min,
                      w.rpe * COALESCE(w.duration_min, 0) AS srpe,
                      w.rpe_legs, w.rpe_breath,
                      w.rpe_legs   * w.duration_min AS srpe_legs,
                      w.rpe_breath * w.duration_min AS srpe_breath,
                      w.rpe_legs - w.rpe_breath     AS drpe_diff,
                      w.d_isquios, w.d_cuadriceps, w.d_gemelos, w.d_aductores,
                      w.d_rodilla, w.d_tobillo, w.d_espalda,
                      w.hooper_sueno, w.hooper_fatiga, w.hooper_estres,
                      w.hooper_doms, w.segundos_registro, w.nota
               FROM wellness_log w
               LEFT JOIN activities a USING (activity_id)
               ORDER BY w.date_local DESC, w.created_at DESC
               LIMIT ?""",
            [limit],
        ).df()
    finally:
        con.close()


def drpe_series(db_path, dias: int = 90) -> pd.DataFrame:
    """Serie de dRPE para graficar: sRPE-piernas vs sRPE-respiración por sesión.

    La divergencia entre ambas es la información nueva: si el sRPE-piernas
    sube mientras el respiratorio y el TRIMP se mantienen, la carga que creció
    es MECÁNICA — la que el reloj de muñeca no ve y la que rompe isquios.
    """
    con = connect(db_path)
    try:
        df = con.execute(
            """SELECT w.date_local, a.sport, w.duration_min,
                      w.rpe, w.rpe_legs, w.rpe_breath,
                      w.rpe_legs   * w.duration_min AS srpe_legs,
                      w.rpe_breath * w.duration_min AS srpe_breath,
                      w.rpe_legs - w.rpe_breath     AS drpe_diff,
                      a.trimp
               FROM wellness_log w
               LEFT JOIN activities a USING (activity_id)
               WHERE w.date_local >= current_date - INTERVAL (?) DAY
                 AND (w.rpe_legs IS NOT NULL OR w.rpe_breath IS NOT NULL)
               ORDER BY w.date_local""",
            [dias],
        ).df()
    finally:
        con.close()
    return df


# ===========================================================================
# 2. Hooper: z-score POR ÍTEM contra la línea base móvil individual
# ===========================================================================
def hooper_zscores(db_path, dias: int = 180) -> pd.DataFrame:
    """Serie diaria de los 4 ítems con su z personal (columnas `<item>_z`).

    Cómo se lee el z: "cuántas desviaciones estándar TUYAS te alejaste hoy de tu
    propia normalidad de las últimas 4 semanas". La base excluye el día de hoy
    (`shift(1)`) para que el valor de hoy no se auto-diluya. Con la escala
    invertida de Hooper, **z positivo = peor que tu normal**.

    Devuelve calendario diario completo (días sin registro = NaN, jamás 0).
    """
    con = connect(db_path)
    try:
        df = con.execute(
            """SELECT date_local,
                      AVG(hooper_sueno)  AS hooper_sueno,
                      AVG(hooper_fatiga) AS hooper_fatiga,
                      AVG(hooper_estres) AS hooper_estres,
                      AVG(hooper_doms)   AS hooper_doms
               FROM wellness_log
               WHERE date_local IS NOT NULL
                 AND (hooper_sueno IS NOT NULL OR hooper_fatiga IS NOT NULL
                      OR hooper_estres IS NOT NULL OR hooper_doms IS NOT NULL)
               GROUP BY date_local ORDER BY date_local"""
        ).df()
    finally:
        con.close()

    cols = list(HOOPER_ITEMS)
    if df.empty:
        return pd.DataFrame(columns=["date_local", *cols, *(f"{c}_z" for c in cols)])

    df["date_local"] = pd.to_datetime(df["date_local"])
    fin = max(df["date_local"].max(), pd.Timestamp.today().normalize())
    idx = pd.date_range(df["date_local"].min(), fin, freq="D")
    s = df.set_index("date_local").reindex(idx)

    for c in cols:
        serie = pd.to_numeric(s[c], errors="coerce")
        previos = serie.shift(1)
        media = previos.rolling(_VENTANA_BASE_DIAS, min_periods=_MIN_OBS_BASE).mean()
        de = previos.rolling(_VENTANA_BASE_DIAS, min_periods=_MIN_OBS_BASE).std()
        # DE cero (contestó siempre lo mismo) → el z no significa nada.
        de = de.where(de > 1e-9)
        s[f"{c}_z"] = (serie - media) / de
        s[f"{c}_n"] = previos.rolling(_VENTANA_BASE_DIAS, min_periods=1).count()

    out = s.reset_index().rename(columns={"index": "date_local"})
    out["date_local"] = out["date_local"].dt.date
    return out.tail(dias).reset_index(drop=True)


def _estado_item(z) -> str:
    if z is None or pd.isna(z):
        return "sin_base"
    if z >= _Z_ROJO:
        return "alto"
    if z >= _Z_AMBAR:
        return "ojo"
    return "ok"


def hooper_status(db_path, max_antiguedad_dias: int = 2) -> dict:
    """Estado subjetivo del último registro Hooper, ítem por ítem.

    Deliberadamente NO devuelve un índice compuesto (Duignan 2020: el sumatorio
    no tiene propiedades de medición aceptables). La decisión se toma por
    CONTEO de ítems en rojo:
      · 2 o más ítems en rojo (z ≥ 1.5) → precaución (estado 'alto')
      · 1 ítem en rojo, o 2 en ámbar (z ≥ 1.0) → 'ojo'
      · resto → 'ok'
    Mientras no haya al menos 14 registros en las últimas 4 semanas no hay z:
    se devuelve 'sin_datos' y se informa cuánto falta para tener línea base.
    """
    vacio = {
        "estado": "sin_datos", "razon": "sin registro matinal reciente",
        "fecha": None, "antiguedad_dias": None, "items": [],
        "n_rojos": 0, "n_ambar": 0, "base_lista": False, "obs_base": 0,
    }
    z = hooper_zscores(db_path)
    cols = list(HOOPER_ITEMS)
    if z.empty:
        return vacio
    con_dato = z.dropna(subset=cols, how="all")
    if con_dato.empty:
        return vacio

    fila = con_dato.iloc[-1]
    fecha = fila["date_local"]
    antig = (_dt.date.today() - fecha).days
    if antig > max_antiguedad_dias:
        vacio["fecha"] = fecha
        vacio["antiguedad_dias"] = antig
        vacio["razon"] = f"último registro subjetivo hace {antig} días"
        return vacio

    items, obs = [], 0
    for c in cols:
        crudo = fila[c]
        zi = fila.get(f"{c}_z")
        obs = max(obs, int(fila.get(f"{c}_n") or 0))
        items.append({
            "clave": c,
            "nombre": HOOPER_ITEMS[c],
            "crudo": None if pd.isna(crudo) else int(round(float(crudo))),
            "z": None if pd.isna(zi) else round(float(zi), 2),
            "estado": _estado_item(zi),
            "escala": HOOPER_ESCALA[c],
        })

    rojos = [i for i in items if i["estado"] == "alto"]
    ambar = [i for i in items if i["estado"] == "ojo"]
    base_lista = any(i["z"] is not None for i in items)

    if not base_lista:
        faltan = max(_MIN_OBS_BASE - obs, 1)
        return {
            "estado": "sin_datos",
            "razon": (f"construyendo tu línea base: faltan ~{faltan} registros "
                      "para poder comparar contra tu normalidad"),
            "fecha": fecha, "antiguedad_dias": antig, "items": items,
            "n_rojos": 0, "n_ambar": 0, "base_lista": False, "obs_base": obs,
        }

    if len(rojos) >= 2:
        estado = "alto"
        razon = " y ".join(f"{i['nombre'].lower()} ({i['crudo']}/7)" for i in rojos[:2])
        razon = f"{len(rojos)} ítems muy sobre tu normal: {razon}"
    elif rojos:
        estado = "ojo"
        razon = f"{rojos[0]['nombre'].lower()} {rojos[0]['crudo']}/7, sobre tu normal (z {rojos[0]['z']:+.1f})"
    elif len(ambar) >= 2:
        estado = "ojo"
        razon = "dos ítems algo peores que tu normal: " + " y ".join(
            i["nombre"].lower() for i in ambar[:2])
    else:
        estado = "ok"
        razon = "sueño, fatiga, estrés y dolor dentro de tu normalidad"

    return {
        "estado": estado, "razon": razon, "fecha": fecha,
        "antiguedad_dias": antig, "items": items,
        "n_rojos": len(rojos), "n_ambar": len(ambar),
        "base_lista": True, "obs_base": obs,
    }


# ===========================================================================
# 3. Molestias por zona y OSTRC-H2 condicional
# ===========================================================================
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


def zonas_a_preguntar(db_path, week_start=None,
                      incluir_respondidas: bool = False) -> list[dict]:
    """Zonas que merecen el OSTRC-H2 esta semana (media de molestia ≥ 3/10).

    La clave del diseño: el OSTRC completo son 4 preguntas × 7 zonas = 28 por
    semana. Nadie sostiene eso. Aplicándolo solo a las zonas que realmente
    molestaron quedan típicamente 0-2 zonas → 0-8 preguntas, ~60-90 s.

    Los NULL (zona no registrada) NO entran en la media: solo se promedian los
    días en que Jorge efectivamente respondió por esa zona.
    """
    week_start = _lunes(week_start or _dt.date.today())
    week_end = week_start + _dt.timedelta(days=6)

    con = connect(db_path)
    try:
        cols = ", ".join(
            f"AVG({c}) AS m_{c}, MAX({c}) AS x_{c}, COUNT({c}) AS n_{c}" for c in ZONAS
        )
        row = con.execute(
            f"""SELECT {cols} FROM wellness_log
                WHERE date_local BETWEEN ? AND ?""",
            [week_start, week_end],
        ).fetchone()
        ya = {
            r[0] for r in con.execute(
                "SELECT zone FROM ostrc_log WHERE week_start = ?", [week_start]
            ).fetchall()
        }
    finally:
        con.close()

    out = []
    for i, (clave, nombre) in enumerate(ZONAS.items()):
        media, maximo, n = row[i * 3], row[i * 3 + 1], row[i * 3 + 2]
        if not n or media is None or float(media) < OSTRC_UMBRAL_ZONA:
            continue
        if not incluir_respondidas and clave in ya:
            continue
        out.append({
            "zona": clave,
            "nombre": nombre,
            "media": round(float(media), 1),
            "maximo": int(maximo),
            "n_registros": int(n),
            "week_start": week_start,
            "ya_respondida": clave in ya,
        })
    out.sort(key=lambda z: -z["media"])
    return out


def ostrc_severity(q1: int, q2: int, q3: int, q4: int) -> int:
    """Severity 0-100 = suma de las 4 respuestas (Clarsen 2013). Valida opciones."""
    vals = {"q1": q1, "q2": q2, "q3": q3, "q4": q4}
    for clave, v in vals.items():
        if int(v) not in OSTRC_VALORES[clave]:
            raise ValueError(
                f"{clave} debe ser uno de {OSTRC_VALORES[clave]} (recibido {v})")
    return int(q1) + int(q2) + int(q3) + int(q4)


def ostrc_clasificacion(q1: int, q2: int, q3: int, q4: int) -> dict:
    """Definiciones de Clarsen: problema de salud y problema SUSTANCIAL.

    - problema de salud   → severity > 0 (cualquier respuesta distinta de 0).
    - problema sustancial → respuesta moderada o peor (≥13) en Q2 (volumen) o
      Q3 (rendimiento). Es la definición clásica de Clarsen 2013; la revisión
      de 2020 admite además considerar Q1 ≥17, pero aquí se mantiene la
      original para no inflar el conteo.
    """
    sev = ostrc_severity(q1, q2, q3, q4)
    return {
        "severity": sev,
        "problema_salud": sev > 0,
        "sustancial": int(q2) >= _OSTRC_SUSTANCIAL or int(q3) >= _OSTRC_SUSTANCIAL,
    }


def save_ostrc(db_path, *, week_start, zone, q1, q2, q3, q4) -> dict:
    """Guarda (upsert) el OSTRC-H2 de una zona para una semana. Devuelve la clasificación."""
    week_start = _lunes(week_start if isinstance(week_start, _dt.date)
                        else pd.Timestamp(week_start).date())
    clave = _zona_clave(zone)
    clas = ostrc_clasificacion(q1, q2, q3, q4)

    con = connect(db_path)
    try:
        con.execute(
            "DELETE FROM ostrc_log WHERE week_start = ? AND zone = ?",
            [week_start, clave],
        )
        con.execute(
            """INSERT INTO ostrc_log (week_start, zone, q1, q2, q3, q4, severity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [week_start, clave, int(q1), int(q2), int(q3), int(q4), clas["severity"]],
        )
    finally:
        con.close()
    return clas


def fetch_ostrc(db_path, semanas: int = 12) -> pd.DataFrame:
    """Historial OSTRC con nombre de zona y las banderas de Clarsen."""
    con = connect(db_path)
    try:
        df = con.execute(
            """SELECT week_start, zone, q1, q2, q3, q4, severity
               FROM ostrc_log
               WHERE week_start >= current_date - INTERVAL (?) DAY
               ORDER BY week_start DESC, severity DESC""",
            [semanas * 7],
        ).df()
    finally:
        con.close()
    if df.empty:
        df["nombre"] = pd.Series(dtype="object")
        df["problema_salud"] = pd.Series(dtype="bool")
        df["sustancial"] = pd.Series(dtype="bool")
        return df
    df["nombre"] = df["zone"].map(ZONAS).fillna(df["zone"])
    df["problema_salud"] = df["severity"] > 0
    df["sustancial"] = (df["q2"] >= _OSTRC_SUSTANCIAL) | (df["q3"] >= _OSTRC_SUSTANCIAL)
    return df


# ===========================================================================
# 4. Adherencia — sin registro, todo lo anterior vale cero
# ===========================================================================
def adherencia(db_path, dias: int = 30) -> dict:
    """Cumplimiento del registro subjetivo (Saw et al. 2015).

    - pct_dias_registrados: % de días de la ventana con al menos un registro.
    - mediana_segundos: cuánto tarda de verdad el formulario (solo días
      cronometrados; los NULL no cuentan como 0 — no registrado ≠ instantáneo).
    - racha_actual: días consecutivos con registro. Se cuenta hacia atrás desde
      hoy, y si hoy todavía no hay registro se arranca desde ayer (el día no
      terminó: la racha no se rompe hasta que pasa).
    """
    hoy = _dt.date.today()
    desde = hoy - _dt.timedelta(days=dias - 1)
    con = connect(db_path)
    try:
        dias_reg = {
            r[0] for r in con.execute(
                "SELECT DISTINCT date_local FROM wellness_log WHERE date_local IS NOT NULL"
            ).fetchall()
        }
        med = con.execute(
            """SELECT median(segundos_registro), COUNT(segundos_registro)
               FROM wellness_log
               WHERE date_local BETWEEN ? AND ? AND segundos_registro IS NOT NULL""",
            [desde, hoy],
        ).fetchone()
    finally:
        con.close()

    en_ventana = sum(
        1 for d in dias_reg if isinstance(d, _dt.date) and desde <= d <= hoy
    )

    inicio = hoy if hoy in dias_reg else hoy - _dt.timedelta(days=1)
    racha, cursor = 0, inicio
    while cursor in dias_reg:
        racha += 1
        cursor -= _dt.timedelta(days=1)

    return {
        "dias_ventana": dias,
        "dias_registrados": en_ventana,
        "pct_dias_registrados": round(100.0 * en_ventana / dias, 1) if dias else 0.0,
        "mediana_segundos": round(float(med[0]), 1) if med and med[0] is not None else None,
        "n_cronometrados": int(med[1]) if med and med[1] is not None else 0,
        "racha_actual": racha,
    }


# ===========================================================================
# 5. Tarjeta "¿Puedo jugar hoy?"
# ===========================================================================
def _factor(estado: str, razon: str) -> dict:
    # estado: ok | ojo | alto | sin_datos  (sin_datos NO pinta el semáforo global)
    return {"estado": estado, "razon": razon}


def match_readiness(db_path) -> dict:
    """Semáforo '¿Puedo jugar hoy?' — carga, recuperación, molestias y subjetivo.

    El cuarto factor (Hooper) aparece solo cuando hay registro reciente Y línea
    base suficiente; si no, se declara 'sin_datos' y NO contamina el semáforo
    global (mejor un factor honestamente vacío que un amarillo permanente).

    Contexto McLean et al. (2010): si el último partido fue hace <48 h, la
    fatiga percibida y neuromuscular está esperablemente deprimida. Se informa,
    no se penaliza.
    """
    con = connect(db_path)
    try:
        dl = con.execute(
            "SELECT acwr FROM daily_load ORDER BY date_local DESC LIMIT 1"
        ).fetchone()
        last_act = con.execute("SELECT MAX(date_local) FROM activities").fetchone()[0]
        last_match = con.execute(
            "SELECT MAX(start_time_utc) FROM activities WHERE sport = 'soccer'"
        ).fetchone()[0]
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

    # --- Factor 4: estado subjetivo (Hooper) ----------------------------------
    hs = hooper_status(db_path)
    subj = _factor(hs["estado"], hs["razon"])

    # --- Contexto McLean 2010: ventana post-partido ---------------------------
    contexto: list[str] = []
    horas_partido = None
    if last_match is not None:
        ts = pd.Timestamp(last_match)
        ahora = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        horas_partido = (ahora - ts.to_pydatetime()).total_seconds() / 3600.0
        if 0 <= horas_partido < 48:
            contexto.append(
                f"Jugaste hace {horas_partido:.0f} h: hasta ~48-72 h después de un "
                "partido la fatiga percibida y la potencia neuromuscular siguen "
                "bajas (McLean 2010). Es lo esperable, no una anomalía."
            )
            if subj["estado"] in ("ojo", "alto"):
                subj["razon"] += f" · esperable a {horas_partido:.0f} h del partido"

    factores = {"Carga": carga, "Recuperación": recup, "Molestias": mol,
                "Estado subjetivo": subj}
    estados = [f["estado"] for f in factores.values()]
    if "alto" in estados:
        overall = ("alto", "🔴 Alto riesgo hoy — modera minutos o descansa")
    elif "ojo" in estados:
        overall = ("ojo", "🟡 Jugable con cuidado — calienta largo y escucha al cuerpo")
    else:
        overall = ("ok", "🟢 Listo para jugar")
    return {
        "estado": overall[0],
        "titulo": overall[1],
        "factores": factores,
        "contexto": contexto,
        "horas_desde_partido": None if horas_partido is None else round(horas_partido, 1),
    }
