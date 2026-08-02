"""Figuras Plotly compartidas por el dashboard y los reportes.

Paleta y reglas según el sistema de visualización del proyecto:
- Color por entidad (cada deporte tiene SU color fijo, nunca se recicla).
- Un solo eje Y por gráfico. Leyenda visible cuando hay ≥2 series.
- Colores de estado reservados para el semáforo de riesgo (icono + texto, nunca solo color).
Paleta categórica validada (CVD-safe, adjacent pairs, light y dark).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# --- Tokens (modo claro) ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

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


def base_layout(fig: go.Figure, title: str | None = None, height: int = 340) -> go.Figure:
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=INK, size=13),
        margin=dict(l=10, r=10, t=48 if title else 16, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=INK_2, size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font=dict(color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED), zeroline=False)
    fig.update_yaxes(
        gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED),
        zeroline=True, zerolinecolor=BASELINE, zerolinewidth=1, rangemode="tozero",
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
