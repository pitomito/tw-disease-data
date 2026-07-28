"""Landing page generator for the GitHub Pages site.

Design notes
------------
Subject is epidemiological surveillance, so the visual language borrows from
monitoring instruments rather than generic data-portal styling: an asymmetric
masthead-plus-stream layout, tabular figures throughout, and a hairline rule
system standing in for chart gridlines. Accent blue matches the Plotly series
hue so the page and the charts read as one system. Both themes are defined at
token level; the viewer's toggle overrides the OS preference in both directions.
"""
from __future__ import annotations

import html
from datetime import date

# Chart entries: (file, title, blurb, tall?) — tall gets a taller preview frame.
CHARTS: list[dict] = [
    {
        "file": "trend_dengue_tainan.html",
        "eyebrow": "登革熱 · 台南市",
        "title": "每週趨勢與移動平均",
        "blurb": "1998 年至今的完整病例序列。4 週與 8 週移動平均疊在原始週值上,"
                 "2015 年的大流行在圖上是一道無法忽視的尖峰。",
        "height": 460,
    },
    {
        "file": "map_dengue_outbreak.html",
        "eyebrow": "登革熱 · 全台",
        "title": "個案熱區圖",
        "blurb": "2023 年疫情的地理分布,以個案座標繪製密度熱區。"
                 "座標自 2021 年起才提供,故僅近年可繪點圖。",
        "height": 520,
    },
    {
        "file": "rank_dengue_peak.html",
        "eyebrow": "登革熱 · 縣市排名",
        "title": "疫情高峰週的地區集中度",
        "blurb": "疫情從來不是平均分布的。高峰週單一縣市即可占去全國大半病例,"
                 "排名圖讓這個集中度一眼可見。",
        "height": 460,
    },
    {
        "file": "wow_dengue_tainan.html",
        "eyebrow": "登革熱 · 台南市",
        "title": "週增長率(WoW)",
        "blurb": "增長率與病例數單位不同,因此獨立成圖而非疊成雙軸 —— "
                 "疫情的加速與減速在這裡比在絕對值上更早顯現。",
        "height": 320,
    },
    {
        "file": "trend_flu_taipei.html",
        "eyebrow": "流感 · 台北市",
        "title": "健保就診人次趨勢",
        "blurb": "流感的季節性在移動平均上呈現規律的年度波形,"
                 "與登革熱的爆發式尖峰形成對照。",
        "height": 460,
    },
    {
        "file": "trend_covid_newtaipei.html",
        "eyebrow": "COVID-19 · 新北市",
        "title": "每月確診趨勢",
        "blurb": "2022 年 4 月的 Omicron 起漲在月增長率上是四位數的百分比,"
                 "這條曲線是那段時間最直接的紀錄。",
        "height": 460,
    },
]


def _stat(value: str, label: str, note: str = "") -> str:
    note_html = f'<span class="stat-note">{html.escape(note)}</span>' if note else ""
    return (
        '<div class="stat">'
        f'<span class="stat-value">{value}</span>'
        f'<span class="stat-label">{html.escape(label)}</span>'
        f"{note_html}"
        "</div>"
    )


def _chart_section(c: dict, index: int) -> str:
    return f"""
      <section class="chart" id="chart-{index}">
        <div class="chart-head">
          <p class="eyebrow">{html.escape(c['eyebrow'])}</p>
          <h3>{html.escape(c['title'])}</h3>
          <p class="blurb">{html.escape(c['blurb'])}</p>
          <a class="open" href="{c['file']}" target="_blank" rel="noopener">
            單獨開啟<span aria-hidden="true"> &rarr;</span>
          </a>
        </div>
        <div class="frame" style="--h:{c['height']}px">
          <iframe data-chart="{c['file']}" src="{c['file']}"
                  title="{html.escape(c['title'])}"
                  loading="lazy" scrolling="no"></iframe>
        </div>
      </section>"""


def build(stats: dict, repo_url: str, streamlit_url: str | None = None) -> str:
    """Render the landing page HTML.

    `stats` keys: facts, span (start,end), counties, dengue_peak, covid_peak.
    `streamlit_url` — when set, the hero shows a live-dashboard call to action.
    """
    span_start, span_end = stats["span"]
    years = int(span_end[:4]) - int(span_start[:4])
    dengue_year, dengue_peak = stats["dengue_peak"]
    covid_y, covid_m, covid_peak = stats["covid_peak"]

    live_cta = (
        f'<a class="cta primary" href="{streamlit_url}" target="_blank" rel="noopener">'
        "開啟互動儀表板</a>"
        if streamlit_url else
        '<span class="cta disabled" title="需在本機執行 streamlit run app.py">'
        "互動儀表板(本機執行)</span>"
    )

    sections = "\n".join(_chart_section(c, i) for i, c in enumerate(CHARTS))

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>台灣傳染病監測資料 · tw-disease-data</title>
<meta name="description" content="從疾管署開放資料建置的傳染病資料倉儲與視覺化 —— 流感、腸病毒、COVID-19、登革熱,1998 至今。">
<style>
  :root {{
    color-scheme: light;
    --paper:      #f7f8fa;
    --card:       #ffffff;
    --ink:        #101418;
    --ink-2:      #47525e;
    --ink-3:      #7c8794;
    --rule:       #dde3ea;
    --accent:     #2a78d6;
    --accent-ink: #1c5cab;
    --signal:     #c94f3d;
    --shadow:     0 1px 2px rgba(16,20,24,.04), 0 8px 24px -12px rgba(16,20,24,.12);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --paper:      #0e1216;
      --card:       #161b21;
      --ink:        #eef2f6;
      --ink-2:      #a7b2be;
      --ink-3:      #76818d;
      --rule:       #262d35;
      --accent:     #5b9bea;
      --accent-ink: #8bbaf2;
      --signal:     #e0705d;
      --shadow:     0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --paper:      #0e1216;
    --card:       #161b21;
    --ink:        #eef2f6;
    --ink-2:      #a7b2be;
    --ink-3:      #76818d;
    --rule:       #262d35;
    --accent:     #5b9bea;
    --accent-ink: #8bbaf2;
    --signal:     #e0705d;
    --shadow:     0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  }}

  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  @media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    * {{ animation: none !important; transition: none !important; }}
  }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", "Noto Sans TC", sans-serif;
    line-height: 1.65;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 0 24px; }}

  /* ---- masthead: asymmetric, instrument-panel feel ---- */
  header {{
    border-bottom: 1px solid var(--rule);
    background:
      linear-gradient(var(--paper), var(--paper)) padding-box,
      repeating-linear-gradient(90deg, var(--rule) 0 1px, transparent 1px 64px) border-box;
  }}
  .masthead {{
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 48px;
    padding: 72px 0 56px;
    align-items: start;
  }}
  .eyebrow {{
    font-size: .74rem;
    letter-spacing: .16em;
    text-transform: uppercase;
    color: var(--ink-3);
    margin: 0 0 14px;
    font-weight: 600;
  }}
  h1 {{
    font-size: clamp(2.1rem, 4.6vw, 3.4rem);
    line-height: 1.08;
    letter-spacing: -.03em;
    font-weight: 760;
    margin: 0 0 20px;
    text-wrap: balance;
  }}
  h1 .thin {{ font-weight: 300; color: var(--ink-2); display: block; }}
  .lede {{
    font-size: 1.06rem;
    color: var(--ink-2);
    margin: 0 0 28px;
    max-width: 62ch;
  }}
  .ctas {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .cta {{
    display: inline-block;
    padding: 11px 20px;
    border-radius: 3px;
    font-size: .93rem;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid var(--rule);
    color: var(--ink);
    background: var(--card);
    transition: border-color .15s, color .15s;
  }}
  .cta:hover {{ border-color: var(--accent); color: var(--accent-ink); }}
  .cta.primary {{
    background: var(--accent); border-color: var(--accent); color: #fff;
  }}
  .cta.primary:hover {{ background: var(--accent-ink); border-color: var(--accent-ink); color: #fff; }}
  .cta.disabled {{ color: var(--ink-3); cursor: default; }}
  .cta:focus-visible, .open:focus-visible, a:focus-visible {{
    outline: 2px solid var(--accent); outline-offset: 2px;
  }}

  /* ---- stat rail: reads like a monitoring readout ---- */
  .stats {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1px;
    background: var(--rule);
    border: 1px solid var(--rule);
  }}
  .stat {{
    background: var(--paper);
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .stat-value {{
    font-size: 1.65rem;
    font-weight: 700;
    letter-spacing: -.02em;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
  }}
  .stat-value .unit {{ font-size: .82rem; font-weight: 500; color: var(--ink-3); margin-left: 3px; }}
  .stat-label {{ font-size: .8rem; color: var(--ink-2); }}
  .stat-note {{ font-size: .74rem; color: var(--ink-3); font-variant-numeric: tabular-nums; }}
  .stat.signal .stat-value {{ color: var(--signal); }}

  /* ---- pipeline strip ---- */
  .pipeline {{
    display: flex; flex-wrap: wrap; gap: 8px 0;
    padding: 20px 0 22px;
    border-bottom: 1px solid var(--rule);
    font-size: .82rem; color: var(--ink-2);
  }}
  .pipeline span {{ display: inline-flex; align-items: center; }}
  .pipeline span:not(:last-child)::after {{
    content: ""; width: 26px; height: 1px; background: var(--rule); margin: 0 12px;
  }}
  .pipeline b {{ font-weight: 600; color: var(--ink); }}

  /* ---- chart sections ---- */
  main {{ padding: 8px 0 64px; }}
  .section-label {{
    display: flex; align-items: baseline; gap: 14px;
    padding: 46px 0 8px;
  }}
  .section-label h2 {{
    font-size: .8rem; letter-spacing: .16em; text-transform: uppercase;
    color: var(--ink-3); font-weight: 600; margin: 0;
  }}
  .section-label .line {{ flex: 1; height: 1px; background: var(--rule); }}

  .chart {{
    display: grid;
    grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
    gap: 32px;
    padding: 34px 0;
    border-bottom: 1px solid var(--rule);
    align-items: start;
  }}
  .chart-head h3 {{
    font-size: 1.28rem; line-height: 1.25; letter-spacing: -.02em;
    margin: 0 0 10px; font-weight: 680; text-wrap: balance;
  }}
  .blurb {{ font-size: .92rem; color: var(--ink-2); margin: 0 0 16px; }}
  .open {{
    font-size: .85rem; font-weight: 600; color: var(--accent-ink);
    text-decoration: none; border-bottom: 1px solid transparent;
  }}
  .open:hover {{ border-bottom-color: currentColor; }}
  .frame {{
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 4px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }}
  .frame iframe {{
    width: 100%; height: var(--h); border: 0; display: block;
  }}

  /* ---- notes + footer ---- */
  .notes {{
    padding: 40px 0;
    display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 28px;
    border-bottom: 1px solid var(--rule);
  }}
  .note h4 {{
    font-size: .78rem; letter-spacing: .12em; text-transform: uppercase;
    color: var(--ink-3); margin: 0 0 8px; font-weight: 600;
  }}
  .note p {{ margin: 0; font-size: .89rem; color: var(--ink-2); }}
  footer {{
    padding: 30px 0 60px;
    font-size: .82rem; color: var(--ink-3);
    display: flex; flex-wrap: wrap; gap: 6px 20px; justify-content: space-between;
  }}
  footer a {{ color: var(--ink-2); }}

  @media (max-width: 880px) {{
    .masthead {{ grid-template-columns: 1fr; gap: 34px; padding: 48px 0 40px; }}
    .chart {{ grid-template-columns: 1fr; gap: 18px; }}
  }}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <div class="masthead">
      <div>
        <p class="eyebrow">Taiwan CDC · 開放資料 · 資料工程專案</p>
        <h1>台灣傳染病監測<span class="thin">從原始開放資料到可讀的疫情曲線</span></h1>
        <p class="lede">
          這個專案把疾管署的四份開放資料集 —— 流感、腸病毒、COVID-19、登革熱 ——
          擷取、清理、建成星型資料倉儲,再以視窗函數算出移動平均、增長率與地區排名。
          下面每一張圖都由這條管線自動產生,每週重新整理。
        </p>
        <div class="ctas">
          {live_cta}
          <a class="cta" href="{repo_url}" target="_blank" rel="noopener">GitHub 原始碼</a>
        </div>
      </div>
      <div class="stats">
        {_stat(f'{stats["facts"]:,}', "事實資料筆數", "三張事實表合計")}
        {_stat(f'{years}<span class="unit">年</span>', "資料時間跨度", f"{span_start} – {span_end}")}
        {_stat(f'{stats["counties"]}', "涵蓋縣市", "以縣市名 conform")}
        {_stat(f'{dengue_peak:,}', f"{dengue_year} 台南單週峰值", "登革熱大流行")}
      </div>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="pipeline">
    <span><b>擷取</b>&nbsp;CSV / 開放資料</span>
    <span><b>快照</b>&nbsp;Parquet</span>
    <span><b>倉儲</b>&nbsp;DuckDB 星型模型</span>
    <span><b>分析</b>&nbsp;SQL 視窗函數</span>
    <span><b>視覺化</b>&nbsp;Plotly · Folium</span>
    <span><b>部署</b>&nbsp;GitHub Actions</span>
  </div>
</div>

<main class="wrap">
  <div class="section-label">
    <h2>圖表</h2><div class="line"></div>
  </div>
{sections}

  <div class="section-label">
    <h2>資料說明</h2><div class="line"></div>
  </div>
  <div class="notes">
    <div class="note">
      <h4>資料來源</h4>
      <p>衛生福利部疾病管制署開放資料平台。四份資料集皆為 CSV 直接下載,無需爬蟲。</p>
    </div>
    <div class="note">
      <h4>更新頻率</h4>
      <p>每週擷取一次最新資料,經 QA 檢查後由 GitHub Actions 自動重建並重新部署本頁。</p>
    </div>
    <div class="note">
      <h4>已知限制</h4>
      <p>登革熱經緯度僅 2021 年起提供,故熱區圖只涵蓋近年;縣市層級的趨勢與排名則可用全量資料。</p>
    </div>
    <div class="note">
      <h4>COVID-19 峰值</h4>
      <p>全國單月最高為 {covid_y} 年 {covid_m} 月,約 {covid_peak:,} 例 —— Omicron 流行的高點。</p>
    </div>
  </div>
</main>

<div class="wrap">
  <footer>
    <span>資料來源:衛生福利部疾病管制署 · 本專案僅供學習與作品集展示</span>
    <span><a href="{repo_url}" target="_blank" rel="noopener">pitomito/tw-disease-data</a> · 最後更新 {date.today().isoformat()}</span>
  </footer>
</div>

<script>
  // Charts are exported twice (light at the root, dark under dark/). Point each
  // iframe at the variant matching the active theme so an embedded chart never
  // shows a white panel on the dark ground. Re-runs when the OS preference or
  // the viewer's theme toggle changes.
  (function () {{
    var frames = document.querySelectorAll('iframe[data-chart]');
    var mq = window.matchMedia('(prefers-color-scheme: dark)');

    function isDark() {{
      var attr = document.documentElement.getAttribute('data-theme');
      if (attr === 'dark') return true;
      if (attr === 'light') return false;
      return mq.matches;
    }}

    function apply() {{
      var dark = isDark();
      frames.forEach(function (f) {{
        var name = f.getAttribute('data-chart');
        var want = dark ? 'dark/' + name : name;
        if (f.getAttribute('src') !== want) f.setAttribute('src', want);
      }});
    }}

    apply();
    mq.addEventListener('change', apply);
    // The theme toggle stamps data-theme on <html>; react to that too.
    new MutationObserver(apply).observe(document.documentElement, {{
      attributes: true, attributeFilter: ['data-theme']
    }});
  }})();
</script>

</body>
</html>
"""
