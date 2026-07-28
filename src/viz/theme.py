"""Central palette + Plotly layout, from the validated dataviz reference palette.

Both light and dark are *selected* palettes — the dark steps were chosen for the
dark surface, not produced by inverting the light ones. Categorical disease hues
are assigned in the palette's fixed slot order.

Call `use_dark(True)` before building figures to render the dark variant; the
static export produces both so the landing page can match the viewer's theme.
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

# --- dark-surface steps (matched to the landing page's dark tokens) ---
_LIGHT = dict(SURFACE=SURFACE, INK=INK, INK_2=INK_2, MUTED=MUTED, GRID=GRID,
              BASELINE=BASELINE, SELECT=SELECT, DISEASE_HUE=dict(DISEASE_HUE))
_DARK = dict(
    SURFACE="#161b21",          # matches --card in the landing page's dark theme
    INK="#eef2f6",
    INK_2="#a7b2be",
    MUTED="#76818d",
    GRID="#262d35",
    BASELINE="#39424c",
    SELECT="#f08050",
    DISEASE_HUE={               # same hues, stepped for the dark ground
        "FLU":    "#5b9bea",
        "EV":     "#28c78a",
        "19CoV":  "#e5b53c",
        "DENGUE": "#3fa93f",
    },
)


def use_dark(enabled: bool = True) -> None:
    """Switch the module-level palette between the light and dark variants."""
    g = globals()
    g.update(_DARK if enabled else _LIGHT)


def base_layout(title: str, height: int = 420) -> dict:
    """Shared Plotly layout: recessive grid/axes, system sans.

    Reads the module-level palette at call time, so `use_dark()` switches the
    surface/ink/grid for every figure built afterwards.

    Title and legend each get their own row in an enlarged top margin (title
    near the very top, legend a clear ~30px band below it) so they never
    overlap regardless of figure height.
    """
    return dict(
        title=dict(text=title, font=dict(size=17, color=INK),
                   x=0, xanchor="left", y=0.97, yanchor="top"),
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family='system-ui, "Segoe UI", sans-serif', color=INK_2, size=13),
        margin=dict(l=60, r=90, t=92, b=44),
        xaxis=dict(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                   showgrid=True, ticks="outside", tickcolor=BASELINE),
        yaxis=dict(gridcolor=GRID, linecolor=BASELINE, zeroline=False,
                   rangemode="tozero"),
        legend=dict(orientation="h", yanchor="top", y=0.84, xanchor="left", x=0,
                    font=dict(size=12)),
        hovermode="x unified",
    )
