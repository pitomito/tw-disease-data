-- =============================================================================
-- 載入事實表(join 維度取代理鍵)
-- =============================================================================

-- --- fact_nhi_visits(流感 + 腸病毒,週)------------------------------------
-- 週 -> 日期:make_date(yr,1,4) 必落在 ISO 第 1 週,對其取週一再位移 (wk-1)*7 天。
INSERT INTO fact_nhi_visits
    (date_key, geo_key, disease_key, age_key, visit_type,
     period_type, iso_year, iso_week, visit_count, total_visit_count)
SELECT CAST(strftime(s.wk_monday, '%Y%m%d') AS INTEGER),
       g.geo_key, d.disease_key, a.age_key, s.visit_type,
       'WEEKLY', CAST(s.iso_year AS SMALLINT), CAST(s.iso_week AS TINYINT),
       s.visit_count, s.total_visit_count
FROM (
    SELECT *,
           (date_trunc('week', make_date(CAST(iso_year AS INTEGER), 1, 4))::DATE
            + (CAST(iso_week AS INTEGER) - 1) * 7) AS wk_monday
    FROM stg_nhi
) s
JOIN dim_disease  d ON d.disease_code = s.disease_code
JOIN dim_geography g ON g.county_name = s.county_name AND g.town_name = ''
JOIN dim_age_group a ON a.age_label   = s.age_label;

-- --- fact_covid_cases(月)---------------------------------------------------
INSERT INTO fact_covid_cases
    (date_key, geo_key, disease_key, age_key, gender_key,
     period_type, onset_year, onset_month, is_imported, case_count)
SELECT s.onset_year * 10000 + s.onset_month * 100 + 1,   -- 當月 1 號 date_key
       g.geo_key, d.disease_key, a.age_key, ge.gender_key,
       'MONTHLY', CAST(s.onset_year AS SMALLINT), CAST(s.onset_month AS TINYINT),
       s.is_imported, s.case_count
FROM stg_covid s
JOIN dim_disease  d  ON d.disease_code = '19CoV'
JOIN dim_geography g ON g.county_name = s.county_name AND g.town_name = s.town_name
JOIN dim_age_group a ON a.age_label   = s.age_label
JOIN dim_gender   ge ON ge.gender_code = s.gender_code;

-- --- fact_dengue_cases(逐筆個案)------------------------------------------
INSERT INTO fact_dengue_cases
    (onset_date_key, determined_date_key, reported_date_key,
     residence_geo_key, infection_geo_key, disease_key, age_key, gender_key,
     is_imported, infection_country, serotype, centroid_x, centroid_y, case_count)
SELECT CAST(strftime(s.onset_date, '%Y%m%d') AS INTEGER),
       CASE WHEN s.determined_date IS NOT NULL
            THEN CAST(strftime(s.determined_date, '%Y%m%d') AS INTEGER) END,
       CASE WHEN s.reported_date IS NOT NULL
            THEN CAST(strftime(s.reported_date, '%Y%m%d') AS INTEGER) END,
       rg.geo_key, ig.geo_key, d.disease_key, a.age_key, ge.gender_key,
       s.is_imported, s.infection_country, s.serotype,
       s.centroid_x, s.centroid_y, s.case_count
FROM stg_dengue s
JOIN dim_disease  d  ON d.disease_code = 'DENGUE'
JOIN dim_age_group a ON a.age_label   = s.age_label
JOIN dim_gender   ge ON ge.gender_code = s.gender_code
-- 居住地:縣市為空 -> '未知'/'';否則對 (縣市, 鄉鎮)
JOIN dim_geography rg
     ON rg.county_name = COALESCE(NULLIF(s.res_county, ''), '未知')
    AND rg.town_name   = CASE WHEN NULLIF(s.res_county, '') IS NULL THEN '' ELSE s.res_town END
-- 感染地:可為 NULL(境外移入常無本地感染地)
LEFT JOIN dim_geography ig
     ON ig.county_name = NULLIF(s.inf_county, '')
    AND ig.town_name   = s.inf_town;
