-- =============================================================================
-- 載入維度
-- =============================================================================

-- --- dim_disease(靜態種子)------------------------------------------------
INSERT INTO dim_disease (disease_key, disease_code, disease_name, disease_category) VALUES
    (1, 'FLU',    '流感',              '第四類法定傳染病'),
    (2, 'EV',     '腸病毒感染併發重症', '第三類法定傳染病'),
    (3, '19CoV',  '嚴重特殊傳染性肺炎', '第五類法定傳染病'),
    (4, 'DENGUE', '登革熱',            '第二類法定傳染病');

-- --- dim_gender(靜態種子)--------------------------------------------------
INSERT INTO dim_gender (gender_key, gender_code, gender_label) VALUES
    (1, 'M', '男'), (2, 'F', '女'), (3, 'U', '不詳');

-- --- dim_date(day 粒度日曆,涵蓋 1998–2026)-------------------------------
INSERT INTO dim_date
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
       d                                       AS full_date,
       year(d), quarter(d), month(d), day(d),
       isoyear(d), week(d),                     -- week() 為 ISO 週
       isodow(d),                               -- 1=Mon .. 7=Sun
       (day(d) = 1)      AS is_month_start,
       (isodow(d) = 1)   AS is_iso_week_start
FROM (SELECT unnest(range(DATE '1998-01-01', DATE '2027-01-01', INTERVAL 1 DAY)) AS d);

-- --- dim_age_group(各來源 distinct 標籤聯集,解析上下界)-------------------
INSERT INTO dim_age_group (age_label, age_lower, age_upper)
WITH labels AS (
    SELECT DISTINCT age_label FROM stg_nhi
    UNION SELECT DISTINCT age_label FROM stg_covid
    UNION SELECT DISTINCT age_label FROM stg_dengue
)
SELECT age_label,
       CASE WHEN regexp_full_match(age_label, '[0-9]+')  THEN CAST(age_label AS SMALLINT)
            WHEN age_label LIKE '%+'                      THEN CAST(rtrim(age_label, '+') AS SMALLINT)
            WHEN age_label LIKE '%-%'                     THEN CAST(split_part(age_label, '-', 1) AS SMALLINT)
            ELSE NULL END AS age_lower,                   -- '不詳' -> NULL
       CASE WHEN regexp_full_match(age_label, '[0-9]+')  THEN CAST(age_label AS SMALLINT)
            WHEN age_label LIKE '%+'                      THEN NULL          -- 65+/70+ 無上界
            WHEN age_label LIKE '%-%'                     THEN CAST(split_part(age_label, '-', 2) AS SMALLINT)
            ELSE NULL END AS age_upper
FROM labels;

-- --- dim_geography ---------------------------------------------------------
-- 以縣市名 conform;縣市碼取自流感健保碼(涵蓋全 22 縣市),鄉鎮以名稱對齊。
CREATE OR REPLACE TEMP VIEW county_map AS
SELECT DISTINCT 縣市別代碼 AS county_code, 縣市 AS county_name
FROM raw_flu;

-- 縣市層級(town = '')
INSERT INTO dim_geography (county_code, county_name, town_code, town_name, geo_level)
SELECT county_code, county_name, '', '', 'county' FROM county_map;

-- 未知縣市 sentinel(登革熱少數居住縣市為空)
INSERT INTO dim_geography (county_code, county_name, town_code, town_name, geo_level)
VALUES ('00000', '未知', '', '', 'county');

-- 鄉鎮層級:COVID(帶健保鄉鎮碼)∪ 登革熱居住/感染鄉鎮(僅名稱)
INSERT INTO dim_geography (county_code, county_name, town_code, town_name, geo_level)
WITH towns AS (
    SELECT 縣市 AS county_name, 鄉鎮 AS town_name, 鄉鎮別代碼 AS town_code
    FROM raw_covid WHERE 鄉鎮 <> ''
    UNION
    SELECT 居住縣市, 居住鄉鎮, '' FROM raw_dengue
    WHERE 居住鄉鎮 <> '' AND 居住縣市 <> ''
    UNION
    SELECT 感染縣市, 感染鄉鎮, '' FROM raw_dengue
    WHERE 感染鄉鎮 <> '' AND 感染縣市 <> ''
)
SELECT cm.county_code,
       t.county_name,
       max(t.town_code)  AS town_code,      -- COVID 的非空碼優先於 ''
       t.town_name,
       'town'
FROM towns t
JOIN county_map cm USING (county_name)
GROUP BY cm.county_code, t.county_name, t.town_name;
