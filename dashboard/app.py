"""Dashboard v0 — Garmin FR255 (D-003).

Ejecutar desde la raíz del proyecto:
    streamlit run dashboard/app.py

Vistas: "Semana y carga" (semáforo de riesgo) y "Detalle de actividad".
Lee la base DuckDB en modo solo-lectura; la ingesta corre aparte (scripts/ingest.py).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from garmin import viz  # noqa: E402
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


if not DB.exists():
    st.error("No existe la base de datos. Ejecuta primero:  python scripts/ingest.py")
    st.stop()

M = mtime()
st.sidebar.title("Garmin FR255")
page = st.sidebar.radio("Vista", ["Semana y carga", "Detalle de actividad"])
st.sidebar.caption("Datos: DuckDB local · métricas propias (D-007). "
                   "La ingesta se corre con scripts/ingest.py.")

# ---------------------------------------------------------------- Semana y carga
if page == "Semana y carga":
    st.title("Semana y carga de entrenamiento")

    rango = st.radio(
        "Rango", ["90 días", "180 días", "1 año", "Todo"],
        horizontal=True, index=1, label_visibility="collapsed",
    )
    dias = {"90 días": 90, "180 días": 180, "1 año": 365, "Todo": 10000}[rango]

    daily = q(
        """SELECT date_local, trimp, n_activities, atl, ctl, tsb, acwr, risk
           FROM daily_load
           WHERE date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY
           ORDER BY date_local""",
        (dias,), M,
    )
    hoy = daily.iloc[-1] if not daily.empty else None

    c1, c2, c3, c4 = st.columns(4)
    if hoy is not None:
        c1.metric("Forma (CTL, crónica)", f"{hoy.ctl:.0f}")
        c2.metric("Fatiga (ATL, aguda)", f"{hoy.atl:.0f}")
        c3.metric("Balance (TSB)", f"{hoy.tsb:+.0f}")
        acwr_txt = "—" if pd.isna(hoy.acwr) else f"{hoy.acwr:.2f}"
        c4.metric("Riesgo (ACWR)", acwr_txt)
        c4.markdown(f"**{viz.STATUS_LABEL.get(hoy.risk)}**")
    st.caption(
        "ACWR = carga media 7 días / carga media 28 días. Zona óptima 0.8–1.3; "
        "sobre 1.5 el riesgo de lesión sube fuerte (D-006: prioridad prevención)."
    )

    st.plotly_chart(viz.fig_daily_load(daily), use_container_width=True)
    st.plotly_chart(viz.fig_acwr(daily), use_container_width=True)

    acts = q(
        """SELECT date_local, sport, trimp FROM activities
           WHERE trimp IS NOT NULL
             AND date_local >= (SELECT MAX(date_local) FROM daily_load) - INTERVAL (?) DAY""",
        (dias,), M,
    )
    st.plotly_chart(viz.fig_weekly_by_sport(acts), use_container_width=True)

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
    st.dataframe(last, use_container_width=True, hide_index=True)

# ---------------------------------------------------------- Detalle de actividad
else:
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
        """SELECT elapsed_s, hr, hr_valid, hr_flag, speed_ms, altitude_m, cadence_rpm
           FROM samples WHERE activity_id = ? ORDER BY elapsed_s""",
        (row.activity_id,), M,
    )
    if samples.empty:
        st.info("Esta actividad no tiene serie de muestras (archivo sin registros por segundo).")
    else:
        st.plotly_chart(viz.fig_activity_hr(samples), use_container_width=True)
        if (samples["speed_ms"].fillna(0) > 0).any():
            st.plotly_chart(viz.fig_activity_speed(samples, row.sport), use_container_width=True)
        else:
            st.caption("Sin datos de velocidad en esta actividad.")
        n_desc = int((~samples["hr_valid"].fillna(False)).sum())
        if n_desc:
            st.caption(f"{n_desc} muestras de FC descartadas por reglas D-008 "
                       "(marcadas, nunca borradas — el dato crudo sigue en la base).")

    laps = q(
        """SELECT lap_index AS vuelta, ROUND(duration_s/60,1) AS minutos,
                  ROUND(distance_m/1000,2) AS km, avg_hr AS fc_media, max_hr AS fc_max
           FROM laps WHERE activity_id = ? ORDER BY lap_index""",
        (row.activity_id,), M,
    )
    if len(laps) > 1:
        st.subheader("Parciales")
        st.dataframe(laps, use_container_width=True, hide_index=True)
