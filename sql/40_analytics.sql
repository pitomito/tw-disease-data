-- =============================================================================
-- 分析層(VIEW):移動平均、增長率、地區排名
-- =============================================================================
-- 設計:
--   * 先把事實表彙總到「縣市 × 期間」的共同粒度(週 / 月)。
--   * 週資料(流感/腸病毒/登革熱)為稀疏序列(某縣市某週可能無列),故先鋪
--     密集時間骨架 zero-fill,視窗函數的 ROWS n PRECEDING 才不會跨過空缺算錯。
--   * 視窗分析(MA / 增長率 / 排名)只定義一次,套用到所有週資料疾病。
-- =============================================================================

-- --- 週維度輔助:所有 ISO 週的週一 ---------------------------------------
CREATE OR REPLACE VIEW dim_iso_week AS
SELECT DISTINCT
       isoyear(full_date)                 AS iso_year,
       week(full_date)                    AS iso_week,
       date_trunc('week', full_date)::DATE AS week_start_date   -- 週一
FROM dim_date;

-- =============================================================================
-- 週資料疾病(流感 + 腸病毒 + 登革熱)
-- =============================================================================

-- Layer 1:縣市 × 週 的實際觀測值(稀疏)。
--   流感/腸病毒 metric = 就診人次、denominator = 健保就診總人次;
--   登革熱 metric = 病例數、無 denominator。
CREATE OR REPLACE VIEW agg_weekly_incidence AS
SELECT d.disease_code, d.disease_name, g.county_name,
       dt.iso_year, dt.iso_week, dt.full_date AS week_start_date,
       SUM(f.visit_count)       AS metric_value,
       SUM(f.total_visit_count) AS denominator
FROM fact_nhi_visits f
JOIN dim_disease  d USING (disease_key)
JOIN dim_geography g USING (geo_key)
JOIN dim_date     dt ON dt.date_key = f.date_key   -- date_key 已是該 ISO 週週一
GROUP BY 1, 2, 3, 4, 5, 6
UNION ALL
SELECT d.disease_code, d.disease_name, g.county_name,
       w.iso_year, w.iso_week, w.week_start_date,
       SUM(f.case_count) AS metric_value,
       NULL              AS denominator
FROM fact_dengue_cases f
JOIN dim_disease  d USING (disease_key)
JOIN dim_geography g ON g.geo_key = f.residence_geo_key   -- 依居住縣市
JOIN dim_date     dt ON dt.date_key = f.onset_date_key
JOIN dim_iso_week w  ON w.week_start_date = date_trunc('week', dt.full_date)::DATE
GROUP BY 1, 2, 3, 4, 5, 6;

-- Layer 2:密集骨架(22 縣市 × 該疾病觀測範圍內每一週),缺值補 0。
CREATE OR REPLACE VIEW v_weekly_dense AS
WITH counties AS (
    SELECT county_name FROM dim_geography
    WHERE geo_level = 'county' AND county_name <> '未知'
),
disease_range AS (
    SELECT disease_code, disease_name,
           min(week_start_date) AS wk_min, max(week_start_date) AS wk_max
    FROM agg_weekly_incidence GROUP BY 1, 2
),
spine AS (
    SELECT dr.disease_code, dr.disease_name, c.county_name,
           w.iso_year, w.iso_week, w.week_start_date
    FROM disease_range dr
    CROSS JOIN counties c
    JOIN dim_iso_week w ON w.week_start_date BETWEEN dr.wk_min AND dr.wk_max
)
SELECT s.disease_code, s.disease_name, s.county_name,
       s.iso_year, s.iso_week, s.week_start_date,
       COALESCE(a.metric_value, 0) AS metric_value,
       a.denominator
FROM spine s
LEFT JOIN agg_weekly_incidence a
       ON a.disease_code = s.disease_code
      AND a.county_name  = s.county_name
      AND a.week_start_date = s.week_start_date;

-- Layer 3a:趨勢 — 4/8 週移動平均 + 週增長率(WoW)。
CREATE OR REPLACE VIEW v_weekly_trend AS
SELECT disease_code, disease_name, county_name,
       iso_year, iso_week, week_start_date,
       metric_value,
       ROUND(metric_value * 1.0 / NULLIF(denominator, 0), 5) AS visit_rate,  -- 就診率(登革熱為 NULL)
       ROUND(AVG(metric_value) OVER w4, 1) AS ma4,                           -- 4 週移動平均
       ROUND(AVG(metric_value) OVER w8, 1) AS ma8,                           -- 8 週移動平均
       LAG(metric_value) OVER w            AS prev_week,
       metric_value - LAG(metric_value) OVER w AS wow_change,
       ROUND(100.0 * (metric_value - LAG(metric_value) OVER w)
             / NULLIF(LAG(metric_value) OVER w, 0), 1) AS wow_growth_pct     -- 週增長率 %
FROM v_weekly_dense
WINDOW
    w  AS (PARTITION BY disease_code, county_name ORDER BY week_start_date),
    w4 AS (PARTITION BY disease_code, county_name ORDER BY week_start_date
           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW),
    w8 AS (PARTITION BY disease_code, county_name ORDER BY week_start_date
           ROWS BETWEEN 7 PRECEDING AND CURRENT ROW);

-- Layer 3b:地區排名 — 每疾病每週,各縣市依 metric 排名 + 佔全國比例。
CREATE OR REPLACE VIEW v_county_rank_weekly AS
SELECT disease_code, disease_name, iso_year, iso_week, week_start_date,
       county_name, metric_value,
       RANK() OVER (PARTITION BY disease_code, week_start_date
                    ORDER BY metric_value DESC) AS county_rank,
       ROUND(100.0 * metric_value
             / NULLIF(SUM(metric_value) OVER (PARTITION BY disease_code, week_start_date), 0),
             1) AS pct_of_national
FROM v_weekly_dense;

-- =============================================================================
-- COVID-19(月資料)
-- =============================================================================

-- 縣市 × 月 實際觀測(稀疏)
CREATE OR REPLACE VIEW agg_covid_monthly AS
SELECT g.county_name, f.onset_year, f.onset_month,
       make_date(f.onset_year, f.onset_month, 1) AS month_start,
       SUM(f.case_count) AS cases
FROM fact_covid_cases f
JOIN dim_geography g USING (geo_key)
GROUP BY 1, 2, 3, 4;

-- 密集月骨架(22 縣市 × 每月),缺值補 0
CREATE OR REPLACE VIEW v_covid_monthly_dense AS
WITH counties AS (
    SELECT county_name FROM dim_geography
    WHERE geo_level = 'county' AND county_name <> '未知'
),
rng AS (SELECT min(month_start) AS mn, max(month_start) AS mx FROM agg_covid_monthly),
months AS (
    SELECT (mn + (n * INTERVAL 1 MONTH))::DATE AS month_start
    FROM rng, generate_series(0,
             (year(mx) - year(mn)) * 12 + (month(mx) - month(mn))) AS t(n)
),
spine AS (SELECT c.county_name, m.month_start FROM counties c CROSS JOIN months m)
SELECT s.county_name,
       year(s.month_start)  AS onset_year,
       month(s.month_start) AS onset_month,
       s.month_start,
       COALESCE(a.cases, 0) AS cases
FROM spine s
LEFT JOIN agg_covid_monthly a
       ON a.county_name = s.county_name AND a.month_start = s.month_start;

-- 趨勢 — 3 個月移動平均 + 月增長率(MoM)
CREATE OR REPLACE VIEW v_covid_monthly_trend AS
SELECT county_name, onset_year, onset_month, month_start, cases,
       ROUND(AVG(cases) OVER m3, 1) AS ma3,
       LAG(cases) OVER m            AS prev_month,
       cases - LAG(cases) OVER m    AS mom_change,
       ROUND(100.0 * (cases - LAG(cases) OVER m)
             / NULLIF(LAG(cases) OVER m, 0), 1) AS mom_growth_pct
FROM v_covid_monthly_dense
WINDOW
    m  AS (PARTITION BY county_name ORDER BY month_start),
    m3 AS (PARTITION BY county_name ORDER BY month_start
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW);

-- 地區排名 — 每月各縣市依病例數排名
CREATE OR REPLACE VIEW v_covid_county_rank AS
SELECT county_name, onset_year, onset_month, month_start, cases,
       RANK() OVER (PARTITION BY month_start ORDER BY cases DESC) AS county_rank,
       ROUND(100.0 * cases
             / NULLIF(SUM(cases) OVER (PARTITION BY month_start), 0), 1) AS pct_of_national
FROM v_covid_monthly_dense;
