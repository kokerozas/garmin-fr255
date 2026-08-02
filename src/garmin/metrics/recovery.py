"""Serie derivada de recuperación con BANDAS PERSONALES (D-017).

Idea central: un valor de recuperación (FC en reposo, sueño, HRV) NO se juzga
contra un umbral universal importado de un libro, sino contra la propia norma
del atleta y su propia variabilidad. Lo que para Jorge es "alto" depende de
cuánto oscila Jorge, no de cuánto oscila un futbolista promedio.

Qué construye este módulo (tabla ``daily_recovery``, una fila por día):

1. **Banda personal de FC en reposo (SWC).** Referencia = media móvil de 28
   días; banda = referencia ± 0.5 · DE de esa misma ventana. Ese 0.5·DE es el
   *smallest worthwhile change* de Hopkins (2000): el cambio más pequeño que
   vale la pena tomarse en serio en una medida repetida.
   Reemplaza la regla anterior del proyecto ("media 7d > media 28d + 5 ppm"),
   que en los datos reales de Jorge (DE ≈ 3.6 ppm) equivalía a ~1.4 DE
   individuales: 3-5 veces más insensible que lo que usa la literatura, o sea
   que solo se encendía cuando el problema ya era enorme. Aquí el corte sale
   ≈ 1.8 ppm. Se compara la media de 7 días (no la noche suelta) contra la
   banda, porque una noche mala es ruido y lo que importa es lo sostenido:
   por eso también se cuenta ``rhr_days_out`` = días consecutivos sobre banda.

2. **Deuda de sueño acumulada.** Σ max(0, necesidad − horas dormidas) en
   ventanas de 7/14/28 días, con la necesidad configurable (default 8.0 h).
   Regla dura de honestidad: **una noche sin dato NO es una noche sin deuda.**
   Solo se suman noches medidas, se exige un mínimo de noches por ventana
   (5/10/20) y por debajo de ese mínimo la deuda es NaN — no un número
   tranquilizador inventado. Además se publica ``sleep_cov_7d`` (% de noches
   con dato) para que el dashboard muestre sobre cuánta evidencia habla.
   Consecuencia a tener presente: como los huecos no se rellenan, la deuda
   reportada es un **piso** (subestima), nunca una exageración.

3. **Ln(rMSSD) 7 días y su CV.** Con una PUERTA DE VALIDEZ explícita: mínimo 3
   noches válidas en la semana y al menos 21 días de historia de HRV. Mientras
   no se cumpla, devuelve NaN con motivo en vez de dibujar ruido con cara de
   tendencia. Hoy Jorge tiene HRV nocturno solo desde 2026-07-18 (verificado,
   no es un bug del pipeline): faltan ~3 semanas de sincronizaciones para que
   esta serie signifique algo. ``estado_hrv()`` calcula cuántos días faltan.

Referencias primarias (D-016 — nada se inventa):
- Buchheit, M. (2014). *Monitoring training status with HR measures: do all
  roads lead to Rome?* Frontiers in Physiology 5:73. — FC de reposo y HRV como
  marcadores de estado; prioridad de la tendencia sobre el valor aislado.
- Hopkins, W.G. (2000). *Measures of reliability in sports medicine and
  science.* Sports Medicine 30(1):1-15. — SWC = 0.5 · DE individual.
- Plews, D.J., Laursen, P.B., Stanley, J., Kilding, A.E. & Buchheit, M. (2013).
  *Training adaptation and heart rate variability in elite endurance athletes.*
  Sports Medicine 43(9):773-781. — Ln(rMSSD) promediado semanalmente y su
  coeficiente de variación como índice de estabilidad autonómica.
- Milewski, M.D. et al. (2014). *Chronic lack of sleep is associated with
  increased sports injuries in adolescent athletes.* J Pediatr Orthop
  34(2):129-133. — dormir <8 h ≈ 1.7× más lesiones.
- von Rosen, P. et al. (2017). *Multiple factors explain injury risk in
  adolescent elite athletes.* Scand J Med Sci Sports 27(11):1364-1371. —
  dormir >8 h reduce las odds de lesión ~61 %.

Limitaciones documentadas:
- **El sueño de reloj de muñeca SOBREESTIMA** frente a polisomnografía: la
  actigrafía clasifica como sueño la vigilia tranquila. Las 5.4 h medias
  medidas de Jorge son probablemente MENOS de 5.4 h reales, así que la deuda
  calculada es conservadora por partida doble (huecos no imputados + medición
  optimista).
- Milewski y von Rosen son cohortes de adolescentes; el tamaño del efecto no
  se traslada literalmente a un adulto amateur. Se usan como dirección y
  magnitud aproximada del riesgo, no como una probabilidad personal.
- La banda SWC describe variación normal, no causa: salir de la banda dice
  "algo cambió" (fatiga, infección, alcohol, calor, estrés), no *qué* cambió.
- El rMSSD viene del reloj (medición de tercero, sin banda pectoral): sirve
  para tendencia propia, no para comparar contra valores de laboratorio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from garmin.db.schema import connect
from garmin.utils.config import load_settings

# --- Parámetros del método (cada uno con su porqué) --------------------------
SWC_K = 0.5              # Hopkins 2000: cambio mínimo que vale la pena = 0.5·DE
VENTANA_REF = 28         # días de la referencia personal móvil (norma reciente)
MIN_DIAS_REF = 14        # con menos de 14 días medidos, la DE de 28d no es fiable
VENTANA_CORTA = 7        # ventana "estado actual"
MIN_DIAS_CORTA = 4       # al menos 4 de 7 noches medidas para hablar de la semana

NECESIDAD_H_DEFAULT = 8.0            # Milewski 2014 / von Rosen 2017
MIN_NOCHES = {7: 5, 14: 10, 28: 20}  # cobertura mínima por ventana de deuda

HRV_MIN_NOCHES_SEMANA = 3   # Plews 2013: 3 registros/semana es el piso práctico
HRV_MIN_HISTORIA_D = 21     # antes de 3 semanas no hay contra qué comparar

# Columnas de daily_recovery, en el orden exacto del esquema (schema.py).
COLUMNAS = [
    "date_local", "rhr_7d", "rhr_ref", "rhr_band_lo", "rhr_band_hi",
    "rhr_state", "rhr_days_out", "sleep_debt_7d", "sleep_debt_14d",
    "sleep_debt_28d", "sleep_cov_7d", "sleep_7d", "sleep_ref",
    "ln_rmssd_7d", "ln_rmssd_cv",
]


# =============================================================================
# 1. Banda personal por SWC (Hopkins 2000)
# =============================================================================

def banda_swc(serie: pd.Series, ventana: int = VENTANA_REF,
              min_dias: int = MIN_DIAS_REF, k: float = SWC_K):
    """Referencia móvil y su banda ± k·DE. Devuelve (ref, lo, hi, de).

    La DE se calcula sobre la MISMA ventana que la media: así la banda se
    ensancha en épocas revueltas (viajes, enfermedad) y se angosta cuando el
    atleta está estable — que es justo lo que uno quiere de una norma personal.
    Con menos de ``min_dias`` medidos en la ventana, todo sale NaN: preferimos
    no tener banda a tener una banda inventada con 3 datos.
    """
    ref = serie.rolling(ventana, min_periods=min_dias).mean()
    de = serie.rolling(ventana, min_periods=min_dias).std(ddof=1)
    return ref, ref - k * de, ref + k * de, de


def clasificar_banda(valor, lo, hi) -> str | None:
    """bajo_banda | dentro | sobre_banda (None si falta cualquiera de los tres)."""
    if valor is None or lo is None or hi is None:
        return None
    if pd.isna(valor) or pd.isna(lo) or pd.isna(hi):
        return None
    if valor > hi:
        return "sobre_banda"
    if valor < lo:
        return "bajo_banda"
    return "dentro"


def dias_consecutivos_fuera(estados) -> list[int]:
    """Racha de días consecutivos en 'sobre_banda' (0 si dentro/bajo/sin dato).

    Lo sostenido pesa más que el pico: 1 día sobre la banda es una mala noche;
    4 días seguidos es el cuerpo avisando algo (Buchheit 2014). Un día sin
    banda calculable corta la racha — no la continúa por suposición.
    """
    racha, out = 0, []
    for e in estados:
        racha = racha + 1 if e == "sobre_banda" else 0
        out.append(racha)
    return out


# =============================================================================
# 2. Deuda de sueño (Milewski 2014 · von Rosen 2017)
# =============================================================================

def necesidad_sueno_h(cfg: dict | None = None) -> float:
    """Horas necesarias por noche: config/settings.yaml → recuperacion.necesidad_sueno_h.

    Tolerante a que la sección o la clave no existan (default 8.0 h, el umbral
    de Milewski 2014). Este módulo solo LEE settings; nunca lo escribe.
    """
    cfg = cfg if cfg is not None else load_settings()
    valor = (cfg.get("recuperacion") or {}).get("necesidad_sueno_h")
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return NECESIDAD_H_DEFAULT
    return valor if 4.0 <= valor <= 12.0 else NECESIDAD_H_DEFAULT


def deficit_nocturno(sleep_h: pd.Series, necesidad: float) -> pd.Series:
    """max(0, necesidad − dormido) noche a noche. Sin dato ⇒ NaN, NUNCA 0.

    Esta línea es el corazón de la honestidad del módulo: si rellenáramos con
    0 estaríamos afirmando "esa noche durmió lo suficiente", que es exactamente
    lo que no sabemos.
    """
    h = pd.to_numeric(sleep_h, errors="coerce")
    return (necesidad - h).clip(lower=0.0)  # NaN se propaga solo


def deuda_sueno(sleep_h: pd.Series, necesidad: float, ventana: int,
                min_noches: int | None = None) -> pd.Series:
    """Deuda acumulada en la ventana. NaN si no hay noches suficientes.

    Solo se suman las noches medidas, así que el resultado es un PISO de la
    deuda real (las noches ausentes no aportan). Por eso siempre se publica
    junto a la cobertura: 6 h de deuda con 7/7 noches y 6 h con 5/7 noches no
    son la misma afirmación.
    """
    min_noches = MIN_NOCHES.get(ventana, max(1, ventana // 2)) if min_noches is None else min_noches
    deficit = deficit_nocturno(sleep_h, necesidad)
    return deficit.rolling(ventana, min_periods=min_noches).sum()


def cobertura_sueno(sleep_h: pd.Series, ventana: int = VENTANA_CORTA) -> pd.Series:
    """% de noches con dato en la ventana (0-100). La honestidad del número."""
    medidas = pd.to_numeric(sleep_h, errors="coerce").notna().astype(float)
    return 100.0 * medidas.rolling(ventana, min_periods=1).sum() / float(ventana)


# =============================================================================
# 3. Ln(rMSSD) con puerta de validez (Plews 2013)
# =============================================================================

def estado_hrv(hrv: pd.Series, fechas: pd.Series | None = None) -> dict:
    """¿Ya se puede interpretar el HRV? Motivo y días que faltan si no.

    Dos condiciones (Plews 2013): densidad (≥3 noches por semana) e historia
    (≥21 días desde la primera medición, para tener contra qué comparar).
    """
    v = pd.to_numeric(hrv, errors="coerce")
    validos = v.notna()
    n = int(validos.sum())
    if n == 0:
        return {"valido": False, "motivo": "aún no hay noches con HRV",
                "n_noches": 0, "dias_historia": 0, "dias_faltantes": HRV_MIN_HISTORIA_D}

    idx = fechas if fechas is not None else pd.Series(v.index, index=v.index)
    idx = pd.to_datetime(pd.Series(list(idx), index=v.index))
    primera, ultima = idx[validos].min(), idx[validos].max()
    dias_historia = int((ultima - primera).days) + 1
    faltan = max(0, HRV_MIN_HISTORIA_D - dias_historia)

    if faltan > 0:
        return {"valido": False,
                "motivo": (f"historia insuficiente: {dias_historia} días de HRV, "
                           f"faltan ~{faltan} para poder leer tendencia"),
                "n_noches": n, "dias_historia": dias_historia, "dias_faltantes": faltan}
    if n < HRV_MIN_NOCHES_SEMANA:
        return {"valido": False,
                "motivo": f"solo {n} noches medidas: se necesitan ≥{HRV_MIN_NOCHES_SEMANA} por semana",
                "n_noches": n, "dias_historia": dias_historia, "dias_faltantes": 0}
    return {"valido": True, "motivo": "serie interpretable",
            "n_noches": n, "dias_historia": dias_historia, "dias_faltantes": 0}


def ln_rmssd_movil(hrv: pd.Series, ventana: int = VENTANA_CORTA,
                   min_noches: int = HRV_MIN_NOCHES_SEMANA):
    """Media móvil de Ln(rMSSD) y su CV (%). Devuelve (media, cv).

    Se promedia el LOGARITMO, no el rMSSD crudo, porque el rMSSD tiene
    distribución muy sesgada y una sola noche buena arrastraría la media
    (Plews 2013). El CV mide estabilidad: subir el CV = sistema autónomo
    inestable, típico de fatiga acumulada o estrés.
    """
    v = pd.to_numeric(hrv, errors="coerce")
    ln = np.log(v.where(v > 0))
    media = ln.rolling(ventana, min_periods=min_noches).mean()
    de = ln.rolling(ventana, min_periods=min_noches).std(ddof=1)
    cv = 100.0 * de / media.abs()
    return media, cv


# =============================================================================
# 4. Serie completa (función pura: recibe DataFrame, no toca la base)
# =============================================================================

def compute_recovery(dm: pd.DataFrame, necesidad_h: float | None = None) -> pd.DataFrame:
    """Construye la serie diaria de recuperación desde daily_metrics.

    ``dm`` necesita: date_local, rhr, sleep_h, hrv_rmssd (las tres últimas
    pueden venir con huecos: eso es lo normal y el módulo está hecho para eso).
    Devuelve un DataFrame con exactamente las columnas de ``daily_recovery``.
    """
    if dm is None or dm.empty:
        return pd.DataFrame(columns=COLUMNAS)

    necesidad = necesidad_sueno_h() if necesidad_h is None else float(necesidad_h)

    d = dm.copy()
    d["date_local"] = pd.to_datetime(d["date_local"])
    for col in ("rhr", "sleep_h", "hrv_rmssd"):
        d[col] = pd.to_numeric(d.get(col), errors="coerce")
    d = d.groupby("date_local", as_index=True)[["rhr", "sleep_h", "hrv_rmssd"]].mean()

    # Calendario continuo: los días sin registro deben EXISTIR como huecos,
    # si no las ventanas de 7/28 días medirían "últimos 28 datos" en vez de
    # "últimos 28 días" (y con 90 % de cobertura eso desplaza todo).
    idx = pd.date_range(d.index.min(), d.index.max(), freq="D")
    s = d.reindex(idx)

    out = pd.DataFrame(index=idx)

    # --- FC en reposo: estado actual vs banda personal ------------------------
    out["rhr_7d"] = s["rhr"].rolling(VENTANA_CORTA, min_periods=MIN_DIAS_CORTA).mean()
    ref, lo, hi, _de = banda_swc(s["rhr"])
    out["rhr_ref"], out["rhr_band_lo"], out["rhr_band_hi"] = ref, lo, hi
    out["rhr_state"] = [
        clasificar_banda(v, l, h)
        for v, l, h in zip(out["rhr_7d"], out["rhr_band_lo"], out["rhr_band_hi"])
    ]
    out["rhr_days_out"] = dias_consecutivos_fuera(out["rhr_state"])

    # --- Sueño: deuda acumulada + cobertura ----------------------------------
    for v in (7, 14, 28):
        out[f"sleep_debt_{v}d"] = deuda_sueno(s["sleep_h"], necesidad, v)
    out["sleep_cov_7d"] = cobertura_sueno(s["sleep_h"], VENTANA_CORTA)
    out["sleep_7d"] = s["sleep_h"].rolling(VENTANA_CORTA, min_periods=MIN_DIAS_CORTA).mean()
    out["sleep_ref"] = s["sleep_h"].rolling(VENTANA_REF, min_periods=MIN_DIAS_REF).mean()

    # --- HRV: solo si pasa la puerta de validez ------------------------------
    # La densidad (≥3 noches por semana) ya la impone min_periods; falta la
    # historia: se tapa todo día que esté a menos de 21 días de la primera
    # noche medida. Preferimos un hueco honesto a una línea de ruido.
    media, cv = ln_rmssd_movil(s["hrv_rmssd"])
    con_hrv = s["hrv_rmssd"].notna()
    if con_hrv.any():
        primera = s.index[con_hrv].min()
        historia_d = (pd.Series(idx, index=idx) - primera).dt.days + 1
        joven = historia_d < HRV_MIN_HISTORIA_D
        media, cv = media.mask(joven), cv.mask(joven)
    else:
        media = cv = pd.Series(np.nan, index=idx)
    out["ln_rmssd_7d"], out["ln_rmssd_cv"] = media, cv

    out = out.reset_index().rename(columns={"index": "date_local"})
    out["date_local"] = out["date_local"].dt.date
    out["rhr_days_out"] = out["rhr_days_out"].astype("Int64")
    return out[COLUMNAS]


# =============================================================================
# 5. Persistencia idempotente (patrón DELETE + INSERT, como rebuild_daily_load)
# =============================================================================

def rebuild_daily_recovery(con) -> pd.DataFrame:
    """Reconstruye daily_recovery completa desde daily_metrics. Idempotente.

    Correrla N veces deja exactamente el mismo resultado: primero borra, luego
    inserta la serie entera. Nada de actualizaciones parciales que se desfasen.
    """
    dm = con.execute(
        """SELECT date_local,
                  COALESCE(resting_hr, hr_min) AS rhr,   -- oficial de Garmin; si no, FC mínima
                  sleep_h,
                  hrv_last_night AS hrv_rmssd
           FROM daily_metrics
           WHERE date_local IS NOT NULL
           ORDER BY date_local"""
    ).df()

    out = compute_recovery(dm)
    con.execute("DELETE FROM daily_recovery")
    if out.empty:
        return out

    # NaN → NULL explícito: en la base "no medido" debe ser NULL, no un NaN
    # que luego se cuele en promedios o comparaciones.
    ins = out.astype(object).where(pd.notna(out), None)
    con.register("dr_tmp", pd.DataFrame(ins))
    con.execute(f"INSERT INTO daily_recovery ({', '.join(COLUMNAS)}) "
                f"SELECT {', '.join(COLUMNAS)} FROM dr_tmp")
    con.unregister("dr_tmp")
    return out


def refresh_recovery(db_path) -> dict:
    """Reconstruye la serie y devuelve el resumen para el print de ingest.py."""
    con = connect(db_path)
    try:
        out = rebuild_daily_recovery(con)
        hrv = con.execute(
            "SELECT hrv_last_night FROM daily_metrics ORDER BY date_local"
        ).df()
        puerta = estado_hrv(hrv["hrv_last_night"]) if not hrv.empty else \
            {"motivo": "sin datos", "dias_faltantes": HRV_MIN_HISTORIA_D}
    finally:
        con.close()

    if out.empty:
        return {"dias_serie": 0, "dias_con_banda": 0, "hrv_motivo": puerta["motivo"]}

    ult = out.iloc[-1]
    def _num(x, nd=1):
        return None if x is None or pd.isna(x) else round(float(x), nd)

    return {
        "dias_serie": int(len(out)),
        "ultimo_dia": str(ult["date_local"]),
        "dias_con_banda": int(out["rhr_band_hi"].notna().sum()),
        "rhr_estado": ult["rhr_state"],
        "rhr_dias_fuera": None if pd.isna(ult["rhr_days_out"]) else int(ult["rhr_days_out"]),
        "deuda_7d_h": _num(ult["sleep_debt_7d"]),
        "cobertura_sueno_7d_pct": _num(ult["sleep_cov_7d"], 0),
        "hrv_motivo": puerta["motivo"],
        "hrv_dias_faltantes": puerta.get("dias_faltantes"),
    }
