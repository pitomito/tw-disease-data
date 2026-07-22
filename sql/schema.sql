-- =============================================================================
-- Taiwan CDC 傳染病資料倉儲 — 星型 Schema (DuckDB)
-- =============================================================================
-- 設計原則
--   * 共用維度 (conformed dimensions) 跨疾病共享:dim_geography / dim_disease /
--     dim_age_group / dim_gender / dim_date。
--   * 三種資料粒度不同,因此拆成三張事實表(標準做法,不硬湊成一張):
--       fact_nhi_visits  — 週 × 縣市 × 年齡(流感 + 腸病毒,兩者 schema 一致)
--       fact_covid_cases — 月 × 縣市/鄉鎮 × 性別 × 年齡(彙總)
--       fact_dengue_cases— 逐筆個案(含經緯度,供 Folium 熱區地圖)
--   * 所有事實表都用「期間起始日」對到 day 粒度的 dim_date:
--       週資料 -> 該 ISO 週的週一;月資料 -> 當月 1 號;個案 -> 發病日。
--     這樣就能用單一 dim_date 服務三種粒度,period_type 欄位標明原始粒度。
--   * 地理一律用「代碼」join,不用中文名(解決「台北市/臺北市」不一致)。
-- 執行:duckdb warehouse.duckdb < sql/schema.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 維度:日期 (day 粒度日曆)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key         INTEGER   PRIMARY KEY,   -- YYYYMMDD
    full_date        DATE      NOT NULL,
    year             SMALLINT  NOT NULL,
    quarter          TINYINT   NOT NULL,
    month            TINYINT   NOT NULL,
    day              TINYINT   NOT NULL,
    iso_year         SMALLINT  NOT NULL,
    iso_week         TINYINT   NOT NULL,      -- 1..53
    day_of_week      TINYINT   NOT NULL,      -- 1=Mon .. 7=Sun
    is_month_start   BOOLEAN   NOT NULL,
    is_iso_week_start BOOLEAN  NOT NULL       -- 週一為 TRUE
);

-- ---------------------------------------------------------------------------
-- 維度:地理(縣市 + 鄉鎮,用內政部/健保代碼當自然鍵)
-- ---------------------------------------------------------------------------
-- 註:三個來源的地理代碼系統不同(健保碼 vs 內政部碼),因此本維度
-- 以「縣市名 + 鄉鎮名」為商業鍵 conform;code 欄位僅為便利屬性。
-- 鄉鎮以空字串 '' 代表「僅到縣市層級」,避免 UNIQUE 對 NULL 的例外語意。
CREATE SEQUENCE IF NOT EXISTS seq_geo_key START 1;
CREATE TABLE IF NOT EXISTS dim_geography (
    geo_key       BIGINT   PRIMARY KEY DEFAULT nextval('seq_geo_key'),
    county_code   VARCHAR  NOT NULL,          -- 代表性健保縣市碼(便利屬性)
    county_name   VARCHAR  NOT NULL,
    town_code     VARCHAR  NOT NULL DEFAULT '',
    town_name     VARCHAR  NOT NULL DEFAULT '', -- '' = 僅到縣市層級
    geo_level     VARCHAR  NOT NULL,          -- 'county' / 'town'
    UNIQUE (county_name, town_name)
);

-- ---------------------------------------------------------------------------
-- 維度:疾病
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_disease (
    disease_key      INTEGER  PRIMARY KEY,
    disease_code     VARCHAR  NOT NULL UNIQUE, -- 'FLU' / 'EV' / '19CoV' / 'DENGUE'
    disease_name     VARCHAR  NOT NULL,        -- '流感' ...
    disease_category VARCHAR                   -- 例:'第三類法定傳染病'(可選)
);

-- ---------------------------------------------------------------------------
-- 維度:年齡層
--   來源標籤格式不一(流感 '0~2'、登革熱 '30-34'),於 ETL 階段標準化後
--   填入 age_lower/age_upper,原始標籤保留在 age_label。
-- ---------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS seq_age_key START 1;
CREATE TABLE IF NOT EXISTS dim_age_group (
    age_key     INTEGER  PRIMARY KEY DEFAULT nextval('seq_age_key'),
    age_label   VARCHAR  NOT NULL UNIQUE,      -- 原始標籤
    age_lower   SMALLINT,                      -- 標準化下界(含)
    age_upper   SMALLINT                       -- 標準化上界(含);NULL = 以上
);

-- ---------------------------------------------------------------------------
-- 維度:性別
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_gender (
    gender_key   INTEGER  PRIMARY KEY,
    gender_code  VARCHAR  NOT NULL UNIQUE,     -- 'M' / 'F' / 'U'
    gender_label VARCHAR  NOT NULL             -- '男' / '女' / '不詳'
);

-- ===========================================================================
-- 事實表
-- ===========================================================================

-- 流感 + 腸病毒(健保門急住診就診人次)。兩者來源 schema 完全一致,
-- 以 disease_key 區分,union 進同一張表。
CREATE SEQUENCE IF NOT EXISTS seq_visit_id START 1;
CREATE TABLE IF NOT EXISTS fact_nhi_visits (
    visit_id          BIGINT   PRIMARY KEY DEFAULT nextval('seq_visit_id'),
    date_key          INTEGER  NOT NULL REFERENCES dim_date(date_key),      -- ISO 週一
    geo_key           BIGINT   NOT NULL REFERENCES dim_geography(geo_key),
    disease_key       INTEGER  NOT NULL REFERENCES dim_disease(disease_key),
    age_key           INTEGER  NOT NULL REFERENCES dim_age_group(age_key),
    visit_type        VARCHAR  NOT NULL,       -- 就診類別:門診/急診/住院
    period_type       VARCHAR  NOT NULL DEFAULT 'WEEKLY',
    iso_year          SMALLINT NOT NULL,
    iso_week          TINYINT  NOT NULL,
    visit_count       INTEGER  NOT NULL,       -- 該疾病就診人次
    total_visit_count INTEGER  NOT NULL        -- 健保就診總人次(分母)
);

-- COVID-19:地區/年齡/性別彙總,月粒度。
CREATE SEQUENCE IF NOT EXISTS seq_covid_id START 1;
CREATE TABLE IF NOT EXISTS fact_covid_cases (
    covid_id     BIGINT   PRIMARY KEY DEFAULT nextval('seq_covid_id'),
    date_key     INTEGER  NOT NULL REFERENCES dim_date(date_key),           -- 當月 1 號
    geo_key      BIGINT   NOT NULL REFERENCES dim_geography(geo_key),       -- 縣市 + 鄉鎮
    disease_key  INTEGER  NOT NULL REFERENCES dim_disease(disease_key),
    age_key      INTEGER  NOT NULL REFERENCES dim_age_group(age_key),
    gender_key   INTEGER  NOT NULL REFERENCES dim_gender(gender_key),
    period_type  VARCHAR  NOT NULL DEFAULT 'MONTHLY',
    onset_year   SMALLINT NOT NULL,
    onset_month  TINYINT  NOT NULL,
    is_imported  BOOLEAN  NOT NULL,            -- 是否境外移入
    case_count   INTEGER  NOT NULL             -- 確定病例數
);

-- 登革熱:逐筆個案(明細事實表)。保留居住/感染兩組地理與經緯度供地圖使用。
CREATE SEQUENCE IF NOT EXISTS seq_dengue_id START 1;
CREATE TABLE IF NOT EXISTS fact_dengue_cases (
    dengue_case_id     BIGINT   PRIMARY KEY DEFAULT nextval('seq_dengue_id'),
    onset_date_key     INTEGER  NOT NULL REFERENCES dim_date(date_key),     -- 發病日
    determined_date_key INTEGER REFERENCES dim_date(date_key),             -- 研判日
    reported_date_key  INTEGER  REFERENCES dim_date(date_key),             -- 通報日
    residence_geo_key  BIGINT   NOT NULL REFERENCES dim_geography(geo_key),-- 居住地
    infection_geo_key  BIGINT   REFERENCES dim_geography(geo_key),         -- 感染地(可 NULL)
    disease_key        INTEGER  NOT NULL REFERENCES dim_disease(disease_key),
    age_key            INTEGER  NOT NULL REFERENCES dim_age_group(age_key),
    gender_key         INTEGER  NOT NULL REFERENCES dim_gender(gender_key),
    is_imported        BOOLEAN  NOT NULL,      -- 是否境外移入
    infection_country  VARCHAR,                -- 感染國家
    serotype           VARCHAR,                -- 血清型(第一~四型)
    centroid_x         DOUBLE,                 -- 最小統計區中心點經度(供 Folium)
    centroid_y         DOUBLE,                 -- 最小統計區中心點緯度
    case_count         INTEGER  NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------------
-- 查詢輔助索引(DuckDB 為分析型,索引非必需;針對常用過濾鍵建即可)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_nhi_date    ON fact_nhi_visits (date_key);
CREATE INDEX IF NOT EXISTS ix_nhi_disease ON fact_nhi_visits (disease_key);
CREATE INDEX IF NOT EXISTS ix_covid_date  ON fact_covid_cases (date_key);
CREATE INDEX IF NOT EXISTS ix_dengue_date ON fact_dengue_cases (onset_date_key);
