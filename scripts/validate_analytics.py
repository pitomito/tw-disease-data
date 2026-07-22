import duckdb, json
con = duckdb.connect('warehouse.duckdb')
out = {}

# zero-fill sanity: dense >> sparse
out['dense_vs_sparse'] = con.sql("""
  SELECT (SELECT count(*) FROM agg_weekly_incidence) AS sparse_rows,
         (SELECT count(*) FROM v_weekly_dense)       AS dense_rows""").fetchall()

# 2015 台南登革熱大流行:移動平均 + 週增長率(應看到爆發性上升)
out['dengue_tainan_2015'] = con.sql("""
  SELECT iso_week, metric_value AS cases, ma4, wow_growth_pct
  FROM v_weekly_trend
  WHERE disease_code='DENGUE' AND county_name='台南市' AND iso_year=2015
    AND iso_week BETWEEN 34 AND 44
  ORDER BY iso_week""").fetchall()

# 登革熱地區排名:2015 疫情高峰週,台南應為第 1
out['dengue_rank_peak'] = con.sql("""
  SELECT county_name, metric_value AS cases, county_rank, pct_of_national
  FROM v_county_rank_weekly
  WHERE disease_code='DENGUE' AND iso_year=2015 AND iso_week=40
  ORDER BY county_rank LIMIT 5""").fetchall()

# COVID 月趨勢:全國最劇烈的月增長(2022 Omicron 起漲)
out['covid_mom_top'] = con.sql("""
  SELECT county_name, month_start, cases, ma3, mom_growth_pct
  FROM v_covid_monthly_trend
  WHERE prev_month IS NOT NULL AND prev_month >= 100
  ORDER BY mom_growth_pct DESC LIMIT 5""").fetchall()

# COVID 地區排名:資料最新月
out['covid_rank_latest'] = con.sql("""
  SELECT county_name, cases, county_rank, pct_of_national
  FROM v_covid_county_rank
  WHERE month_start=(SELECT max(month_start) FROM v_covid_county_rank)
  ORDER BY county_rank LIMIT 5""").fetchall()

# 手算對照:驗證 ma4 = 最近 4 週平均(取流感台北某段)
out['ma4_manual_check'] = con.sql("""
  WITH t AS (
    SELECT week_start_date, metric_value, ma4,
           ROUND(AVG(metric_value) OVER (ORDER BY week_start_date
                 ROWS BETWEEN 3 PRECEDING AND CURRENT ROW),1) AS ma4_recomputed
    FROM v_weekly_trend
    WHERE disease_code='FLU' AND county_name='台北市' AND iso_year=2020
  )
  SELECT count(*) AS rows, sum(CASE WHEN ma4=ma4_recomputed THEN 1 ELSE 0 END) AS matching
  FROM t""").fetchall()

con.close()
open('scripts/analytics_validation.json','w',encoding='utf-8').write(
    json.dumps(out, ensure_ascii=False, indent=2, default=str))
print('written')
