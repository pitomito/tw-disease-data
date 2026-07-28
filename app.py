"""Taiwan CDC 傳染病互動儀表板 (Streamlit).

Run:  streamlit run app.py

Layout follows dashboard conventions rather than document conventions: filters
live in the sidebar, the summary (stat row) comes before the detail (charts),
and each figure gets a short read of what it shows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from viz import charts, data  # noqa: E402

st.set_page_config(page_title="台灣傳染病儀表板", page_icon="🦟",
                   layout="wide", initial_sidebar_state="expanded")

# --- styling: tighten Streamlit's default spacing and give the stat row a
#     surface of its own. Kept minimal so it rides on Streamlit's own theming
#     (works in both light and dark) instead of hardcoding colors.
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px; }
      [data-testid="stMetric"] {
        background: color-mix(in srgb, currentColor 4%, transparent);
        border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
        border-radius: 4px; padding: 12px 16px;
      }
      [data-testid="stMetricLabel"] { opacity: .75; font-size: .82rem; }
      [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
      .caption-rule {
        border: 0; border-top: 1px solid color-mix(in srgb, currentColor 12%, transparent);
        margin: 1.6rem 0 .6rem;
      }
      .eyebrow {
        font-size: .74rem; letter-spacing: .14em; text-transform: uppercase;
        opacity: .6; font-weight: 600; margin-bottom: .2rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- cached resources / queries ------------------------------------------------
@st.cache_resource
def get_con():
    # On a fresh deployment the .duckdb build artifact isn't in the repo, so the
    # first run rebuilds it from the committed snapshot (~40s, then cached).
    if not data.DB_PATH.exists():
        with st.spinner("首次啟動:正在從資料快照建置倉儲(約 40 秒)…"):
            return data.connect()
    return data.connect()


@st.cache_data
def cached_diseases():
    return data.diseases(get_con())


@st.cache_data
def cached_counties():
    return data.counties(get_con())


con = get_con()
dis_df = cached_diseases()
counties = cached_counties()
code2name = dict(zip(dis_df["disease_code"], dis_df["disease_name"]))
weekly = [(c, code2name[c]) for c in data.WEEKLY_DISEASES]


def _county_index(name: str) -> int:
    return counties.index(name) if name in counties else 0


# ============================== 側邊欄:篩選 ==================================
with st.sidebar:
    st.markdown("### 篩選條件")
    d_label = st.selectbox("疾病(週資料)", [n for _, n in weekly], key="dis")
    d_code = next(c for c, n in weekly if n == d_label)
    county = st.selectbox("縣市", counties, index=_county_index("台南市"), key="cty")

    st.markdown('<hr class="caption-rule">', unsafe_allow_html=True)
    st.caption(
        "資料來源:衛生福利部疾病管制署開放資料。\n\n"
        "星型倉儲 (DuckDB) + 分析層 SQL Views,每週由 GitHub Actions 自動更新。"
    )

# ============================== 標題 ==========================================
st.markdown('<p class="eyebrow">Taiwan CDC · 傳染病監測</p>', unsafe_allow_html=True)
st.title("台灣傳染病互動儀表板")

# --- summary before detail: the stat row answers "what's the situation" ---
kpi = data.weekly_kpis(con, d_code, county)
unit = "例" if d_code == "DENGUE" else "人次"
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"最新一週({kpi['latest_week']:%Y-%m-%d})",
          f"{int(kpi['latest_value']):,} {unit}",
          delta=(f"{kpi['latest_wow']:+.0f}% WoW"
                 if kpi["latest_wow"] is not None else None))
c2.metric("4 週移動平均", f"{kpi['latest_ma4']:,.1f} {unit}")
c3.metric(f"歷史單週最高({kpi['peak_week']:%Y-%m})",
          f"{int(kpi['peak_value']):,} {unit}")
c4.metric("累計總計", f"{int(kpi['total_value']):,} {unit}")

tab_trend, tab_rank, tab_map = st.tabs(["趨勢與移動平均", "地區排名", "登革熱熱區"])

# ============================== 趨勢 ==========================================
with tab_trend:
    df = data.weekly_trend(con, d_code, county)
    if df.empty:
        st.info("此組合無資料。")
    else:
        st.plotly_chart(charts.weekly_trend_fig(df, d_code, d_label, county),
                        width="stretch", theme=None)
        st.caption("原始週值為淺色長條;實線為 8 週移動平均(趨勢),虛線為 4 週(較敏感的訊號)。")

        st.plotly_chart(charts.wow_growth_fig(df, d_label, county),
                        width="stretch", theme=None)
        st.caption("增長率與病例數單位不同,故獨立成圖而非疊成雙軸 —— "
                   "疫情的加速與減速通常在這裡比在絕對值上更早顯現。")

    st.markdown('<hr class="caption-rule">', unsafe_allow_html=True)
    st.markdown('<p class="eyebrow">COVID-19 · 月資料</p>', unsafe_allow_html=True)
    cov_county = st.selectbox("縣市", counties, index=_county_index("新北市"),
                              key="cov_cty", label_visibility="collapsed")
    cov = data.covid_trend(con, cov_county)
    if not cov.empty:
        st.plotly_chart(charts.covid_trend_fig(cov, cov_county),
                        width="stretch", theme=None)

# ============================== 排名 ==========================================
with tab_rank:
    weeks = data.weekly_weeks(con, d_code)
    wk = st.select_slider("週(週一起始日)", options=weeks, value=weeks[-1],
                          format_func=lambda d: d.strftime("%Y-%m-%d"), key="rk_wk")
    rank_df = data.county_rank_week(con, d_code, wk)
    st.plotly_chart(
        charts.county_rank_fig(rank_df, d_label, wk.strftime("%Y-%m-%d"), county),
        width="stretch", theme=None)
    st.caption(f"橘色為側邊欄選定的「{county}」。標籤數字為該縣市占全國病例的比例。")
    with st.expander("完整排名表"):
        st.dataframe(rank_df, width="stretch", hide_index=True)

# ============================== 地圖 ==========================================
with tab_map:
    years = data.dengue_years(con)
    default_yr = data.dengue_top_year(con)
    yr = st.select_slider("年份", options=years, value=default_yr, key="map_yr")
    pts = data.dengue_points(con, yr)
    st.caption(f"{yr} 年已定位登革熱個案:{len(pts):,} 筆"
               "(座標僅 2021 年起提供,故僅近年可繪點圖;"
               "繪圖時上限 5,000 點,密度圖抽樣後視覺等價)")
    st_folium(charts.dengue_heatmap(pts, str(yr)), use_container_width=True, height=560)
