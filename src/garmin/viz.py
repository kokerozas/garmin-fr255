"""Figuras Plotly compartidas por el dashboard y los reportes.

Paleta y reglas según el sistema de visualización del proyecto:
- Color por entidad (cada deporte tiene SU color fijo, nunca se recicla).
- Un solo eje Y por gráfico. Leyenda visible cuando hay ≥2 series.
- Colores de estado reservados para el semáforo de riesgo (icono + texto, nunca solo color).
Paleta categórica validada (CVD-safe, adjacent pairs, light y dark).

LA REGLA DEL 3D (D-019). El 3D no está prohibido: está condicionado. Cleveland &
McGill (1984, JASA 79(387):531-554) ordenaron experimentalmente los canales
perceptuales — posición > longitud > ángulo > área > volumen — y el 3D empuja el
dato desde "posición" hacia "volumen y profundidad", además de añadir oclusión y
distorsión de perspectiva (Munzner 2014, cap. 6 "No Unjustified 3D"). Pero la
evidencia tiene matices: Zacks et al. (1998, J Exp Psychol Appl 4(2):119-138)
concluyen que las advertencias sobre las claves 3D "pueden estar exageradas"
frente al efecto del contexto gráfico, y St. John et al. (2001, Human Factors
43(1):79-98) mostraron que el 3D SÍ gana cuando la tarea es comprender una forma
tridimensional real. De ahí las tres líneas que rigen este módulo:
  1. dato abstracto (carga, HRV, molestias) → 2D siempre;
  2. dato intrínsecamente espacial (ruta con altitud) → 3D para entender la FORMA,
     nunca para leer valores, y siempre con su equivalente 2D al lado;
  3. todo 3D va rotulado como exploración y jamás alimenta las recomendaciones.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Tokens (modo claro) — valores validados CVD, NO cambiar ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# Modo oscuro: mismo papel, tinta invertida. Los SLOTS no cambian de matiz (siguen
# siendo los mismos colores validados), solo cambia el fondo sobre el que se leen.
_DARK = {
    "surface": "#14140f", "ink": "#f4f3ee", "ink_2": "#c3c2b7",
    "muted": "#898781", "grid": "#2e2d27", "baseline": "#52514e",
}
_LIGHT = {
    "surface": SURFACE, "ink": INK, "ink_2": INK_2,
    "muted": MUTED, "grid": GRID, "baseline": BASELINE,
}


def theme(dark: bool = False) -> dict:
    """Tokens de color del tema. El claro es el sistema validado; el oscuro lo espeja."""
    return dict(_DARK if dark else _LIGHT)

# Paleta categórica en orden fijo (slots 1-8, validada)
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Estado (semáforo ACWR) — reservados, jamás para series
STATUS = {"optima": "#0ca30c", "precaucion": "#fab219", "alta": "#d03b3b", "baja": "#898781"}
STATUS_LABEL = {
    "optima": "🟢 Óptima",
    "precaucion": "🟡 Precaución",
    "alta": "🔴 Alta",
    "baja": "⚪ Subcarga",
    None: "— Sin datos",
}

# Color por deporte: sigue a la ENTIDAD (orden fijo por volumen del histórico)
SPORT_ES = {
    "soccer": "Fútbol",
    "running": "Trote",
    "hiking": "Senderismo",
    "walking": "Caminata",
    "training": "Gimnasio",
    "alpine_skiing": "Esquí",
    "swimming": "Natación",
}
SPORT_COLORS = {
    "soccer": SLOTS[0],
    "running": SLOTS[1],
    "hiking": SLOTS[2],
    "walking": SLOTS[3],
    "training": SLOTS[4],
    "alpine_skiing": SLOTS[5],
    "swimming": SLOTS[6],
    "otros": SLOTS[7],
}


def sport_display(sport: str | None) -> str:
    return SPORT_ES.get(sport, "Otros" if sport else "Otros")


def sport_key(sport: str | None) -> str:
    return sport if sport in SPORT_COLORS else "otros"


def base_layout(fig: go.Figure, title: str | None = None, height: int = 340,
                dark: bool = False) -> go.Figure:
    t = theme(dark)
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  color=t["ink"], size=13),
        margin=dict(l=10, r=10, t=48 if title else 16, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    font=dict(color=t["ink_2"], size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=t["surface"], font=dict(color=t["ink"])),
    )
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["baseline"],
                     tickfont=dict(color=t["muted"]), zeroline=False)
    fig.update_yaxes(
        gridcolor=t["grid"], linecolor=t["baseline"], tickfont=dict(color=t["muted"]),
        zeroline=True, zerolinecolor=t["baseline"], zerolinewidth=1, rangemode="tozero",
    )
    return fig


def add_rangeselector(fig: go.Figure, slider: bool = True) -> go.Figure:
    """Botones 3m/6m/1a/todo + slider. Plotly ya lo traía; simplemente no se usaba."""
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1a", step="year", stepmode="backward"),
                dict(step="all", label="todo"),
            ],
            font=dict(size=11), bgcolor="rgba(0,0,0,0)", activecolor=SLOTS[0],
        ),
        rangeslider=dict(visible=slider, thickness=0.06),
    )
    return fig


def fig_daily_load(daily: pd.DataFrame, title="Carga diaria (TRIMP) y tendencias") -> go.Figure:
    """Barras de TRIMP diario + líneas ATL (aguda) y CTL (crónica). Mismo eje, mismas unidades."""
    fig = go.Figure()
    fig.add_bar(
        x=daily["date_local"], y=daily["trimp"], name="TRIMP día",
        marker_color=SLOTS[0], marker_line_width=0, opacity=0.55,
        hovertemplate="TRIMP %{y:.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=daily["date_local"], y=daily["atl"], name="Aguda (ATL, 7d)",
        line=dict(color=SLOTS[1], width=2), mode="lines",
        hovertemplate="ATL %{y:.1f}<extra></extra>",
    )
    fig.add_scatter(
        x=daily["date_local"], y=daily["ctl"], name="Crónica (CTL, 42d)",
        line=dict(color=SLOTS[2], width=2), mode="lines",
        hovertemplate="CTL %{y:.1f}<extra></extra>",
    )
    fig.update_yaxes(title_text="TRIMP / día", title_font=dict(color=MUTED, size=12))
    return base_layout(fig, title)


def fig_acwr(daily: pd.DataFrame, title="Ratio agudo:crónico (riesgo de lesión)") -> go.Figure:
    """Línea ACWR sobre bandas de riesgo (sombreado de estado, etiquetado)."""
    fig = go.Figure()
    x0, x1 = daily["date_local"].min(), daily["date_local"].max()
    bands = [
        (0.0, 0.8, STATUS["baja"], "subcarga"),
        (0.8, 1.3, STATUS["optima"], "óptima"),
        (1.3, 1.5, STATUS["precaucion"], "precaución"),
        (1.5, 2.2, STATUS["alta"], "alta"),
    ]
    for lo, hi, color, label in bands:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=color, opacity=0.10, line_width=0)
        fig.add_annotation(
            x=1.0, xref="paper", y=(lo + hi) / 2, text=label, showarrow=False,
            font=dict(color=INK_2, size=11), xanchor="right",
        )
    fig.add_scatter(
        x=daily["date_local"], y=daily["acwr"], name="ACWR",
        line=dict(color=SLOTS[0], width=2), mode="lines", connectgaps=False,
        hovertemplate="ACWR %{y:.2f}<extra></extra>",
    )
    fig.add_hline(y=1.0, line=dict(color=BASELINE, width=1, dash="dot"))
    fig.update_yaxes(range=[0, 2.2], title_text="agudo (7d) / crónico (28d)",
                     title_font=dict(color=MUTED, size=12))
    fig.update_layout(showlegend=False)  # una sola serie: el título la nombra
    return base_layout(fig, title)


def fig_weekly_by_sport(acts: pd.DataFrame, title="TRIMP semanal por deporte") -> go.Figure:
    """Barras apiladas por semana, color fijo por deporte, separador de 2px."""
    df = acts.dropna(subset=["trimp", "date_local"]).copy()
    df["date_local"] = pd.to_datetime(df["date_local"])
    df["semana"] = df["date_local"].dt.to_period("W").apply(lambda p: p.start_time)
    df["k"] = df["sport"].map(sport_key)
    weekly = df.groupby(["semana", "k"], as_index=False)["trimp"].sum()

    fig = go.Figure()
    order = [k for k in SPORT_COLORS if k in set(weekly["k"])]
    for k in order:
        d = weekly[weekly["k"] == k]
        fig.add_bar(
            x=d["semana"], y=d["trimp"],
            name=sport_display(k) if k != "otros" else "Otros",
            marker_color=SPORT_COLORS[k],
            marker_line=dict(color=SURFACE, width=2),  # espaciador entre segmentos
            hovertemplate="%{y:.0f}<extra>" + (sport_display(k) if k != "otros" else "Otros") + "</extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.35, legend_traceorder="normal")
    fig.update_yaxes(title_text="TRIMP / semana", title_font=dict(color=MUTED, size=12))
    return base_layout(fig, title)


# Etapas de sueño: rampa ordinal de un solo tono (profundo=oscuro) + gris para despierto
STAGE_COLORS = {"deep": "#1c5cab", "rem": "#2a78d6", "light": "#86b6ef", "awake": MUTED}
STAGE_ES = {"deep": "Profundo", "rem": "REM", "light": "Ligero", "awake": "Despierto"}

# Zonas Z1..Z5: rampa ordinal claro→oscuro (intensidad creciente)
ZONE_COLORS = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]


def fig_sleep_stages(dm: pd.DataFrame, title="Sueño por etapas (el puntaje va en el hover)",
                     x_range=None) -> go.Figure:
    d = dm.dropna(subset=["sleep_h"]).copy()
    # En rangos largos cada barra mide ~1 px: el separador blanco la taparía por
    # completo (bug visto con el histórico completo). Sin separador cuando es denso.
    dense = len(d) > 150
    fig = go.Figure()
    for key in ("deep", "rem", "light", "awake"):
        col = f"sleep_{key}_h"
        fig.add_bar(
            x=d["date_local"], y=d[col], name=STAGE_ES[key],
            marker_color=STAGE_COLORS[key],
            marker_line=dict(color=SURFACE, width=0 if dense else 1),
            customdata=d[["sleep_score"]],
            hovertemplate="%{y:.1f} h · puntaje %{customdata[0]}<extra>" + STAGE_ES[key] + "</extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.05 if dense else 0.3,
                      legend_traceorder="normal")
    fig.update_yaxes(title_text="horas", title_font=dict(color=MUTED, size=12))
    fig = base_layout(fig, title, height=280)
    if x_range is not None:
        fig.update_xaxes(range=x_range)
    return fig


def fig_hrv(dm: pd.DataFrame, title="HRV nocturno (RMSSD) vs tu banda personal",
            x_range=None) -> go.Figure:
    d = dm.dropna(subset=["hrv_last_night"]).copy()
    fig = go.Figure()
    if not d.empty:
        lo = d["hrv_baseline_lower"].dropna()
        hi = d["hrv_baseline_upper"].dropna()
        if not lo.empty and not hi.empty:
            fig.add_hrect(
                y0=float(lo.iloc[-1]), y1=float(hi.iloc[-1]),
                fillcolor=STATUS["optima"], opacity=0.10, line_width=0,
                annotation_text="banda equilibrada", annotation_position="top right",
                annotation_font=dict(color=INK_2, size=11),
            )
        fig.add_scatter(
            x=d["date_local"], y=d["hrv_last_night"], name="HRV",
            mode="lines+markers", line=dict(color=SLOTS[0], width=2),
            marker=dict(size=8), customdata=d[["hrv_status"]],
            hovertemplate="%{y:.0f} ms · %{customdata[0]}<extra></extra>",
        )
    fig.update_yaxes(title_text="ms", title_font=dict(color=MUTED, size=12), rangemode="normal")
    fig.update_layout(showlegend=False)
    fig = base_layout(fig, title, height=260)
    if x_range is not None:
        fig.update_xaxes(range=x_range)
    return fig


def fig_daily_line(dm: pd.DataFrame, col: str, title: str, unit: str, slot: int = 0,
                   x_range=None, fmt: str = ".0f") -> go.Figure:
    d = dm.dropna(subset=[col])
    fig = go.Figure()
    fig.add_scatter(
        x=d["date_local"], y=d[col], mode="lines+markers",
        line=dict(color=SLOTS[slot], width=2), marker=dict(size=6),
        hovertemplate="%{y:" + fmt + "} " + unit + "<extra></extra>",
    )
    fig.update_yaxes(title_text=unit, title_font=dict(color=MUTED, size=12), rangemode="normal")
    fig.update_layout(showlegend=False)
    fig = base_layout(fig, title, height=240)
    if x_range is not None:
        fig.update_xaxes(range=x_range)
    return fig


def fig_zone_bar(zones: pd.DataFrame, title="Tiempo en zona (según tu FCmax)") -> go.Figure:
    """zones: columnas zone (1..5), seconds. Barras ordinales con etiqueta directa."""
    base = pd.DataFrame({"zone": [1, 2, 3, 4, 5]})
    d = base.merge(zones, on="zone", how="left").fillna({"seconds": 0.0})
    mins = d["seconds"] / 60.0
    fig = go.Figure(
        go.Bar(
            x=[f"Z{int(z)}" for z in d["zone"]], y=mins,
            marker_color=ZONE_COLORS, marker_line_width=0,
            text=[f"{m:.0f}′" if m >= 1 else "" for m in mins],
            textposition="outside", textfont=dict(color=INK_2, size=12),
            hovertemplate="%{y:.1f} min<extra>%{x}</extra>",
        )
    )
    fig.update_yaxes(title_text="minutos", title_font=dict(color=MUTED, size=12))
    fig.update_layout(showlegend=False)
    return base_layout(fig, title, height=260)


def fig_activity_hr(samples: pd.DataFrame, title="Frecuencia cardíaca") -> go.Figure:
    """Curva de FC: muestras válidas en línea; artefactos marcados en gris."""
    fig = go.Figure()
    valid = samples[samples["hr_valid"] == True]  # noqa: E712
    bad = samples[(samples["hr_valid"] == False) & samples["hr"].notna()]  # noqa: E712
    fig.add_scatter(
        x=valid["elapsed_s"] / 60.0, y=valid["hr"], name="FC válida",
        line=dict(color=SLOTS[0], width=2), mode="lines",
        hovertemplate="min %{x:.1f} · %{y:.0f} ppm<extra></extra>",
    )
    if not bad.empty:
        fig.add_scatter(
            x=bad["elapsed_s"] / 60.0, y=bad["hr"], name="Descartada (D-008)",
            mode="markers", marker=dict(color=MUTED, size=5, symbol="x"),
            hovertemplate="min %{x:.1f} · %{y:.0f} ppm (descartada)<extra></extra>",
        )
    fig.update_xaxes(title_text="minutos", title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(title_text="ppm", title_font=dict(color=MUTED, size=12), rangemode="normal")
    if bad.empty:
        fig.update_layout(showlegend=False)
    return base_layout(fig, title, height=300)


def fig_activity_speed(samples: pd.DataFrame, sport: str | None, title=None) -> go.Figure:
    """Ritmo (min/km, eje invertido) para trote/caminata; velocidad (km/h) para el resto."""
    s = samples[samples["speed_ms"].notna() & (samples["speed_ms"] > 0)]
    fig = go.Figure()
    as_pace = sport in ("running", "walking", "hiking")
    if as_pace:
        y = 1000.0 / s["speed_ms"] / 60.0  # min/km
        y = y.where(y < 20)  # ritmos absurdos fuera de escala → hueco
        fig.add_scatter(
            x=s["elapsed_s"] / 60.0, y=y, name="Ritmo",
            line=dict(color=SLOTS[1], width=2), mode="lines", connectgaps=False,
            hovertemplate="min %{x:.1f} · %{y:.2f} min/km<extra></extra>",
        )
        fig.update_yaxes(autorange="reversed", title_text="min/km", rangemode="normal",
                         title_font=dict(color=MUTED, size=12))
        title = title or "Ritmo"
    else:
        fig.add_scatter(
            x=s["elapsed_s"] / 60.0, y=s["speed_ms"] * 3.6, name="Velocidad",
            line=dict(color=SLOTS[1], width=2), mode="lines",
            hovertemplate="min %{x:.1f} · %{y:.1f} km/h<extra></extra>",
        )
        fig.update_yaxes(title_text="km/h", title_font=dict(color=MUTED, size=12))
        title = title or "Velocidad"
    fig.update_xaxes(title_text="minutos", title_font=dict(color=MUTED, size=12))
    fig.update_layout(showlegend=False)
    return base_layout(fig, title, height=300)


# =============================================================================
# Figuras nuevas (D-019). Cada una declara en su docstring por qué esa forma
# y no otra: la elección de gráfico es una decisión con literatura, no un gusto.
# =============================================================================

# Rampa secuencial derivada del azul del sistema (mismo matiz, luminancia creciente).
# Secuencial = para magnitudes ordenadas; jamás usar la categórica para eso.
RAMPA_AZUL = [[0.0, "#eef4fc"], [0.25, "#b8d3f4"], [0.5, "#6ba3e6"],
              [0.75, "#2a78d6"], [1.0, "#104281"]]
# Rampa para "cuánto duele": del neutro al rojo de estado. Aquí el color codifica
# severidad, que sí es ordinal, así que la rampa es legítima.
RAMPA_DOLOR = [[0.0, "#e8e7e0"], [0.4, "#fab219"], [1.0, "#d03b3b"]]

DIAS_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def fig_calendar_load(daily: pd.DataFrame, title="Calendario de carga (TRIMP por día)",
                      dark: bool = False) -> go.Figure:
    """Heatmap día-de-semana × semana. La alternativa CORRECTA a la superficie 3D.

    La carga en el tiempo es univariada: dibujarla como superficie obliga a inventar
    un segundo eje y paga oclusión y distorsión de perspectiva a cambio de nada. El
    calendario codifica las mismas tres variables (día, semana, carga) con ambas
    dimensiones temporales en POSICIÓN y solo la magnitud en color.
    Ref: van Wijk & van Selow (1999), IEEE InfoVis '99, 4-9.
    """
    t = theme(dark)
    fig = go.Figure()
    d = daily.dropna(subset=["trimp"]).copy() if (daily is not None and not daily.empty) else pd.DataFrame()
    if not d.empty:
        d["fecha"] = pd.to_datetime(d["date_local"])
        d["dow"] = d["fecha"].dt.weekday                       # 0 = lunes
        d["semana"] = d["fecha"] - pd.to_timedelta(d["dow"], unit="D")
        pivot = d.pivot_table(index="dow", columns="semana", values="trimp", aggfunc="sum")
        pivot = pivot.reindex(range(7))
        textos = [[f"{c:%d-%m-%Y}" for c in pivot.columns] for _ in range(7)]
        fig.add_heatmap(
            x=pivot.columns, y=[DIAS_ES[i] for i in pivot.index], z=pivot.values,
            colorscale=RAMPA_AZUL, customdata=textos,
            hovertemplate="%{customdata} · %{z:.0f} TRIMP<extra></extra>",
            colorbar=dict(title=dict(text="TRIMP", font=dict(size=11)),
                          tickfont=dict(size=10), thickness=12),
            xgap=2, ygap=2,
        )
    fig.update_yaxes(autorange="reversed", rangemode="normal", showgrid=False)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(showlegend=False)
    fig = base_layout(fig, title, height=260, dark=dark)
    fig.update_layout(hovermode="closest")
    return fig


def fig_serie_con_banda(df: pd.DataFrame, col: str, lo: str, hi: str, title: str,
                        unit: str, slot: int = 0, ref: str | None = None,
                        invertido: bool = False, x_range=None,
                        fmt: str = ".0f", dark: bool = False) -> go.Figure:
    """Serie diaria sobre su BANDA DE REFERENCIA PERSONAL (media móvil ± SWC).

    Es el patrón visual central del monitoreo de una sola persona: no existe un
    umbral universal, existe TU banda. Los puntos fuera de banda se marcan además
    con forma distinta, nunca solo con color.
    Ref: Hopkins (2000), Sports Medicine 30(1):1-15 (SWC = 0.5·DE);
         Thornton et al. (2019), IJSPP 14(6):698-705 (visualización de monitoreo).
    """
    t = theme(dark)
    fig = go.Figure()
    d = df.dropna(subset=[col]).copy() if (df is not None and not df.empty and col in df) else pd.DataFrame()
    if not d.empty:
        banda = d.dropna(subset=[lo, hi]) if (lo in d and hi in d) else pd.DataFrame()
        if not banda.empty:
            fig.add_scatter(x=banda["date_local"], y=banda[hi], mode="lines",
                            line=dict(width=0), showlegend=False, hoverinfo="skip")
            fig.add_scatter(
                x=banda["date_local"], y=banda[lo], mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor="rgba(42,120,214,0.13)",
                name="tu banda habitual", hoverinfo="skip",
            )
        if ref and ref in d:
            fig.add_scatter(x=d["date_local"], y=d[ref], mode="lines", name="tu referencia",
                            line=dict(color=t["baseline"], width=1.5, dash="dot"),
                            hovertemplate="ref %{y:" + fmt + "}<extra></extra>")
        fig.add_scatter(
            x=d["date_local"], y=d[col], mode="lines+markers", name=title,
            line=dict(color=SLOTS[slot], width=2), marker=dict(size=5),
            hovertemplate="%{y:" + fmt + "} " + unit + "<extra></extra>",
        )
        if not banda.empty:
            fuera = d[d[col] < d[lo]] if invertido else d[d[col] > d[hi]]
            if not fuera.empty:
                fig.add_scatter(
                    x=fuera["date_local"], y=fuera[col], mode="markers",
                    name="fuera de tu banda",
                    marker=dict(color=STATUS["precaucion"], size=10, symbol="diamond",
                                line=dict(color=t["surface"], width=1)),
                    hovertemplate="%{y:" + fmt + "} " + unit + " · fuera de banda<extra></extra>",
                )
    fig.update_yaxes(title_text=unit, title_font=dict(color=t["muted"], size=12),
                     rangemode="normal")
    fig = base_layout(fig, title, height=280, dark=dark)
    if x_range is not None:
        fig.update_xaxes(range=x_range)
    return fig


def fig_carga_absoluta(daily: pd.DataFrame,
                       title="Carga de la semana (absoluta) y tu percentil",
                       dark: bool = False) -> go.Figure:
    """Carga aguda ABSOLUTA de 7 días + su percentil personal, en dos paneles.

    Reemplaza al ACWR como gráfico principal de carga. Impellizzeri et al. (2021,
    Sports Medicine 51(3):581-592) sustituyeron la carga crónica por valores
    ALEATORIOS y el ACWR siguió asociándose con lesión igual de bien: la señal
    estaba en el numerador (la carga aguda), no en el cociente. El percentil traduce
    "412 TRIMP" a "más alto que el 88 % de tus semanas", interpretable sin importar
    umbrales de otras poblaciones.
    Van en subplots separados, no superpuestos, porque son unidades distintas
    (TRIMP y percentil): la regla de un solo eje Y por panel se mantiene.
    """
    t = theme(dark)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        row_heights=[0.62, 0.38])
    d = daily.copy() if daily is not None else pd.DataFrame()
    if not d.empty and "load_7d" in d:
        fig.add_scatter(
            x=d["date_local"], y=d["load_7d"], name="Carga 7 días",
            mode="lines", line=dict(color=SLOTS[0], width=2),
            fill="tozeroy", fillcolor="rgba(42,120,214,0.15)",
            hovertemplate="%{y:.0f} TRIMP en 7 días<extra></extra>", row=1, col=1,
        )
        if "load_28d" in d:
            fig.add_scatter(
                x=d["date_local"], y=d["load_28d"] / 4.0, name="Tu base (28d ÷ 4)",
                mode="lines", line=dict(color=SLOTS[2], width=2, dash="dot"),
                hovertemplate="base %{y:.0f}<extra></extra>", row=1, col=1,
            )
        if "load_7d_pct" in d:
            pct = d.dropna(subset=["load_7d_pct"])
            if not pct.empty:
                fig.add_scatter(
                    x=pct["date_local"], y=pct["load_7d_pct"] * 100,
                    name="Percentil personal", mode="lines",
                    line=dict(color=SLOTS[3], width=2),
                    hovertemplate="percentil %{y:.0f}<extra></extra>", row=2, col=1,
                )
                for y, txt in ((50, "mediana"), (90, "top 10 % de tus semanas")):
                    fig.add_hline(y=y, line=dict(color=t["baseline"], width=1, dash="dot"),
                                  annotation_text=txt, annotation_position="right",
                                  annotation_font=dict(color=t["muted"], size=10),
                                  row=2, col=1)
    fig.update_yaxes(title_text="TRIMP / 7 días",
                     title_font=dict(color=t["muted"], size=12), row=1, col=1)
    fig.update_yaxes(title_text="percentil", range=[0, 100], rangemode="normal",
                     title_font=dict(color=t["muted"], size=12), row=2, col=1)
    fig = base_layout(fig, title, height=420, dark=dark)
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["baseline"],
                     tickfont=dict(color=t["muted"]))
    return fig


def fig_molestias_dumbbell(zonas, title="Molestias por zona: hoy vs tu promedio de 28 días",
                           dark: bool = False) -> go.Figure:
    """Dot plot ordenado (dumbbell). SUSTITUYE al gráfico de radar, a propósito.

    El radar es tentador para 7 zonas del cuerpo, pero: el ojo compara mal longitudes
    orientadas en ángulos distintos; el ORDEN de los ejes es arbitrario y cambiarlo
    produce otra figura con los mismos datos; y el área del polígono crece con el
    CUADRADO del valor, así que duplicar una molestia cuadruplica la impresión visual.
    El dot plot usa posición sobre escala común —el peldaño más alto de la jerarquía
    perceptual— y además muestra el CAMBIO respecto a la base personal.
    Ref: Few (2005) "Keep radar graphs below the radar"; Cleveland & McGill (1984),
         JASA 79(387):531-554.

    zonas: lista de dicts {zona, actual, promedio}.
    """
    t = theme(dark)
    fig = go.Figure()
    d = sorted(zonas or [], key=lambda z: z.get("actual") or 0)
    if d:
        nombres = [z["zona"] for z in d]
        actual = [z.get("actual") or 0 for z in d]
        prom = [z.get("promedio") or 0 for z in d]
        for n, a, p in zip(nombres, actual, prom):
            fig.add_scatter(x=[p, a], y=[n, n], mode="lines",
                            line=dict(color=t["baseline"], width=2),
                            showlegend=False, hoverinfo="skip")
        fig.add_scatter(
            x=prom, y=nombres, mode="markers", name="promedio 28 días",
            marker=dict(color=t["muted"], size=10, symbol="circle-open",
                        line=dict(width=2)),
            hovertemplate="%{x:.1f}/10 de promedio<extra>%{y}</extra>",
        )
        colores = [STATUS["alta"] if a >= 7 else STATUS["precaucion"] if a >= 4
                   else STATUS["optima"] for a in actual]
        fig.add_scatter(
            x=actual, y=nombres, mode="markers+text", name="hoy",
            marker=dict(color=colores, size=15,
                        line=dict(color=t["surface"], width=1.5)),
            text=[f"{a:.0f}" if a else "" for a in actual],
            textposition="middle right", textfont=dict(color=t["ink_2"], size=11),
            hovertemplate="%{x:.0f}/10 hoy<extra>%{y}</extra>",
        )
    fig.update_xaxes(range=[-0.4, 11], title_text="molestia 0-10",
                     title_font=dict(color=t["muted"], size=12))
    fig.update_yaxes(rangemode="normal", showgrid=False)
    fig = base_layout(fig, title, height=300, dark=dark)
    fig.update_layout(hovermode="closest")
    return fig


def fig_carga_vs_recuperacion(df: pd.DataFrame,
                              title="Carga vs recuperación (cada punto es un día)",
                              dark: bool = False) -> go.Figure:
    """Scatter 2D con 4 variables: la alternativa HONESTA al scatter 3D rotable.

    Las dos variables más importantes van en POSICIÓN (x = carga, y = recuperación);
    la molestia va en color (ordinal) y el volumen del día en tamaño. Sedlmair,
    Munzner & Tory (2013, IEEE TVCG 19(12):2634-2643) compararon 816 scatterplots y
    concluyeron que el 3D interactivo "rara vez ayuda y a menudo perjudica": en 3D no
    hay línea de referencia entre el punto y el eje, así que la profundidad no se lee,
    hay que rotar, y al rotar se pierde el estado mental anterior.
    El cuadrante peligroso (carga alta + recuperación baja) queda abajo a la derecha.

    df: columnas x, y y opcionalmente color, size, fecha.
    """
    t = theme(dark)
    fig = go.Figure()
    d = df.dropna(subset=["x", "y"]).copy() if (df is not None and not df.empty) else pd.DataFrame()
    if not d.empty:
        fig.add_vrect(x0=0.8, x1=1.3, fillcolor=STATUS["optima"], opacity=0.08, line_width=0,
                      annotation_text="carga en tu banda óptima",
                      annotation_position="top left",
                      annotation_font=dict(color=t["muted"], size=10))
        fig.add_hline(y=0, line=dict(color=t["baseline"], width=1, dash="dot"),
                      annotation_text="tu recuperación normal", annotation_position="right",
                      annotation_font=dict(color=t["muted"], size=10))
        tam = d["size"].fillna(0) if "size" in d else pd.Series([10.0] * len(d), index=d.index)
        mx = tam.max()
        tam = 8 + 22 * (tam / mx if (mx and mx > 0) else 0)
        color = d["color"].fillna(0) if "color" in d else pd.Series([0] * len(d), index=d.index)
        tiene_fecha = "fecha" in d
        fig.add_scatter(
            x=d["x"], y=d["y"], mode="markers",
            marker=dict(size=tam, color=color, colorscale=RAMPA_DOLOR, cmin=0, cmax=10,
                        showscale=True, opacity=0.75,
                        line=dict(color=t["surface"], width=1),
                        colorbar=dict(title=dict(text="molestia", font=dict(size=11)),
                                      tickfont=dict(size=10), thickness=12)),
            customdata=d[["fecha"]] if tiene_fecha else None,
            hovertemplate=("%{customdata[0]}<br>carga %{x:.2f} · recuperación %{y:+.2f} DE"
                           "<extra></extra>") if tiene_fecha else
                          "carga %{x:.2f} · recuperación %{y:+.2f} DE<extra></extra>",
        )
    fig.update_xaxes(title_text="carga relativa (ACWR)",
                     title_font=dict(color=t["muted"], size=12), rangemode="normal")
    fig.update_yaxes(title_text="recuperación (desviaciones de tu normal)",
                     title_font=dict(color=t["muted"], size=12), rangemode="normal")
    fig.update_layout(showlegend=False)
    fig = base_layout(fig, title, height=420, dark=dark)
    fig.update_layout(hovermode="closest")
    return fig


def fig_sparkline(serie, color_slot: int = 0, dark: bool = False) -> go.Figure:
    """Micro-serie sin ejes para incrustar en una tarjeta: la forma, no los valores.

    Ref: Tufte (2006), Beautiful Evidence — sparklines como "gráficos del tamaño de
    una palabra". Pensado para la tarjeta pre-partido, que debe leerse en 5 segundos.
    """
    s = pd.Series(serie).dropna()
    fig = go.Figure()
    if not s.empty:
        fig.add_scatter(y=s.values, mode="lines",
                        line=dict(color=SLOTS[color_slot], width=2), hoverinfo="skip")
        fig.add_scatter(y=[s.values[-1]], x=[len(s) - 1], mode="markers",
                        marker=dict(color=SLOTS[color_slot], size=7), hoverinfo="skip")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, rangemode="normal")
    fig.update_layout(
        height=52, margin=dict(l=0, r=0, t=4, b=4), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def fig_bullet(valor, lo, hi, ref, unit: str = "", dark: bool = False) -> go.Figure:
    """Bullet graph: el valor de hoy contra su banda personal, en una sola línea.

    Ref: Few (2006), Information Dashboard Design — sustituye a los medidores tipo
    velocímetro, que gastan mucho espacio para mostrar un número.
    """
    t = theme(dark)
    fig = go.Figure()
    vacio = valor is None or (isinstance(valor, float) and np.isnan(valor))
    if vacio:
        fig.update_layout(height=64, margin=dict(l=0, r=0, t=4, b=4), showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig
    ejes = [float(v) for v in (valor, lo, hi, ref) if v is not None and not pd.isna(v)]
    span = (max(ejes) - min(ejes)) if len(ejes) > 1 else (abs(float(valor)) or 1.0)
    span = span or 1.0
    x0, x1 = min(ejes) - 0.35 * span, max(ejes) + 0.35 * span
    if lo is not None and hi is not None and not pd.isna(lo) and not pd.isna(hi):
        fig.add_shape(type="rect", x0=lo, x1=hi, y0=0.28, y1=0.72,
                      fillcolor="rgba(42,120,214,0.18)", line_width=0)
    if ref is not None and not pd.isna(ref):
        fig.add_shape(type="line", x0=ref, x1=ref, y0=0.2, y1=0.8,
                      line=dict(color=t["baseline"], width=2, dash="dot"))
    fuera = (hi is not None and not pd.isna(hi) and valor > hi) or \
            (lo is not None and not pd.isna(lo) and valor < lo)
    fig.add_shape(type="line", x0=x0, x1=valor, y0=0.5, y1=0.5,
                  line=dict(color=SLOTS[0], width=6))
    fig.add_scatter(
        x=[valor], y=[0.5], mode="markers+text",
        marker=dict(color=STATUS["precaucion"] if fuera else SLOTS[0], size=14,
                    line=dict(color=t["surface"], width=1.5)),
        text=[f"  {valor:.1f} {unit}"], textposition="middle right",
        textfont=dict(color=t["ink"], size=13), hoverinfo="skip",
    )
    fig.update_xaxes(range=[x0, x1], visible=False)
    fig.update_yaxes(range=[0, 1], visible=False)
    fig.update_layout(height=64, margin=dict(l=0, r=0, t=4, b=4), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def fig_small_multiples(dm: pd.DataFrame, cols, title="Panel de recuperación",
                        x_range=None, dark: bool = False) -> go.Figure:
    """Rejilla de mini-series con eje X compartido (small multiples / trellis).

    Cuando hay que comparar la FORMA de varias series, apilarlas en un solo gráfico
    las hace competir por el eje; separarlas en paneles alineados deja que el ojo
    compare posiciones sobre la misma escala temporal.
    Ref: Tufte (1983/2001); Buchheit (2017) "Want to see my report, coach?", IJSPP.

    cols: lista de tuplas (columna, etiqueta).
    """
    t = theme(dark)
    cols = [c for c in (cols or [])
            if dm is not None and not dm.empty and c[0] in dm.columns]
    if not cols:
        return base_layout(go.Figure(), title, height=200, dark=dark)
    fig = make_subplots(rows=len(cols), cols=1, shared_xaxes=True,
                        vertical_spacing=0.05, subplot_titles=[c[1] for c in cols])
    for i, (col, _lab) in enumerate(cols, start=1):
        d = dm.dropna(subset=[col])
        fig.add_scatter(
            x=d["date_local"], y=d[col], mode="lines",
            line=dict(color=SLOTS[(i - 1) % len(SLOTS)], width=2),
            showlegend=False, hovertemplate="%{y:.1f}<extra></extra>", row=i, col=1,
        )
        fig.update_yaxes(rangemode="normal", row=i, col=1)
    fig = base_layout(fig, title, height=120 * len(cols) + 60, dark=dark)
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["baseline"],
                     tickfont=dict(color=t["muted"]))
    for ann in fig.layout.annotations:
        ann.font = dict(size=12, color=t["ink_2"])
    if x_range is not None:
        fig.update_xaxes(range=x_range)
    return fig


def fig_decoupling(df: pd.DataFrame,
                   title="Fatiga intra-partido: coste cardíaco 2ª vs 1ª mitad",
                   dark: bool = False) -> go.Figure:
    """Serie del decoupling por partido con banda de ±1 DE personal.

    Positivo = la segunda mitad te costó más pulso por cada metro recorrido: firma de
    fatiga acumulada dentro del partido, que es el tramo donde se concentran las
    lesiones musculares. Se lee como serie contra sí misma, nunca como valor absoluto.
    Ref: Mohr, Krustrup & Bangsbo (2003), Journal of Sports Sciences 21(7):519-528.
    """
    t = theme(dark)
    fig = go.Figure()
    d = (df.dropna(subset=["decoupling_pct"]).copy()
         if (df is not None and not df.empty and "decoupling_pct" in df) else pd.DataFrame())
    if not d.empty:
        m, s = d["decoupling_pct"].mean(), d["decoupling_pct"].std()
        if pd.notna(s) and s > 0:
            fig.add_hrect(y0=m - s, y1=m + s, fillcolor="rgba(42,120,214,0.10)", line_width=0,
                          annotation_text="tu rango habitual", annotation_position="top left",
                          annotation_font=dict(color=t["muted"], size=10))
        fig.add_hline(y=0, line=dict(color=t["baseline"], width=1, dash="dot"))
        fig.add_scatter(
            x=d["date_local"], y=d["decoupling_pct"], mode="lines+markers",
            name="decoupling", line=dict(color=SLOTS[0], width=2), marker=dict(size=7),
            hovertemplate="%{y:+.1f} %<extra></extra>",
        )
    fig.update_yaxes(title_text="% más de coste en la 2ª mitad", rangemode="normal",
                     title_font=dict(color=t["muted"], size=12))
    fig.update_layout(showlegend=False)
    return base_layout(fig, title, height=300, dark=dark)


# ----------------------------------------------------------------- El 3D (D-019)

def fig_route_3d(samples: pd.DataFrame, color_by: str = "hr",
                 title="Recorrido en 3D (color = pulso)", dark: bool = False) -> go.Figure:
    """EL ÚNICO 3D PLENAMENTE JUSTIFICADO: la ruta es espacial de verdad.

    Munzner no prohíbe el 3D: prohíbe el 3D INJUSTIFICADO, y define la justificación
    como que el dato sea intrínsecamente tridimensional. Latitud, longitud y altitud
    lo son — no es una codificación inventada. St. John et al. (2001, Human Factors
    43(1):79-98), con seis experimentos sobre terreno natural, mostraron que el 3D SÍ
    supera al 2D cuando la tarea es comprender la FORMA de algo tridimensional, y que
    el 2D gana para juzgar posiciones o distancias exactas: justo la división que se
    aplica aquí. Por eso este gráfico se MIRA y el perfil 2D de al lado se LEE.

    aspectmode='data' es obligatorio: si el eje Z se autoescalara, una loma de 40 m
    parecería el Everest.
    """
    t = theme(dark)
    fig = go.Figure()
    tiene = (samples is not None and not samples.empty
             and {"lat", "lon", "altitude_m"} <= set(samples.columns))
    d = samples.dropna(subset=["lat", "lon", "altitude_m"]).copy() if tiene else pd.DataFrame()
    if not d.empty:
        c = d[color_by] if color_by in d else None
        fig.add_scatter3d(
            x=d["lon"], y=d["lat"], z=d["altitude_m"], mode="lines",
            line=dict(color=c if c is not None else SLOTS[0], colorscale="Cividis",
                      width=5, showscale=c is not None,
                      colorbar=dict(title=dict(text="ppm", font=dict(size=11)),
                                    tickfont=dict(size=10), thickness=12)),
            hovertemplate="alt %{z:.0f} m<extra></extra>", name="recorrido",
        )
    fig.update_layout(
        title=title, height=460, showlegend=False,
        paper_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  color=t["ink"], size=13),
        margin=dict(l=0, r=0, t=48, b=0),
        scene=dict(
            aspectmode="data",              # no exagerar el relieve
            xaxis=dict(title="longitud", backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
            yaxis=dict(title="latitud", backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
            zaxis=dict(title="altitud (m)", backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
        ),
    )
    return fig


def fig_elevation_profile(samples: pd.DataFrame,
                          title="Perfil de altitud (este es el que se lee)",
                          dark: bool = False) -> go.Figure:
    """El gráfico 2D DE LECTURA que acompaña siempre a la ruta 3D.

    Altitud contra distancia, con el pulso como color. Aquí sí se pueden leer valores:
    ambas variables están en posición sobre escala común.
    """
    t = theme(dark)
    fig = go.Figure()
    tiene = (samples is not None and not samples.empty and "altitude_m" in samples.columns)
    d = samples.dropna(subset=["altitude_m"]).copy() if tiene else pd.DataFrame()
    if not d.empty:
        con_dist = "distance_m" in d and d["distance_m"].notna().any()
        x = d["distance_m"] / 1000.0 if con_dist else d["elapsed_s"] / 60.0
        xlab = "km" if con_dist else "minutos"
        fig.add_scatter(
            x=x, y=d["altitude_m"], mode="lines", name="altitud",
            line=dict(color=SLOTS[2], width=2), fill="tozeroy",
            fillcolor="rgba(27,175,122,0.15)",
            hovertemplate="%{y:.0f} m<extra></extra>",
        )
        if "hr" in d and d["hr"].notna().any():
            fig.add_scatter(
                x=x, y=d["altitude_m"], mode="markers", name="pulso",
                marker=dict(size=4, color=d["hr"], colorscale="Cividis", showscale=True,
                            colorbar=dict(title=dict(text="ppm", font=dict(size=11)),
                                          tickfont=dict(size=10), thickness=12)),
                hovertemplate="%{marker.color:.0f} ppm<extra></extra>",
            )
        fig.update_xaxes(title_text=xlab, title_font=dict(color=t["muted"], size=12))
    fig.update_yaxes(title_text="m", rangemode="normal",
                     title_font=dict(color=t["muted"], size=12))
    fig.update_layout(showlegend=False)
    return base_layout(fig, title, height=300, dark=dark)


def fig_scatter3d_exploracion(df: pd.DataFrame,
                              labels=("carga", "recuperación", "molestia"),
                              title="🎢 Exploración en 3D", dark: bool = False) -> go.Figure:
    """Scatter 3D rotable: JUGUETE DE EXPLORACIÓN, explícitamente rotulado como tal.

    Se implementa a pesar de que la evidencia le es adversa, y esa evidencia se
    declara en pantalla en vez de esconderla: Sedlmair, Munzner & Tory (2013, IEEE
    TVCG 19(12):2634-2643) compararon 816 scatterplots de 75 conjuntos de datos con
    scatter 2D, 3D interactivo y SPLOM, y el 3D "rara vez ayuda y a menudo perjudica".
    El problema de fondo: sin línea de referencia entre el punto y los ejes la
    profundidad no se puede leer; hay que rotar, y un "grupo" puede ser un artefacto
    del ángulo de cámara.
    Por qué existe igual: construir intuición sobre la propia nube de datos es un
    objetivo legítimo que ese estudio no midió. Pero los valores se leen en los 2D.

    df: columnas x, y, z y opcionalmente fecha.
    """
    t = theme(dark)
    fig = go.Figure()
    d = df.dropna(subset=["x", "y", "z"]).copy() if (df is not None and not df.empty) else pd.DataFrame()
    if not d.empty:
        tiene_fecha = "fecha" in d
        fig.add_scatter3d(
            x=d["x"], y=d["y"], z=d["z"], mode="markers",
            marker=dict(size=4, opacity=0.6, color=d["z"], colorscale=RAMPA_DOLOR,
                        showscale=False),
            customdata=d[["fecha"]] if tiene_fecha else None,
            hovertemplate=("%{customdata[0]}<extra></extra>" if tiene_fecha
                           else "<extra></extra>"),
            name="días",
        )
    fig.update_layout(
        title=title, height=520, showlegend=False,
        paper_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  color=t["ink"], size=13),
        margin=dict(l=0, r=0, t=48, b=40),
        scene=dict(
            xaxis=dict(title=labels[0], backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
            yaxis=dict(title=labels[1], backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
            zaxis=dict(title=labels[2], backgroundcolor=t["surface"],
                       gridcolor=t["grid"], color=t["muted"]),
        ),
        annotations=[dict(
            text="Exploración visual — los valores se leen en los gráficos 2D de arriba.",
            showarrow=False, xref="paper", yref="paper", x=0, y=0,
            font=dict(color=t["muted"], size=11), xanchor="left",
        )],
    )
    return fig


def fig_parcoords(df: pd.DataFrame, cols,
                  title="Coordenadas paralelas (carga → recuperación → síntoma)",
                  dark: bool = False) -> go.Figure:
    """El sustituto honesto del "3D rotable" cuando hay 5-6 variables.

    Cada día es una línea que cruza todos los ejes; arrastrando sobre un eje se
    filtran los demás (brushing). El orden de los ejes es FIJO y documentado —
    carga → recuperación → síntoma — porque igual que en el radar, cambiar el orden
    cambia la figura, y dejarlo al azar sería el mismo pecado que se le critica.
    Ref: Inselberg & Dimsdale (1990), IEEE Visualization '90, 361-378.

    cols: lista de tuplas (columna, etiqueta), en el orden en que deben aparecer.
    """
    t = theme(dark)
    cols = [c for c in (cols or [])
            if df is not None and not df.empty and c[0] in df.columns]
    if not cols:
        return base_layout(go.Figure(), title, height=320, dark=dark)
    d = df.dropna(subset=[c[0] for c in cols])
    if d.empty:
        return base_layout(go.Figure(), title, height=320, dark=dark)
    color_col = cols[-1][0]
    fig = go.Figure(go.Parcoords(
        line=dict(color=d[color_col], colorscale=RAMPA_DOLOR, showscale=True,
                  colorbar=dict(title=dict(text=cols[-1][1], font=dict(size=11)),
                                tickfont=dict(size=10), thickness=12)),
        dimensions=[dict(label=lab, values=d[c]) for c, lab in cols],
        labelfont=dict(size=12, color=t["ink_2"]),
        tickfont=dict(size=10, color=t["muted"]),
    ))
    fig.update_layout(
        title=title, height=380, paper_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  color=t["ink"], size=13),
        margin=dict(l=60, r=60, t=64, b=24),
    )
    return fig
