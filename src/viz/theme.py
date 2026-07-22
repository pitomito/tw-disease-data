"""Central palette + Plotly layout, from the validated dataviz reference palette.

Light mode only (dashboards render on a light surface). Categorical disease hues
are assigned in the palette's fixed slot order.
"""
from __future__ import annotations

# --- chrome / ink (recessive chart furniture) ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SELECT = "#eb6834"   # slot-8 orange: marks the user's selection, never a series

# --- categorical disease hues (fixed slot order: blue, aqua, yellow, green) ---
DISEASE_HUE = {
    "FLU":    "#2a78d6",
    "EV":     "#1baf7a",
    "19CoV":  "#eda100",
    "DENGUE": "#008300",
}

# --- sequential blue ramp (magnitude): light -> dark, for the dengue heatmap ---
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]


def base_layout(title: str, height: int = 420) -> dict:
    """Shared Plotly layout: recessive grid/axes, system sans, light surface."""
    return dict(
        title=dict(text=title, font=dict(size=17, color=INK)),
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family='system-ui, "Segoe UI", sans-serif', color=INK_2, size=13),
        margin=dict(l=60, r=90, t=52, b=44),
        xaxis=dict(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                   showgrid=True, ticks="outside", tickcolor=BASELINE),
        yaxis=dict(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                   rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=12)),
        hovermode="x unified",
    )
