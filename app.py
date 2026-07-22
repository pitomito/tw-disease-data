"""Taiwan CDC 傳染病互動儀表板 (Streamlit).

Run:  streamlit run app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from viz import charts, data  # noqa: E402

st.set_page_config(page_title="台灣傳染病儀表板", page_icon="🦟", layout="wide")


# --- cached resources / queries ------------------------------------------------
@st.cache_resource
def get_con():
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

st.title("🦟 台灣傳染病互動儀表板")
st.caption("資料來源:衛福部疾管署開放資料 · 星型倉儲 (DuckDB) + 分析層 SQL Views")

tab_trend, tab_rank, tab_map = st.tabs(["📈 趨勢與移動平均", "🏆 地區排名", "🗺️ 登革熱熱區"])

# ============================== 趨勢 ==========================================
with tab_trend:
    c1, c2 = st.columns(2)
    weekly = [(c, code2name[c]) for c in data.WEEKLY_DISEASES]
    with c1:
        d_label = st.selectbox("疾病(週資料)", [n for _, n in weekly], key="tr_dis")
    d_code = next(c for c, n in weekly if n == d_label)
    with c2:
        county = st.selectbox("縣市", counties, index=counties.index("台南市")
                              if "台南市" in counties else 0, key="tr_cty")

    df = data.weekly_trend(con, d_code, county)
    if df.empty:
        st.info("此組合無資料。")
    else:
        st.plotly_chart(charts.weekly_trend_fig(df, d_code, d_label, county),
                        width="stretch", theme=None)
        st.plotly_chart(charts.wow_growth_fig(df, d_label, county),
                        width="stretch", theme=None)

    st.divider()
    st.subheader("COVID-19(月資料)")
    cov_county = st.selectbox("縣市", counties, index=counties.index("新北市")
                              if "新北市" in counties else 0, key="cov_cty")
    cov = data.covid_trend(con, cov_county)
    if not cov.empty:
        st.plotly_chart(charts.covid_trend_fig(cov, cov_county),
                        width="stretch", theme=None)

# ============================== 排名 ==========================================
with tab_rank:
    c1, c2 = st.columns(2)
    with c1:
        d_label = st.selectbox("疾病(週資料)", [n for _, n in weekly], key="rk_dis")
    d_code = next(c for c, n in weekly if n == d_label)
    weeks = data.weekly_weeks(con, d_code)
    with c2:
        wk = st.select_slider("週(週一起始日)", options=weeks, value=weeks[-1],
                              format_func=lambda d: d.strftime("%Y-%m-%d"), key="rk_wk")
    rank_df = data.county_rank_week(con, d_code, wk)
    highlight = st.session_state.get("tr_cty")
    st.plotly_chart(
        charts.county_rank_fig(rank_df, d_label, wk.strftime("%Y-%m-%d"), highlight),
        width="stretch", theme=None)
    with st.expander("完整排名表"):
        st.dataframe(rank_df, width="stretch", hide_index=True)

# ============================== 地圖 ==========================================
with tab_map:
    years = data.dengue_years(con)
    default_yr = data.dengue_top_year(con)
    yr = st.select_slider("年份", options=years, value=default_yr, key="map_yr")
    pts = data.dengue_points(con, yr)
    st.caption(f"{yr} 年已定位登革熱個案:{len(pts):,} 筆"
               "(座標僅 2021 年起提供,故僅近年可繪點圖)")
    st_folium(charts.dengue_heatmap(pts, str(yr)), use_container_width=True, height=560)
