"""Headless smoke-test + standalone HTML export (also the GitHub Pages fallback).

Builds every figure without Streamlit, so a failure here is a data/chart bug,
not a server issue.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from viz import charts, data  # noqa: E402

OUT = ROOT / "exports"
OUT.mkdir(exist_ok=True)
con = data.connect()
HTML_KW = dict(include_plotlyjs="cdn", full_html=True)   # lean files for GitHub Pages

# weekly trend + growth (dengue / 台南)
df = data.weekly_trend(con, "DENGUE", "台南市")
charts.weekly_trend_fig(df, "DENGUE", "登革熱", "台南市").write_html(OUT / "trend_dengue_tainan.html", **HTML_KW)
charts.wow_growth_fig(df, "登革熱", "台南市").write_html(OUT / "wow_dengue_tainan.html", **HTML_KW)

# flu trend (台北)
df_flu = data.weekly_trend(con, "FLU", "台北市")
charts.weekly_trend_fig(df_flu, "FLU", "流感", "台北市").write_html(OUT / "trend_flu_taipei.html", **HTML_KW)

# ranking: dengue 2023 outbreak peak week (2023 is the geocoded-volume year)
weeks = data.weekly_weeks(con, "DENGUE")
rank_year = data.dengue_top_year(con)
peak = max((w for w in weeks if w.year == rank_year),
           key=lambda w: data.county_rank_week(con, "DENGUE", w)["metric_value"].sum())
rank = data.county_rank_week(con, "DENGUE", peak)
charts.county_rank_fig(rank, "登革熱", peak.strftime("%Y-%m-%d"), "台南市").write_html(OUT / "rank_dengue_peak.html", **HTML_KW)

# covid trend (新北)
cov = data.covid_trend(con, "新北市")
charts.covid_trend_fig(cov, "新北市").write_html(OUT / "trend_covid_newtaipei.html", **HTML_KW)

# dengue heatmap (2023 outbreak)
map_year = data.dengue_top_year(con)
pts = data.dengue_points(con, map_year)
charts.dengue_heatmap(pts, str(map_year)).save(str(OUT / "map_dengue_outbreak.html"))

# landing page linking every export (GitHub Pages entry point)
cards = [
    ("trend_dengue_tainan.html", "登革熱 · 台南 — 每週趨勢與移動平均"),
    ("wow_dengue_tainan.html", "登革熱 · 台南 — 週增長率 (WoW)"),
    ("rank_dengue_peak.html", f"登革熱 — 縣市排名({rank_year} 疫情高峰週)"),
    ("trend_flu_taipei.html", "流感 · 台北 — 每週趨勢與移動平均"),
    ("trend_covid_newtaipei.html", "COVID-19 · 新北 — 每月趨勢"),
    ("map_dengue_outbreak.html", f"登革熱個案熱區圖({map_year})"),
]
lis = "\n".join(
    f'    <li><a href="{href}">{label}</a></li>' for href, label in cards)
index = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>台灣傳染病資料視覺化</title>
<style>
 body{{font-family:system-ui,"Segoe UI",sans-serif;max-width:760px;margin:3rem auto;
      padding:0 1rem;color:#0b0b0b;background:#fcfcfb;line-height:1.6}}
 h1{{font-size:1.5rem}} .sub{{color:#52514e}}
 ul{{list-style:none;padding:0}} li{{margin:.5rem 0}}
 a{{display:block;padding:.9rem 1.1rem;background:#fff;border:1px solid #e1e0d9;
    border-radius:8px;text-decoration:none;color:#2a78d6}}
 a:hover{{border-color:#2a78d6}}
 footer{{margin-top:2rem;color:#898781;font-size:.85rem}}
</style></head><body>
<h1>🦟 台灣傳染病資料視覺化</h1>
<p class="sub">資料來源:衛福部疾管署開放資料 · 星型倉儲 (DuckDB) + 分析層 SQL Views。
每週由 GitHub Actions 自動更新。</p>
<ul>
{lis}
</ul>
<footer>互動儀表板(Streamlit)請見 repo 的 <code>app.py</code>。</footer>
</body></html>
"""
(OUT / "index.html").write_text(index, encoding="utf-8")

print("exported:")
for f in sorted(OUT.glob("*.html")):
    print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size} bytes)")
print(f"\nsmoke-test rows: dengue-trend={len(df)}, flu-trend={len(df_flu)}, "
      f"rank={len(rank)} @ {peak}, covid={len(cov)}, "
      f"dengue-points-{map_year}={len(pts):,}")
