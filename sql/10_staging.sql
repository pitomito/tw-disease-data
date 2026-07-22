-- =============================================================================
-- Staging 層:讀 raw parquet,做欄位對齊與基本清理(不落地,以 VIEW 呈現)
-- =============================================================================
-- 清理宏(reusable):
--   age_canon    — 年齡層分隔符正規化:'~' -> '-',讓 COVID/登革熱分桶對齊
--   norm_gender  — 性別正規化:非 M/F 一律歸 'U'(處理 COVID 的 '' 與 'X')
CREATE OR REPLACE MACRO age_canon(x)   AS replace(x, '~', '-');
CREATE OR REPLACE MACRO norm_gender(x) AS CASE WHEN x IN ('M', 'F') THEN x ELSE 'U' END;

-- 流感 + 腸病毒:來源 schema 一致,union 成單一 staging(以 disease_code 區分)
CREATE OR REPLACE VIEW stg_nhi AS
SELECT 'FLU'                                   AS disease_code,
       年                                       AS iso_year,
       週                                       AS iso_week,
       就診類別                                  AS visit_type,
       age_canon(年齡別)                         AS age_label,
       縣市                                      AS county_name,
       TRY_CAST(類流感健保就診人次 AS INTEGER)     AS visit_count,
       TRY_CAST(健保就診總人次 AS INTEGER)         AS total_visit_count
FROM raw_flu
UNION ALL
SELECT 'EV',
       年, 週, 就診類別, age_canon(年齡別), 縣市,
       TRY_CAST(腸病毒健保就診人次 AS INTEGER),
       TRY_CAST(健保就診總人次 AS INTEGER)
FROM raw_ev;

-- COVID-19:月粒度彙總
CREATE OR REPLACE VIEW stg_covid AS
SELECT TRY_CAST(發病年份 AS INTEGER)  AS onset_year,
       TRY_CAST(發病月份 AS INTEGER)  AS onset_month,
       縣市                          AS county_name,
       鄉鎮                          AS town_name,
       norm_gender(性別)             AS gender_code,
       age_canon(年齡層)             AS age_label,
       (是否為境外移入 = '1')         AS is_imported,
       TRY_CAST(確定病例數 AS INTEGER) AS case_count
FROM raw_covid;

-- 登革熱:逐筆個案(明細)
CREATE OR REPLACE VIEW stg_dengue AS
SELECT strptime(發病日, '%Y/%m/%d')::DATE                              AS onset_date,
       TRY_CAST(strptime(NULLIF(個案研判日, ''), '%Y/%m/%d') AS DATE)   AS determined_date,
       TRY_CAST(strptime(NULLIF(通報日, ''),   '%Y/%m/%d') AS DATE)     AS reported_date,
       norm_gender(性別)                                              AS gender_code,
       age_canon(年齡層)                                              AS age_label,
       居住縣市                                                        AS res_county,
       居住鄉鎮                                                        AS res_town,
       感染縣市                                                        AS inf_county,
       感染鄉鎮                                                        AS inf_town,
       (是否境外移入 = '是')                                            AS is_imported,
       NULLIF(感染國家, '')                                            AS infection_country,
       NULLIF(血清型, '')                                              AS serotype,
       TRY_CAST(NULLIF(最小統計區中心點X, '') AS DOUBLE)                AS centroid_x,
       TRY_CAST(NULLIF(最小統計區中心點Y, '') AS DOUBLE)                AS centroid_y,
       TRY_CAST(確定病例數 AS INTEGER)                                  AS case_count
FROM raw_dengue;
