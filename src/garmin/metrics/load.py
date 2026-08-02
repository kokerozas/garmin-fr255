"""Métricas de carga de entrenamiento (D-006, D-007, D-017).

Qué hay aquí
------------
- TRIMP de Banister por sesión, integrado muestra a muestra sobre FC válida.
  Unifica la carga entre deportes (fútbol, running, etc.) porque solo usa FC.
- FCmax / FCreposo estimadas desde los propios datos (percentiles robustos),
  con override manual desde config/settings.yaml si el atleta los define.
- Serie diaria: ATL (EWMA 7d), CTL (EWMA 42d), TSB = CTL-ATL,
  y ACWR (promedio 7d / promedio 28d) con semáforo de riesgo.
- **Carga absoluta** (D-017): sumas móviles 7/14/21/28 d, percentil de la carga
  semanal dentro del propio año, cambio semana-a-semana con umbral individual,
  y monotonía / strain de Foster como serie diaria.
- `efficiency_index()`: función pura de metros por unidad de TRIMP.

Por qué se reencuadró la carga (el punto importante)
----------------------------------------------------
Entre 2019 y 2025 la literatura desmontó al ACWR como vehículo principal de
decisión. El golpe definitivo: Impellizzeri, Woodcock, Coutts, Fanchini,
McCall & Vigotsky (2021), *What Role Do Chronic Workloads Play in the Acute to
Chronic Workload Ratio? Time to Dismiss ACWR and Its Underlying Theory*,
Sports Medicine 51(3):581-592 — sustituyeron la carga crónica real por valores
ALEATORIOS y el ACWR siguió asociándose con lesión igual de bien. Si el
denominador puede ser ruido y el resultado no cambia, el ratio no está midiendo
lo que se creía. Antes ya se había mostrado que el acoplamiento matemático
(la carga aguda está DENTRO de la crónica) fabrica correlación espuria:
Impellizzeri, Tenan, Kempton, Novak & Coutts (2020), *Acute:Chronic Workload
Ratio: Conceptual Issues and Fundamental Pitfalls*, Int J Sports Physiol Perform
15(6):907-913; y Lolli, Batterham, Hawkins, Kelly, Gregson, Thorpe, Atkinson &
Drust (2019), *Mathematical coupling causes spurious correlation within the
conventional acute-to-chronic workload ratio calculations*, Br J Sports Med
53(15):921-922. La prueba de fuego clínica: Dalen-Lorentsen, Bjørneboe, Clarsen,
Vagle, Fagerland & Andersen (2021), *Does load management using the
acute:chronic workload ratio prevent health problems? A cluster randomised
trial of 482 elite youth footballers of both sexes*, Br J Sports Med — ECA con
482 futbolistas juveniles: CERO diferencia planificando con ACWR.

Conclusión operativa para este proyecto: el ACWR **se conserva** (está en el
dashboard, es cultura común y sigue siendo una señal de conversación, D-016),
pero deja de ser el protagonista. El protagonista pasa a ser la **carga
absoluta** y su **cambio**, que es lo que la evidencia sí sostiene:

- Rogalski, Dawson, Heasman & Gabbett (2013), *Training and game loads and
  injury risk in elite Australian footballers*, J Sci Med Sport 16(6):499-503 —
  la carga SEMANAL ACUMULADA absoluta y su incremento discriminan riesgo.
- Cross, Williams, Trewartha, Kemp & Stokes (2016), *The Influence of In-Season
  Training Loads on Injury Risk in Professional Rugby Union*, Int J Sports
  Physiol Perform 11(3):350-355 — los cambios de carga semanal de más de
  **2 desviaciones estándar** respecto de la variabilidad habitual del atleta
  elevan el riesgo. Aquí ese "2 DE" se calcula con la propia variabilidad de
  Jorge (ventana de 365 días), no con un umbral importado de otro deporte.
- Foster (1998), *Monitoring training in athletes with reference to overtraining
  syndrome*, Med Sci Sports Exerc 30(7):1164-1168 — monotonía = media/DE de la
  carga diaria de la semana; strain = carga semanal × monotonía. Semanas
  planas y altas (monotonía alta) preceden a enfermedad y sobrecarga.
- Akubat, Barrett & Abt (2014), *Integrating the internal and external training
  loads in soccer*, Int J Sports Physiol Perform 9(3):457-462 — índice de
  eficiencia = trabajo externo por unidad de carga interna.

Limitaciones declaradas
-----------------------
- El percentil de carga (`load_7d_pct`) es descriptivo: dice "esta semana está
  en el percentil X de tu propio año". NO es un umbral de riesgo publicado;
  su valor es hacer interpretable un número (412 TRIMP) sin importar umbrales.
- El "2 DE" de Cross 2016 se derivó en rugby profesional con sRPE. Aquí se
  aplica sobre TRIMP de FC y con la variabilidad individual — la lógica
  (cambio inusual PARA ESTE atleta) se respeta; la magnitud absoluta no es
  transferible.
- Foster 1998 define monotonía sobre la semana calendario; aquí se calcula como
  ventana móvil de 7 días para tener una serie diaria. Es la misma fórmula con
  resolución más fina.
- `efficiency_index` sustituye el iTRIMP del paper original de Akubat por el
  TRIMP de Banister ya implementado (**desviación declarada**): iTRIMP exige
  una curva lactato-FC individual de laboratorio que no existe aquí. El índice
  sirve para comparar sesiones de Jorge entre sí, no contra otros atletas.
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

# --- Parámetros de la carga absoluta (D-017) ---------------------------------
# Ventana de referencia personal: un año completo captura la estacionalidad del
# fútbol amateur (pretemporada, receso, parones por lesión o viaje).
VENTANA_REF_D = 365
# Mínimo de días con dato para que el percentil / la DE signifiquen algo. Con
# menos de ~4 meses de historia el "percentil de tu año" es una ilusión.
MIN_DIAS_REF = 120
# Guarda del denominador del cambio semanal: con semanas de carga casi cero el
# porcentaje explota (de 5 a 60 TRIMP es +1100 % y no significa nada).
MIN_CARGA_PREV = 50.0
# Umbrales de Cross 2016 expresados en DE de la propia distribución de cambios.
K_AMBAR, K_ROJO = 1.5, 2.0


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


# =============================================================================
# Carga absoluta: helpers puros (testeables sin base de datos)
# =============================================================================

def percentil_movil(
    serie: pd.Series,
    ventana: int = VENTANA_REF_D,
    min_periodos: int = MIN_DIAS_REF,
) -> pd.Series:
    """Percentil [0-1] de cada valor DENTRO de su propia ventana histórica.

    Traduce "412 TRIMP" a "percentil 0.88 de tu último año", que es
    interpretable sin importar ningún umbral de otro deporte ni otro atleta.
    Devuelve NaN hasta tener `min_periodos` días con dato: un percentil sobre
    tres semanas de historia sería una ilusión estadística.
    """
    return serie.rolling(ventana, min_periods=min_periodos).rank(pct=True)


def cambio_semanal(carga_7d: pd.Series, min_prev: float = MIN_CARGA_PREV) -> pd.Series:
    """Cambio relativo de la carga de 7 días contra los 7 días anteriores.

    Rogalski 2013 / Cross 2016: lo que discrimina riesgo no es el nivel de carga
    sino el SALTO. La guarda `min_prev` existe porque el porcentaje se vuelve
    absurdo con denominadores diminutos (de 4 a 50 TRIMP es +1150 %, y sin
    embargo 50 TRIMP es una sesión suave). Bajo esa guarda: NaN, no un número
    inventado.
    """
    prev = carga_7d.shift(7)
    with np.errstate(divide="ignore", invalid="ignore"):
        cambio = np.where(prev > min_prev, carga_7d / prev - 1.0, np.nan)
    return pd.Series(cambio, index=carga_7d.index, dtype="float64")


def clasificar_cambio(cambio: float | None, sd: float | None) -> str | None:
    """Semáforo del cambio semanal contra la variabilidad PROPIA del atleta.

    Cross et al. 2016 encontró el aumento de riesgo en cambios > 2 DE. Aquí la
    DE no se importa: es la de la distribución de cambios semanales de Jorge en
    su último año. Así, un atleta muy regular se alerta antes que uno errático,
    que es exactamente la individualización que pedía el paper.
    """
    if cambio is None or sd is None:
        return None
    if pd.isna(cambio) or pd.isna(sd) or sd <= 1e-9:
        return None
    mag = abs(float(cambio))
    if mag > K_ROJO * float(sd):
        return "rojo"
    if mag > K_AMBAR * float(sd):
        return "ambar"
    return None


def monotonia_strain(
    trimp_diario: pd.Series, ventana: int = 7
) -> tuple[pd.Series, pd.Series]:
    """Monotonía y strain de Foster (1998) como serie diaria móvil.

    monotonía = media(TRIMP de la ventana) / DE(TRIMP de la ventana)
    strain    = carga de la ventana (suma) × monotonía

    Monotonía alta = todos los días iguales; el cuerpo nunca tiene un día
    claramente fácil y el estrés se acumula. Foster sitúa la atención sobre 2.0.

    Cuidado con DE = 0: una semana de ceros (parón) o perfectamente plana daría
    infinito. Aquí devuelve NaN — no hay monotonía definida sin variación, y un
    infinito contaminaría cualquier gráfico o promedio posterior.
    """
    roll = trimp_diario.rolling(ventana, min_periods=ventana)
    media, de, suma = roll.mean(), roll.std(), roll.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        mono = np.where(de > 1e-9, media / de, np.nan)
    monotonia = pd.Series(mono, index=trimp_diario.index, dtype="float64")
    return monotonia, suma * monotonia


# --- Índice de eficiencia (Akubat 2014) --------------------------------------
# Criterios de validez: sin ellos el índice compara peras con manzanas.
EFF_MIN_HR_COVERAGE = 0.9   # con FC parcial el denominador está subestimado
EFF_MIN_DURACION_S = 1800.0  # <30 min: el calentamiento domina la sesión
EFF_METODO_VALIDO = "samples"  # 'session_avg' promedia y borra la variabilidad


def efficiency_index(
    distance_m: float | None,
    trimp: float | None,
    trimp_method: str | None = None,
    hr_coverage: float | None = None,
    duration_s: float | None = None,
    *,
    min_hr_coverage: float = EFF_MIN_HR_COVERAGE,
    min_duracion_s: float = EFF_MIN_DURACION_S,
) -> float | None:
    """Metros recorridos por unidad de TRIMP. None si la sesión no es comparable.

    Referencia: Akubat, Barrett & Abt (2014), *Integrating the internal and
    external training loads in soccer*, Int J Sports Physiol Perform 9(3):457-462.
    Idea: mismo trabajo externo con menos coste interno = mejor condición; el
    mismo trabajo con MÁS coste interno = fatiga acumulada, calor o enfermedad.

    **Desviación declarada (D-016):** el paper usa iTRIMP (TRIMP individualizado
    con la curva lactato-FC del atleta, medida en laboratorio). Aquí se usa el
    TRIMP de Banister ya implementado, porque esa curva no existe para Jorge.
    Consecuencia: el índice es válido para comparar sesiones de Jorge ENTRE SÍ
    a lo largo del tiempo, no para compararlo con valores publicados.

    Esta función es PURA a propósito: la escritura en `activity_external` la hace
    `garmin.metrics.external`, dueño de esa tabla. Aquí solo vive el criterio.

    Criterios de validez (si falla alguno → None, nunca un número dudoso):
      - `trimp_method == 'samples'`: el fallback `session_avg` aplana la
        intensidad y sesga el denominador.
      - `hr_coverage >= 0.9`: con huecos de FC el TRIMP queda subestimado y el
        índice sale artificialmente alto.
      - `duration_s >= 1800`: en sesiones cortas el calentamiento pesa demasiado.
      - distancia y TRIMP positivos.
    """
    if trimp_method != EFF_METODO_VALIDO:
        return None
    if hr_coverage is None or float(hr_coverage) < min_hr_coverage:
        return None
    if duration_s is None or float(duration_s) < min_duracion_s:
        return None
    if distance_m is None or trimp is None:
        return None
    dist, carga = float(distance_m), float(trimp)
    if not np.isfinite(dist) or not np.isfinite(carga):
        return None
    if dist <= 0 or carga <= 0:
        return None
    return dist / carga


# =============================================================================
# Serie diaria
# =============================================================================

# Orden explícito de columnas de daily_load. Nombrarlas (en vez de un SELECT
# posicional) es lo que permite que el esquema siga creciendo con migraciones
# aditivas sin romper esta inserción: invariante 3 del proyecto.
DAILY_LOAD_COLS = [
    "date_local", "trimp", "n_activities", "atl", "ctl", "tsb", "acwr", "risk",
    "load_7d", "load_14d", "load_21d", "load_28d", "load_7d_pct",
    "wow_change", "wow_flag", "monotonia", "strain",
]


def rebuild_daily_load(con) -> pd.DataFrame:
    """Reconstruye la tabla daily_load completa desde activities.

    Idempotente por construcción: DELETE + INSERT completo. Correrla N veces
    sobre la misma base deja exactamente el mismo resultado.
    """
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

    # --- ACWR: se conserva como señal cultural, ya NO como vehículo principal.
    # Impellizzeri et al. 2021 (Sports Med 51:581-592) mostró que sustituir la
    # carga crónica por ruido aleatorio no cambia su asociación con lesión, y
    # Dalen-Lorentsen et al. 2021 (BJSM) no halló beneficio clínico en un ECA
    # con 482 futbolistas. Se mantiene por continuidad del dashboard (D-016:
    # con sus limitaciones a la vista), acompañado de la carga absoluta.
    acute = s["trimp"].rolling(7, min_periods=7).mean()
    chronic = s["trimp"].rolling(28, min_periods=28).mean()
    s["acwr"] = np.where(chronic > 1e-9, acute / chronic, np.nan)
    s["risk"] = [classify_acwr(v if not pd.isna(v) else None) for v in s["acwr"]]

    # --- Carga absoluta acumulada (Rogalski et al. 2013, JSAMS 16:499-503).
    # La carga semanal acumulada y sus ventanas más largas discriminan riesgo
    # SIN el acoplamiento matemático que arruina al ACWR (Lolli et al. 2019,
    # BJSM 53:921-922: aguda dentro de crónica ⇒ correlación espuria).
    # min_periods = ventana completa: media semana no es una semana.
    for v in (7, 14, 21, 28):
        s[f"load_{v}d"] = s["trimp"].rolling(v, min_periods=v).sum()

    # --- Percentil personal: hace legible el número absoluto sin umbrales
    # importados ("percentil 0.88 de tu propio año" en vez de "412 TRIMP").
    s["load_7d_pct"] = percentil_movil(s["load_7d"])

    # --- Cambio semana-a-semana con umbral individualizado (Cross et al. 2016,
    # IJSPP 11:350-355 → "2 DE"). La DE es la de Jorge, en ventana de 365 días.
    s["wow_change"] = cambio_semanal(s["load_7d"])
    sd_wow = s["wow_change"].rolling(VENTANA_REF_D, min_periods=MIN_DIAS_REF).std()
    s["wow_flag"] = pd.Series(
        [clasificar_cambio(c, d) for c, d in zip(s["wow_change"], sd_wow)],
        index=s.index,
        dtype="object",
    )

    # --- Monotonía y strain (Foster 1998, MSSE 30:1164-1168) como serie diaria.
    # Hasta ahora solo se calculaban puntualmente en recommendations.py; tenerlos
    # como serie permite ver la tendencia y no solo la foto de hoy.
    s["monotonia"], s["strain"] = monotonia_strain(s["trimp"])

    out = s.reset_index().rename(columns={"index": "date_local"})
    out["date_local"] = out["date_local"].dt.date
    out = out[DAILY_LOAD_COLS]

    cols = ", ".join(DAILY_LOAD_COLS)
    con.execute("DELETE FROM daily_load")
    con.register("dl", out)
    con.execute(f"INSERT INTO daily_load ({cols}) SELECT {cols} FROM dl")
    con.unregister("dl")
    return out


def _num(v, nd: int = 2):
    """Redondeo seguro para el reporte: NaN/None/inf → None (nunca 'nan' en pantalla)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else round(f, nd)


def refresh_all(db_path) -> dict:
    """TRIMP pendientes + reconstrucción de daily_load. Reporte resumido.

    Mantiene las claves históricas (`trimp_calculados`, `dias_serie`, `acwr_hoy`,
    `riesgo_hoy`) para no romper a quien ya las consume, y suma las de la carga
    absoluta, que son las que ahora deberían leerse primero.
    """
    con = connect(db_path)
    try:
        n_trimp = compute_trimp(con)
        daily = rebuild_daily_load(con)
        last = daily.iloc[-1] if not daily.empty else None
        if last is None:
            base = dict.fromkeys(
                ["acwr_hoy", "riesgo_hoy", "carga_7d", "carga_7d_pct", "carga_28d",
                 "cambio_semanal", "cambio_flag", "monotonia", "strain"]
            )
        else:
            base = {
                "acwr_hoy": _num(last["acwr"]),
                "riesgo_hoy": last["risk"],
                "carga_7d": _num(last["load_7d"], 0),
                "carga_7d_pct": _num(last["load_7d_pct"], 2),
                "carga_28d": _num(last["load_28d"], 0),
                "cambio_semanal": _num(last["wow_change"], 3),
                "cambio_flag": last["wow_flag"],
                "monotonia": _num(last["monotonia"], 2),
                "strain": _num(last["strain"], 0),
            }
        return {"trimp_calculados": n_trimp, "dias_serie": int(len(daily)), **base}
    finally:
        con.close()
