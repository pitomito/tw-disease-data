"""Chart builders: Plotly figures + a Folium hotspot map.

Design rules applied (dataviz skill):
  * One axis per chart — weekly counts and their moving averages share a unit;
    the week-over-week growth-rate lives in its OWN chart, never a 2nd y-axis.
  * Single entity shown as raw (recessive) + MA4 + MA8 in one disease hue,
    separated by weight, not by unrelated colors.
  * Ranking = magnitude: one hue, bars sorted; the selected county is the only
    mark that changes color (identity of the selection, not a series).
  * Heatmap = sequential single-hue blue ramp (never rainbow).
"""
from __future__ import annotations

import folium
import pandas as pd
import plotly.graph_objects as go
from folium.plugins import HeatMap

from . import theme


def weekly_trend_fig(df: pd.DataFrame, disease_code: str, disease_name: str,
                     county_name: str) -> go.Figure:
    hue = theme.DISEASE_HUE.get(disease_code, "#2a78d6")
    fig = go.Figure()
    # raw weekly = recessive context
    fig.add_bar(x=df["week_start_date"], y=df["metric_value"], name="每週",
                marker_color=hue, opacity=0.22,
                hovertemplate="%{x|%Y-%m-%d}<br>每週 %{y:,}<extra></extra>")
    # 4-week MA = the readable signal
    fig.add_scatter(x=df["week_start_date"], y=df["ma4"], name="4 週移動平均",
                    mode="lines", line=dict(color=hue, width=1.6, dash="dot"),
                    hovertemplate="MA4 %{y:.0f}<extra></extra>")
    # 8-week MA = the trend
    fig.add_scatter(x=df["week_start_date"], y=df["ma8"], name="8 週移動平均",
                    mode="lines", line=dict(color=hue, width=2.6),
                    hovertemplate="MA8 %{y:.0f}<extra></extra>")
    metric_label = "病例數" if disease_code == "DENGUE" else "健保就診人次"
    fig.update_layout(**theme.base_layout(f"{disease_name} · {county_name} — 每週趨勢與移動平均"))
    fig.update_yaxes(title_text=metric_label)
    return fig


def wow_growth_fig(df: pd.DataFrame, disease_name: str, county_name: str) -> go.Figure:
    """Week-over-week growth %, its own chart (no dual axis)."""
    d = df.dropna(subset=["wow_growth_pct"])
    colors = [theme.SELECT if v >= 0 else theme.DISEASE_HUE["FLU"] for v in d["wow_growth_pct"]]
    fig = go.Figure()
    fig.add_bar(x=d["week_start_date"], y=d["wow_growth_pct"], marker_color=colors,
                hovertemplate="%{x|%Y-%m-%d}<br>WoW %{y:.0f}%<extra></extra>")
    fig.update_layout(**theme.base_layout(
        f"{disease_name} · {county_name} — 週增長率 (WoW %)", height=260))
    fig.update_layout(showlegend=False, hovermode="x")
    fig.update_yaxes(title_text="週增長率 %", rangemode="normal", zeroline=True,
                     zerolinecolor=theme.BASELINE)
    return fig


def county_rank_fig(df: pd.DataFrame, disease_name: str, week_label: str,
                    selected_county: str | None = None, top_n: int = 15) -> go.Figure:
    d = df.head(top_n).iloc[::-1]   # reverse so rank 1 sits on top
    colors = [theme.SELECT if c == selected_county else theme.DISEASE_HUE["FLU"]
              for c in d["county_name"]]
    fig = go.Figure()
    fig.add_bar(
        x=d["metric_value"], y=d["county_name"], orientation="h",
        marker_color=colors,
        text=[f"{p:.0f}%" for p in d["pct_of_national"]],
        textposition="outside", textfont=dict(color=theme.INK_2, size=11),
        hovertemplate="%{y}<br>%{x:,}(占全國 %{text})<extra></extra>",
    )
    fig.update_layout(**theme.base_layout(
        f"{disease_name} — 縣市排名({week_label},標籤=占全國比例)"))
    fig.update_layout(showlegend=False, hovermode="closest",
                      margin=dict(l=90, r=70, t=52, b=44))
    fig.update_xaxes(title_text="數值")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def covid_trend_fig(df: pd.DataFrame, county_name: str) -> go.Figure:
    hue = theme.DISEASE_HUE["19CoV"]
    fig = go.Figure()
    fig.add_bar(x=df["month_start"], y=df["cases"], name="每月確診",
                marker_color=hue, opacity=0.25,
                hovertemplate="%{x|%Y-%m}<br>確診 %{y:,}<extra></extra>")
    fig.add_scatter(x=df["month_start"], y=df["ma3"], name="3 月移動平均",
                    mode="lines", line=dict(color=hue, width=2.6),
                    hovertemplate="MA3 %{y:.0f}<extra></extra>")
    fig.update_layout(**theme.base_layout(f"COVID-19 · {county_name} — 每月趨勢"))
    fig.update_yaxes(title_text="確定病例數")
    return fig


def dengue_heatmap(df: pd.DataFrame, year_label: str, max_points: int = 5000) -> folium.Map:
    """Folium density heatmap of geocoded dengue cases (single-hue blue ramp).

    A density map is visually equivalent under sampling, so cap the point count to
    keep the browser render responsive when a year has tens of thousands of cases.
    """
    total = len(df)
    if total > max_points:
        df = df.sample(max_points, random_state=0)
    # Basemap follows the active palette so the map matches the page around it.
    dark = theme.SURFACE != "#fcfcfb"
    m = folium.Map(location=[23.7, 120.9], zoom_start=7,
                   tiles="CartoDB dark_matter" if dark else "CartoDB positron",
                   control_scale=True)
    if not df.empty:
        HeatMap(
            df[["lat", "lon"]].values.tolist(),
            radius=9, blur=12, min_opacity=0.35,
            gradient={0.0: theme.BLUE_RAMP[0], 0.4: theme.BLUE_RAMP[2],
                      0.7: theme.BLUE_RAMP[4], 1.0: theme.BLUE_RAMP[6]},
        ).add_to(m)
    title_html = (
        f'<div style="position:fixed;top:10px;left:50px;z-index:9999;'
        f'background:{theme.SURFACE};padding:6px 12px;border-radius:6px;'
        f'font-family:system-ui,sans-serif;color:{theme.INK};'
        f'box-shadow:0 1px 4px rgba(0,0,0,.15)">'
        f'登革熱個案熱區 · {year_label}({total:,} 筆已定位'
        f'{"、繪圖抽樣 " + format(len(df), ",") if total > max_points else ""})</div>'
    )
    m.get_root().html.add_child(folium.Element(title_html))
    return m
