"""Dashboard — Garmin FR255 (D-003, rediseñado en D-019).

Ejecutar desde la raíz del proyecto:
    streamlit run dashboard/app.py

Cinco vistas: "Hoy" (lo accionable), "Carga", "Recuperación", "Registrar" y
"Explorar" (incluye el 3D). Lee la base DuckDB en solo-lectura; la ingesta corre
aparte (scripts/ingest.py).

JERARQUÍA DEL REPORTE (Buchheit 2017, "Want to see my report, coach?", IJSPP).
Lo accionable va arriba y el detalle abajo: la vista "Hoy" responde la única
pregunta que Jorge se hace el día del partido, y todo lo demás está para cuando
quiera entender el porqué. Los gráficos 3D viven en "Explorar" y jamás alimentan
recomendaciones (D-019).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from garmin import formulas, guides, viz  # noqa: E402
from garmin.metrics import readiness as rdy_mod  # noqa: E402
from garmin.metrics import wellness  # noqa: E402
from garmin.metrics.recommendations import build_recommendations  # noqa: E402
from garmin.utils.config import db_path  # noqa: E402

st.set_page_config(page_title="Garmin FR255 — Carga y riesgo", layout="wide")

DB = db_path()


@st.cache_data(show_spinner=False)
def q(sql: str, params: tuple = (), _mtime: float = 0.0) -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql, list(params)).df()
    finally:
        con.close()


def mtime() -> float:
    return DB.stat().st_mtime if DB.exists() else 0.0


@st.cache_data(show_spinner=False)
def recomendaciones(_mtime: float) -> list[dict]:
    return build_recommendations(DB)


@st.cache_data(show_spinner=False)
def readiness(_mtime: float) -> dict:
    return wellness.match_readiness(DB)


@st.cache_data(show_spinner=False)
def estado_dominios(_mtime: float) -> dict:
    return rdy_mod.estado_global(DB)


def ficha_formula(f: dict, compacta: bool = False) -> None:
    """Renderiza una ficha del formulario: fórmula, parámetros, código y citas."""
    if not compacta:
        st.markdown(f"#### {f['nombre']}")
        st.caption(f["pregunta"])
    st.latex(f["latex"])
    if f.get("variables"):
        st.markdown("**Dónde:** " + " · ".join(
            f"$`{sym}`$ {desc}" for sym, desc in f["variables"].items()))
    if f.get("parametros"):
        st.markdown("**Valores en este proyecto:** " + " · ".join(
            f"$`{k}`$ = {v}" if k.startswith("\\") else f"{k}: **{v}**"
            for k, v in f["parametros"].items()))
    st.markdown(f"**Implementado en:** `{f['implementacion']}`")
    with st.expander("📚 Referencias y limitaciones"):
        for r in f["referencias"]:
            st.markdown(f"- {r}")
        st.warning(f"**Limitaciones:** {f['limitaciones']}")


# Guía → fórmulas que le corresponden, para que el botón ℹ️ pueda mostrar la ecuación
# sin que haya que mantener el enlace a mano en dos sitios.
_FORMULAS_POR_GUIA: dict[str, list[dict]] = {}
for _f in formulas.FORMULAS:
    _FORMULAS_POR_GUIA.setdefault(_f.get("guia"), []).append(_f)


def guia(key: str) -> None:
    """Botón ℹ️ con la explicación del panel (D-014) y su fórmula exacta (D-021)."""
    if key not in guides.GUIDES:
        return
    with st.popover("ℹ️ ¿Cómo leer este panel?"):
        st.markdown(guides.GUIDES[key])
        for f in _FORMULAS_POR_GUIA.get(key, []):
            st.divider()
            st.markdown(f"##### 🧮 {f['nombre']}")
            ficha_formula(f, compacta=True)


def panel(fig, key: str | None = None, **kw) -> None:
    """Un gráfico y su guía, siempre juntos: evita el botón ℹ️ huérfano."""
    st.plotly_chart(fig, width="stretch", **kw)
    if key:
        guia(key)


if not DB.exists():
    st.error("No existe la base de datos. Ejecuta primero:  python scripts/ingest.py")
    st.stop()

M = mtime()
st.sidebar.title("Garmin FR255")
page = st.sidebar.radio(
    "Vista", ["Hoy", "Carga", "Recuperación", "Registrar", "Explorar",
              "Detalle de actividad", "Fórmulas"],
)
OSCURO = st.sidebar.toggle(
    "Modo oscuro", value=False,
    help="Cambia el fondo de los gráficos. La paleta de colores es la misma: "
         "está validada para daltonismo en ambos modos.",
)
st.sidebar.caption("Datos: DuckDB local · métricas propias (D-007/D-018). "
                   "La ingesta se corre con scripts/ingest.py.")

RANGOS = {"90 días": 90, "6 meses": 183, "1 año": 365, "Todo": 10000}
# 'sin_datos' es un estado de pleno derecho: un factor sin información no se pinta
# como si estuviera bien. Se usa .get() porque los módulos pueden sumar estados
# nuevos y un panel del dashboard nunca debe caerse por un estado desconocido.
EMOJI = {"ok": "✅", "ojo": "⚠️", "alto": "⛔", "sin_datos": "◻️"}


def selector_rango(key: str, index: int = 1) -> int:
    etiqueta = st.radio("Rango", list(RANGOS), horizontal=True, index=index,
                        label_visibility="collapsed", key=key)
    return RANGOS[etiqueta]


# =============================================================== Vista: Hoy
if page == "Hoy":
    st.title("¿Puedo jugar hoy?")

    rd = readiness(M)
    CAJA = {"ok": st.success, "ojo": st.warning, "alto": st.error}
    CAJA[rd["estado"]](f"## {rd['titulo']}")

    factores = list(rd["factores"].items())
    for fila in (factores[:2], factores[2:]):
        if not fila:
            continue
        for col, (nombre, f) in zip(st.columns(len(fila)), fila):
            col.markdown(f"{EMOJI.get(f['estado'], '•')} **{nombre}**")
            col.caption(f["razon"])
    guia("puedo_jugar")
    st.divider()

    # --- Los cuatro dominios del índice de disposición (D-018) ---
    st.subheader("Tu estado por dominios")
    est = estado_dominios(M)
    detalle = est.get("detalle") or []
    if detalle:
        ICONO_DOM = {"ok": "✅", "ojo": "⚠️", "alerta": "⛔"}
        for col, d in zip(st.columns(max(len(detalle), 2)), detalle):
            z = d.get("z")
            col.metric(f"{ICONO_DOM.get(d.get('estado'), '•')} {d['dominio']}",
                       "—" if z is None else f"{z:+.1f} DE")
            col.caption(d.get("razon") or "")
        st.caption(
            f"{est.get('dominios_alerta', 0)} de {est.get('dominios_evaluables', 0)} "
            "dominios evaluables en alerta. Cada valor es cuántas desviaciones estás "
            "de TU propia normal de 60 días — no de un umbral de otra persona. "
            "Es un conteo de banderas, no un modelo de riesgo calibrado."
        )
        if est.get("motivo"):
            st.caption(f"ℹ️ {est['motivo']}")
    else:
        st.info("Aún no hay dominios evaluables. Sincroniza el reloj o registra tu "
                "estado en la vista **Registrar**.")
    guia("readiness")
    st.divider()

    # --- Molestias por zona: dumbbell en vez de radar (D-019) ---
    dolores_hoy = wellness.pain_status(DB, dias=7)
    dolores_28 = {d["zona"]: d for d in wellness.pain_status(DB, dias=28)}
    if dolores_hoy:
        zonas = [{"zona": d["zona"], "actual": d["nivel_max"],
                  "promedio": dolores_28.get(d["zona"], {}).get("nivel_max", 0)}
                 for d in dolores_hoy]
        panel(viz.fig_molestias_dumbbell(zonas, dark=OSCURO), "molestias_zonas")
    else:
        st.info("Sin molestias registradas en los últimos 7 días. El registro toma "
                "30 segundos y es lo único que ve lo que el reloj no ve.")

    st.subheader("🧭 Recomendaciones")
    ICONO = {"alerta": st.error, "atencion": st.warning, "info": st.info, "ok": st.success}
    for r in recomendaciones(M):
        ICONO.get(r["nivel"], st.info)(f"**{r['titulo']}** — {r['detalle']}")
    guia("recomendaciones")
    st.caption("Motor de reglas transparente sobre tus métricas (no es consejo "
               "médico; ante dolor real, profesional de salud).")

# ============================================================== Vista: Carga
elif page == "Carga":
    st.title("Carga de entrenamiento")
    dias = selector_rango("rango_carga")

    daily = q(
        """SELECT date_local, trimp, n_activities, atl, ctl, tsb, acwr, risk,
                  load_7d, load_14d, load_28d, load_7d_pct, wow_change, wow_flag,
                  monotonia, strain
           FROM daily_load
           WHERE date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY
           ORDER BY date_local""",
        (dias,), M,
    )
    hoy = daily.iloc[-1] if not daily.empty else None

    # KPIs: la carga ABSOLUTA manda; el ACWR pasa a acompañante (D-018).
    c1, c2, c3, c4 = st.columns(4)
    if hoy is not None:
        carga7 = None if pd.isna(hoy.load_7d) else hoy.load_7d
        pct = None if pd.isna(hoy.load_7d_pct) else hoy.load_7d_pct * 100
        wow = None if pd.isna(hoy.wow_change) else hoy.wow_change * 100
        c1.metric("Carga de 7 días", "—" if carga7 is None else f"{carga7:.0f} TRIMP",
                  None if wow is None else f"{wow:+.0f}% vs semana previa")
        c2.metric("Percentil de tu año", "—" if pct is None else f"{pct:.0f}")
        c3.metric("Forma (CTL)", f"{hoy.ctl:.0f}")
        c4.metric("Balance (TSB)", f"{hoy.tsb:+.0f}")
        # Ojo con el NaN: pandas convierte un VARCHAR nulo de DuckDB en float('nan'),
        # y bool(nan) es True — un `if hoy.wow_flag:` a secas deja pasar los vacíos.
        if pd.notna(hoy.wow_flag) and wow is not None:
            aviso = {"rojo": st.error, "ambar": st.warning}.get(hoy.wow_flag, st.info)
            aviso(f"Salto de carga inusual para ti ({wow:+.0f} % respecto a la semana "
                  "previa): supera tu propia variabilidad habitual.")
    guia("carga_absoluta")

    panel(viz.fig_carga_absoluta(daily, dark=OSCURO), "carga_absoluta")
    panel(viz.fig_calendar_load(daily, dark=OSCURO), "calendario_carga")
    panel(viz.fig_daily_load(daily), "carga_diaria")

    with st.expander("Señales secundarias: ACWR, monotonía y reparto por deporte"):
        st.caption(
            "El ACWR está aquí abajo a propósito: sigue siendo descriptivo, pero dejó "
            "de ser el número principal (ver su guía ℹ️)."
        )
        panel(viz.fig_acwr(daily), "acwr")
        acts = q(
            """SELECT date_local, sport, trimp FROM activities
               WHERE trimp IS NOT NULL
                 AND date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY""",
            (dias,), M,
        )
        panel(viz.fig_weekly_by_sport(acts), "semanal_deporte")

    # --- Carga externa y fatiga intra-partido (D-018) ---
    st.subheader("Carga externa: lo que sufrió el músculo")
    ext = q(
        """SELECT a.date_local, a.sport, e.m_per_min_act, e.eff_index, e.gps_grade,
                  e.hsr_m, e.distance_m
           FROM activity_external e JOIN activities a USING (activity_id)
           WHERE a.date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY
           ORDER BY a.date_local""",
        (dias,), M,
    )
    if ext.empty:
        st.info("Sin sesiones con carga externa en este rango.")
    else:
        g = ext["gps_grade"].value_counts().to_dict()
        e1, e2, e3 = st.columns(3)
        e1.metric("Sesiones con distancia", int(ext["distance_m"].notna().sum()))
        e2.metric("Con señal de grado alto", int(g.get("alta", 0)),
                  help="Solo estas permiten contar sprints y distancia a alta velocidad.")
        e3.metric("Con índice de eficiencia", int(ext["eff_index"].notna().sum()))
        if not g.get("alta") and ext["gps_grade"].notna().any():
            st.warning(
                "Ninguna sesión de este rango tiene señal de grado alto, así que no hay "
                "conteo de sprints ni distancia a alta velocidad. En el reloj: "
                "**Configuración > Sistema > Grabación de datos > Cada segundo** "
                "activa esas métricas de ahí en adelante."
            )
        eff = ext.dropna(subset=["eff_index"])
        if not eff.empty:
            panel(viz.fig_daily_line(eff.rename(columns={"date_local": "date_local"}),
                                     "eff_index", "Índice de eficiencia (metros por TRIMP)",
                                     "m/TRIMP", slot=2, fmt=".1f"), "eficiencia")
        else:
            guia("carga_externa")

    intra = q(
        """SELECT a.date_local, i.decoupling_pct
           FROM activity_intrasession i JOIN activities a USING (activity_id)
           WHERE i.decoupling_pct IS NOT NULL
             AND a.date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY
           ORDER BY a.date_local""",
        (dias,), M,
    )
    if not intra.empty:
        panel(viz.fig_decoupling(intra, dark=OSCURO), "decoupling")

    st.subheader("Últimas actividades")
    last = q(
        """SELECT CAST(date_local AS VARCHAR) AS fecha, sport, sport_profile AS perfil,
                  ROUND(duration_s/60) AS minutos, ROUND(distance_m/1000, 2) AS km,
                  avg_hr AS fc_media, max_hr AS fc_max, ROUND(trimp,1) AS trimp,
                  ROUND(hr_coverage*100) AS calidad_fc_pct
           FROM activities ORDER BY start_time_utc DESC LIMIT 15""", (), M,
    )
    last["sport"] = last["sport"].map(viz.sport_display)
    last = last.rename(columns={"sport": "deporte", "calidad_fc_pct": "calidad FC %"})
    st.dataframe(last, width="stretch", hide_index=True)

# ======================================================= Vista: Recuperación
elif page == "Recuperación":
    st.title("Recuperación")
    dias_r = selector_rango("rango_rec")

    dm = q(
        """SELECT m.*, COALESCE(m.resting_hr, m.hr_min) AS fc_reposo,
                  r.rhr_7d, r.rhr_ref, r.rhr_band_lo, r.rhr_band_hi, r.rhr_state,
                  r.rhr_days_out, r.sleep_debt_7d, r.sleep_debt_28d, r.sleep_cov_7d,
                  r.sleep_7d, r.sleep_ref, r.ln_rmssd_7d
           FROM daily_metrics m
           LEFT JOIN daily_recovery r USING (date_local)
           WHERE m.date_local >= (SELECT MAX(date_local) FROM daily_metrics) - INTERVAL (?) DAY
           ORDER BY m.date_local""",
        (dias_r,), M,
    )
    if dm.empty:
        st.info("Sin datos de monitoreo. Copia los archivos de Monitor/Sleep/HRVStatus "
                "del reloj a data/raw/monitoring/ y corre scripts/ingest.py.")
        st.stop()

    def _ultimo(col):
        s = dm.dropna(subset=[col])
        return None if s.empty else s.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    rhr = _ultimo("fc_reposo")
    if rhr is not None:
        estado_txt = {"sobre_banda": "⚠️ sobre tu banda", "bajo_banda": "🔵 bajo tu banda",
                      "dentro": "✅ dentro de tu banda"}.get(rhr.get("rhr_state"), "—")
        c1.metric("FC en reposo", f"{rhr.fc_reposo:.0f} ppm", estado_txt,
                  delta_color="off")
        c1.plotly_chart(
            viz.fig_bullet(rhr.fc_reposo, rhr.get("rhr_band_lo"), rhr.get("rhr_band_hi"),
                           rhr.get("rhr_ref"), "ppm", dark=OSCURO),
            width="stretch", config={"displayModeBar": False},
        )
    deuda = _ultimo("sleep_debt_7d")
    if deuda is not None:
        c2.metric("Deuda de sueño (7 días)", f"{deuda.sleep_debt_7d:.1f} h",
                  f"cobertura {deuda.sleep_cov_7d:.0f} %", delta_color="off")
    sue = _ultimo("sleep_h")
    if sue is not None:
        c3.metric("Último sueño", f"{sue.sleep_h:.1f} h"
                  + (f" · {sue.sleep_score:.0f} pts" if pd.notna(sue.get("sleep_score")) else ""))
    hrv = _ultimo("hrv_last_night")
    HRV_ES = {"balanced": "🟢 Equilibrado", "unbalanced": "🟡 Desequilibrado",
              "low": "🔴 Bajo", "poor": "🔴 Pobre", "none": "— Calibrando"}
    if hrv is not None:
        c4.metric("HRV última noche", f"{hrv.hrv_last_night:.0f} ms",
                  HRV_ES.get(str(hrv.get("hrv_status")), ""), delta_color="off")
    guia("kpis_recuperacion")

    # Eje de tiempo COMPARTIDO: donde un panel se ve vacío es porque el reloj no
    # retenía ese dato — el vacío también es información.
    rng = [pd.Timestamp(dm["date_local"].min()) - pd.Timedelta(days=1),
           pd.Timestamp(dm["date_local"].max()) + pd.Timedelta(days=1)]

    panel(viz.fig_serie_con_banda(dm, "fc_reposo", "rhr_band_lo", "rhr_band_hi",
                                  "FC en reposo y tu banda personal", "ppm",
                                  ref="rhr_ref", x_range=rng, dark=OSCURO),
          "banda_personal")

    if dm["sleep_debt_7d"].notna().any():
        panel(viz.fig_daily_line(dm, "sleep_debt_7d",
                                 "Deuda de sueño acumulada (7 días)", "horas",
                                 slot=1, x_range=rng, fmt=".1f"),
              "deuda_sueno")
    panel(viz.fig_sleep_stages(dm, x_range=rng), "sueno")
    panel(viz.fig_hrv(dm, x_range=rng), "hrv")

    panel(viz.fig_small_multiples(
        dm, [("stress_avg", "Estrés medio diario"),
             ("body_battery_max", "Body Battery máxima"),
             ("vo2max", "VO2max (medición Garmin)")],
        title="Otros marcadores (medición de Garmin, no propia)",
        x_range=rng, dark=OSCURO), "estres")

    st.caption(
        "Historial completo desde octubre 2023 gracias al export de cuenta (D-013). "
        "El HRV nocturno existe solo desde jul-2026 y necesita ~3 semanas más para que "
        "su tendencia sea legible. Donde un panel se ve vacío, ese dato no existía."
    )

# ========================================================== Vista: Registrar
elif page == "Registrar":
    st.title("Registrar")
    ad = wellness.adherencia(DB, dias=30)
    a1, a2, a3 = st.columns(3)
    a1.metric("Días registrados (30)", f"{ad.get('pct_dias_registrados', 0):.0f} %")
    a2.metric("Racha actual", f"{ad.get('racha_actual', 0)} días")
    seg = ad.get("mediana_segundos")
    a3.metric("Tiempo típico", "—" if not seg else f"{seg:.0f} s",
              help="El objetivo de diseño es menos de 30 segundos. Si esto sube, el "
                   "formulario está creciendo demasiado.")
    guia("adherencia")

    tab_sesion, tab_manana, tab_ostrc = st.tabs(
        ["Tras la sesión", "Al despertar (Hooper)", "Revisión semanal (OSTRC)"])

    # --- Post-sesión: dRPE + molestias por zona ---
    with tab_sesion:
        st.caption("Lo que el reloj no ve: cómo se sintió y dónde molesta.")
        guia("drpe")
        acts21 = q(
            """SELECT activity_id, CAST(date_local AS VARCHAR) AS f, sport,
                      ROUND(duration_s/60) AS mins
               FROM activities WHERE date_local >= current_date - INTERVAL 21 DAY
               ORDER BY start_time_utc DESC""", (), M,
        )
        opciones = ["— Registro general del día (sin sesión) —"] + [
            f"{r.f} · {viz.sport_display(r.sport)} · {r.mins:.0f} min"
            for r in acts21.itertuples()
        ]
        sel = st.selectbox("¿Qué registras?", opciones)
        idx = opciones.index(sel) - 1
        act_id = acts21.iloc[idx]["activity_id"] if idx >= 0 else None
        dur_def = int(acts21.iloc[idx]["mins"]) if idx >= 0 else 0
        fecha = (pd.Timestamp(acts21.iloc[idx]["f"]).date() if idx >= 0
                 else pd.Timestamp.today().date())

        r1, r2 = st.columns(2)
        rpe_breath = r1.slider("🫁 ¿Cuánto te costó respirar?", 0, 10, 5)
        r1.caption(getattr(wellness, "RPE_BREATH_TEXTO", ""))
        rpe_legs = r2.slider("🦵 ¿Cuánto te pesaron las piernas?", 0, 10, 5)
        r2.caption(getattr(wellness, "RPE_LEGS_TEXTO", ""))
        st.caption(wellness.RPE_ESCALA)
        dur = st.number_input("Duración (min)", 0, 600, dur_def,
                              help="Se toma de la actividad; edítala solo si registras sin reloj.")

        st.markdown("**Molestias por zona** (0 = nada · 4+ = relevante · 7+ = dolor serio)")
        dolores = {}
        zonas = list(wellness.ZONAS.items())
        for fila in (zonas[:4], zonas[4:]):
            cols = st.columns(len(fila))
            for c, (key, nombre) in zip(cols, fila):
                dolores[key] = c.slider(nombre, 0, 10, 0, key=f"z_{key}")
        nota = st.text_input("Nota (opcional)",
                             placeholder="ej. cancha sintética, molestia al rematar…")

        if st.button("💾 Guardar sesión", type="primary"):
            wellness.save_log(
                DB, date_local=fecha, activity_id=act_id,
                rpe=round((rpe_legs + rpe_breath) / 2), duration_min=dur,
                dolores=dolores, nota=nota,
                rpe_legs=rpe_legs, rpe_breath=rpe_breath,
            )
            st.cache_data.clear()
            st.success(
                f"Guardado para {fecha} — sRPE piernas {rpe_legs * dur}, "
                f"respiración {rpe_breath * dur}. Ya entra en las recomendaciones."
            )

    # --- Matinal: Hooper 4 ítems ---
    with tab_manana:
        st.caption("Cuatro preguntas al despertar, antes de saber qué toca entrenar.")
        st.warning(getattr(wellness, "HOOPER_AVISO_INVERSION",
                           "Ojo: en esta escala 7 es lo PEOR."))
        guia("hooper")
        hooper = {}
        items = list(getattr(wellness, "HOOPER_ITEMS", {}).items())
        if items:
            for fila in (items[:2], items[2:]):
                for c, (key, texto) in zip(st.columns(len(fila)), fila):
                    hooper[key] = c.select_slider(texto, options=list(range(1, 8)), value=4,
                                                  key=f"h_{key}")
            if st.button("💾 Guardar estado de la mañana", type="primary"):
                wellness.save_hooper(DB, date_local=pd.Timestamp.today().date(),
                                     hooper=hooper)
                st.cache_data.clear()
                st.success("Guardado. Con ~3 semanas de registros aparecerá tu línea "
                           "base y el dominio subjetivo en la vista Hoy.")
        hs = wellness.hooper_status(DB)
        if hs.get("items"):
            st.markdown(f"**Tu estado frente a tu propia base** ({hs.get('fecha')}):")
            for it in hs["items"]:
                z = it.get("z")
                st.write(f"- {it.get('nombre', it.get('clave'))}: **{it.get('valor')}/7**"
                         + (f" ({z:+.1f} DE)" if z is not None else " (base en formación)"))
            if not hs.get("base_lista"):
                st.caption(f"Tu línea base todavía se está formando "
                           f"({hs.get('obs_base', 0)} registros). Con ~3 semanas los "
                           "z-scores empiezan a significar algo.")
        else:
            st.info(hs.get("razon") or "Sin registro matinal reciente.")

    # --- Semanal: OSTRC condicional ---
    with tab_ostrc:
        st.caption("Solo se preguntan las zonas que vienen molestando. "
                   "Si no hay ninguna, esta pestaña queda vacía y está bien.")
        guia("ostrc")
        pendientes = wellness.zonas_a_preguntar(DB)
        if not pendientes:
            st.success("Ninguna zona superó el umbral esta semana: nada que responder.")
        else:
            preguntas = getattr(wellness, "OSTRC_PREGUNTAS", [])
            for z in pendientes:
                with st.form(f"ostrc_{z['zona']}"):
                    st.markdown(f"**{z['nombre']}** — molestia media {z['media']:.1f}/10 "
                                f"en {z['n_registros']} registros")
                    resp = {}
                    for p in preguntas:
                        etiquetas = [o[0] for o in p["opciones"]]
                        elegida = st.radio(p["texto"], etiquetas, key=f"{z['zona']}_{p['clave']}")
                        resp[p["clave"]] = dict(p["opciones"])[elegida]
                    if st.form_submit_button("Guardar respuesta"):
                        out = wellness.save_ostrc(DB, week_start=z["week_start"],
                                                  zone=z["zona"], **resp)
                        etiqueta = ("problema sustancial" if out["sustancial"]
                                    else "problema de salud" if out["problema_salud"]
                                    else "sin problema")
                        st.cache_data.clear()
                        st.success(f"Severidad {out['severity']}/100 — {etiqueta}")
        st.caption(getattr(wellness, "OSTRC_LIMITACION", ""))

    st.subheader("Últimos registros")
    logs = wellness.fetch_logs(DB, 15)
    if logs.empty:
        st.info("Aún no hay registros. El primero toma 30 segundos.")
    else:
        if "sport" in logs:
            logs["sport"] = logs["sport"].map(lambda s: viz.sport_display(s) if s else "General")
        st.dataframe(logs.rename(columns={"date_local": "fecha", "sport": "sesión",
                                          "duration_min": "min"}),
                     width="stretch", hide_index=True)

# =========================================================== Vista: Explorar
elif page == "Explorar":
    st.title("Explorar")
    st.caption(
        "Aquí viven los gráficos de exploración, incluidos los 3D. Regla del proyecto "
        "(D-019): **de estos gráficos no se leen valores** y ninguno alimenta las "
        "recomendaciones ni la tarjeta pre-partido. Para decidir, usa las otras vistas."
    )

    dias_e = selector_rango("rango_expl", index=2)
    cruce = q(
        """SELECT l.date_local, l.acwr, l.trimp, l.load_7d,
                  r.indice AS z_recup,
                  COALESCE(w.molestia, 0) AS molestia
           FROM daily_load l
           LEFT JOIN daily_readiness r USING (date_local)
           LEFT JOIN (
               SELECT date_local, GREATEST(
                   COALESCE(MAX(d_isquios),0), COALESCE(MAX(d_cuadriceps),0),
                   COALESCE(MAX(d_gemelos),0), COALESCE(MAX(d_aductores),0),
                   COALESCE(MAX(d_rodilla),0), COALESCE(MAX(d_tobillo),0),
                   COALESCE(MAX(d_espalda),0)) AS molestia
               FROM wellness_log GROUP BY date_local
           ) w USING (date_local)
           WHERE l.date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY
           ORDER BY l.date_local""",
        (dias_e,), M,
    )
    plano = pd.DataFrame({
        "x": cruce["acwr"], "y": cruce["z_recup"], "color": cruce["molestia"],
        "size": cruce["trimp"], "fecha": cruce["date_local"].astype(str),
    })
    panel(viz.fig_carga_vs_recuperacion(plano, dark=OSCURO), "carga_vs_recuperacion")

    panel(viz.fig_parcoords(
        cruce.rename(columns={"acwr": "carga", "z_recup": "recuperacion"}),
        [("carga", "Carga (ACWR)"), ("recuperacion", "Recuperación (DE)"),
         ("molestia", "Molestia")], dark=OSCURO), "coordenadas_paralelas")

    with st.expander("🎢 Ver en 3D (juguete de exploración)"):
        st.caption(
            "La evidencia le es adversa a este gráfico y aun así está aquí: girar tu "
            "propia nube de datos ayuda a formar intuición. Pero los valores se leen "
            "arriba — ver la guía."
        )
        tri = pd.DataFrame({
            "x": cruce["acwr"], "y": cruce["z_recup"], "z": cruce["molestia"],
            "fecha": cruce["date_local"].astype(str),
        })
        panel(viz.fig_scatter3d_exploracion(tri, dark=OSCURO), "exploracion_3d")

# =========================================================== Vista: Fórmulas
elif page == "Fórmulas":
    st.title("Formulario")
    st.caption(
        "Cada métrica del dashboard con la fórmula que el código ejecuta de verdad, "
        "la ruta al archivo donde vive, sus referencias primarias y sus limitaciones. "
        "Si alguna vez la ficha y el código se contradicen, eso es un bug (D-016)."
    )

    busca = st.text_input("Buscar métrica, autor o archivo",
                          placeholder="ej. sueño, Foster, ACWR, clean.py…")
    encontradas = formulas.buscar(busca)
    if busca:
        st.caption(f"{len(encontradas)} de {len(formulas.FORMULAS)} fichas coinciden.")

    claves = {f["clave"] for f in encontradas}
    for cat, titulo, subtitulo in formulas.CATEGORIAS:
        fichas = [f for f in formulas.por_categoria(cat) if f["clave"] in claves]
        if not fichas:
            continue
        st.header(titulo)
        st.caption(subtitulo)
        for f in fichas:
            with st.container(border=True):
                ficha_formula(f)
        st.divider()

    if not encontradas:
        st.info("Ninguna ficha coincide con esa búsqueda.")

# ================================================= Vista: Detalle de actividad
elif page == "Detalle de actividad":
    st.title("Detalle de actividad")

    acts = q(
        """SELECT activity_id, date_local, sport, sport_profile, duration_s, distance_m,
                  avg_hr, max_hr, trimp, hr_coverage, n_samples, avg_speed_ms
           FROM activities ORDER BY start_time_utc DESC""", (), M,
    )
    if acts.empty:
        st.info("Sin actividades cargadas.")
        st.stop()

    def label(r) -> str:
        dep = viz.sport_display(r.sport)
        extra = f" · {r.sport_profile}" if r.sport_profile and str(r.sport_profile) != dep else ""
        return f"{str(r.date_local)[:10]} · {dep}{extra} · {r.duration_s/60:.0f} min"

    acts["etiqueta"] = acts.apply(label, axis=1)
    sel = st.selectbox("Actividad", acts["etiqueta"])
    row = acts[acts["etiqueta"] == sel].iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Duración", f"{row.duration_s/60:.0f} min")
    c2.metric("Distancia", "—" if pd.isna(row.distance_m) else f"{row.distance_m/1000:.2f} km")
    c3.metric("FC media / máx", f"{row.avg_hr:.0f} / {row.max_hr:.0f}"
              if pd.notna(row.avg_hr) else "—")
    c4.metric("TRIMP", "—" if pd.isna(row.trimp) else f"{row.trimp:.0f}")
    c5.metric("Calidad FC", f"{row.hr_coverage*100:.0f} %")

    samples = q(
        """SELECT elapsed_s, hr, hr_valid, hr_flag, speed_ms, altitude_m, cadence_rpm,
                  lat, lon, distance_m
           FROM samples WHERE activity_id = ? ORDER BY elapsed_s""",
        (row.activity_id,), M,
    )
    if samples.empty:
        st.info("Esta actividad no tiene serie de muestras (archivo sin registros por segundo).")
    else:
        panel(viz.fig_activity_hr(samples), "fc_actividad")
        if (samples["speed_ms"].fillna(0) > 0).any():
            panel(viz.fig_activity_speed(samples, row.sport), "ritmo")
        else:
            st.caption("Sin datos de velocidad en esta actividad.")
        n_desc = int((~samples["hr_valid"].fillna(False)).sum())
        if n_desc:
            st.caption(f"{n_desc} muestras de FC descartadas por reglas D-008 "
                       "(marcadas, nunca borradas — el dato crudo sigue en la base).")

        zdf = q("SELECT zone, seconds FROM activity_zones WHERE activity_id = ? ORDER BY zone",
                (row.activity_id,), M)
        if not zdf.empty:
            panel(viz.fig_zone_bar(zdf), "zonas")

        # El 3D de la ruta: solo con relieve real. En una cancha plana sería ruido (D-019).
        alt = samples["altitude_m"].dropna()
        relieve = (alt.max() - alt.min()) if not alt.empty else 0
        tiene_gps = samples[["lat", "lon"]].notna().all(axis=1).any()
        if tiene_gps and relieve >= 50:
            st.subheader("Recorrido")
            st.caption(f"Desnivel de {relieve:.0f} m: el 3D aporta aquí porque el terreno "
                       "ES tridimensional. El perfil de abajo es el que se lee.")
            panel(viz.fig_route_3d(samples, dark=OSCURO), "ruta_3d")
            panel(viz.fig_elevation_profile(samples, dark=OSCURO))
        elif tiene_gps:
            st.caption(f"Desnivel de solo {relieve:.0f} m: no se dibuja la ruta en 3D "
                       "porque no aportaría nada sobre un plano (D-019).")

    laps = q(
        """SELECT lap_index AS vuelta, ROUND(duration_s/60,1) AS minutos,
                  ROUND(distance_m/1000,2) AS km, avg_hr AS fc_media, max_hr AS fc_max
           FROM laps WHERE activity_id = ? ORDER BY lap_index""",
        (row.activity_id,), M,
    )
    if len(laps) > 1:
        st.subheader("Parciales")
        st.dataframe(laps, width="stretch", hide_index=True)
