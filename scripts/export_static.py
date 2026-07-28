"""Headless smoke-test + standalone HTML export (also the GitHub Pages site).

Builds every figure without Streamlit, so a failure here is a data/chart bug,
not a server issue. Each chart is emitted twice — a light variant and a dark
variant under dark/ — so the landing page can swap the embedded charts to match
the viewer's theme instead of showing a white panel on a dark page.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from viz import charts, data, landing, theme  # noqa: E402

OUT = ROOT / "exports"
OUT.mkdir(exist_ok=True)
con = data.connect()
HTML_KW = dict(include_plotlyjs="cdn", full_html=True)   # lean files for GitHub Pages

# ---- data pulled once; both theme passes reuse it -------------------------
df = data.weekly_trend(con, "DENGUE", "台南市")
df_flu = data.weekly_trend(con, "FLU", "台北市")
cov = data.covid_trend(con, "新北市")
weeks = data.weekly_weeks(con, "DENGUE")
rank_year = data.dengue_top_year(con)
peak = max((w for w in weeks if w.year == rank_year),
           key=lambda w: data.county_rank_week(con, "DENGUE", w)["metric_value"].sum())
rank = data.county_rank_week(con, "DENGUE", peak)
map_year = rank_year
pts = data.dengue_points(con, map_year)


def build_charts(out_dir: Path) -> None:
    """Write every chart into out_dir using the currently active palette."""
    out_dir.mkdir(parents=True, exist_ok=True)
    charts.weekly_trend_fig(df, "DENGUE", "登革熱", "台南市").write_html(
        out_dir / "trend_dengue_tainan.html", **HTML_KW)
    charts.wow_growth_fig(df, "登革熱", "台南市").write_html(
        out_dir / "wow_dengue_tainan.html", **HTML_KW)
    charts.weekly_trend_fig(df_flu, "FLU", "流感", "台北市").write_html(
        out_dir / "trend_flu_taipei.html", **HTML_KW)
    charts.county_rank_fig(rank, "登革熱", peak.strftime("%Y-%m-%d"), "台南市").write_html(
        out_dir / "rank_dengue_peak.html", **HTML_KW)
    charts.covid_trend_fig(cov, "新北市").write_html(
        out_dir / "trend_covid_newtaipei.html", **HTML_KW)
    charts.dengue_heatmap(pts, str(map_year)).save(
        str(out_dir / "map_dengue_outbreak.html"))


theme.use_dark(False)
build_charts(OUT)
theme.use_dark(True)
build_charts(OUT / "dark")
theme.use_dark(False)      # leave the module in its default state

# ---- landing page --------------------------------------------------------
# Headline figures come from the warehouse so the page never states a number
# the data doesn't support.
stats = {
    "facts": con.sql(
        "SELECT (SELECT count(*) FROM fact_nhi_visits)"
        "     + (SELECT count(*) FROM fact_covid_cases)"
        "     + (SELECT count(*) FROM fact_dengue_cases)").fetchone()[0],
    "span": [str(x) for x in con.sql(
        "SELECT min(full_date), max(full_date) FROM dim_date "
        "WHERE date_key IN (SELECT onset_date_key FROM fact_dengue_cases)").fetchone()],
    "counties": con.sql(
        "SELECT count(*) FROM dim_geography "
        "WHERE geo_level='county' AND county_name <> '未知'").fetchone()[0],
    "dengue_peak": con.sql(
        "SELECT iso_year, max(metric_value) FROM v_weekly_trend "
        "WHERE disease_code='DENGUE' AND county_name='台南市' "
        "GROUP BY 1 ORDER BY 2 DESC LIMIT 1").fetchone(),
    "covid_peak": con.sql(
        "SELECT onset_year, onset_month, sum(cases) FROM v_covid_monthly_trend "
        "GROUP BY 1,2 ORDER BY 3 DESC LIMIT 1").fetchone(),
}
# Set STREAMLIT_URL once the app is deployed to Streamlit Community Cloud;
# until then the hero shows a "run locally" note instead of a dead link.
STREAMLIT_URL = os.environ.get("STREAMLIT_URL") or None
(OUT / "index.html").write_text(
    landing.build(stats, repo_url="https://github.com/pitomito/tw-disease-data",
                  streamlit_url=STREAMLIT_URL),
    encoding="utf-8")

print("exported:")
for f in sorted(OUT.rglob("*.html")):
    print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size} bytes)")
print(f"\nsmoke-test rows: dengue-trend={len(df)}, flu-trend={len(df_flu)}, "
      f"rank={len(rank)} @ {peak}, covid={len(cov)}, "
      f"dengue-points-{map_year}={len(pts):,}")
