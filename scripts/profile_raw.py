"""Profile the raw parquet so the ETL cleaning logic is grounded in real values."""
import duckdb

con = duckdb.connect()
RAW = "data/raw"


def q(title, sql):
    print(f"\n=== {title} ===")
    for row in con.sql(sql).fetchall():
        print("  ", row)


# --- flu / enterovirus ---
q("flu 就診類別 (visit_type) distinct",
  f"SELECT DISTINCT 就診類別 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' ORDER BY 1")
q("flu 年齡別 distinct",
  f"SELECT DISTINCT 年齡別 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' ORDER BY 1")
q("flu 週 min/max + distinct count",
  f"SELECT MIN(週), MAX(週), COUNT(DISTINCT 週) FROM '{RAW}/nhi_influenza_like_illness/*.parquet'")
q("flu county name + code sample",
  f"SELECT DISTINCT 縣市, 縣市別代碼 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' ORDER BY 2 LIMIT 30")

# --- covid ---
q("covid 性別 distinct",
  f"SELECT DISTINCT 性別 FROM '{RAW}/covid_age_county_gender/*.parquet'")
q("covid 是否為境外移入 distinct",
  f"SELECT DISTINCT 是否為境外移入 FROM '{RAW}/covid_age_county_gender/*.parquet'")
q("covid 年齡層 distinct",
  f"SELECT DISTINCT 年齡層 FROM '{RAW}/covid_age_county_gender/*.parquet' ORDER BY 1")
q("covid 縣市 distinct (check 臺/台)",
  f"SELECT DISTINCT 縣市 FROM '{RAW}/covid_age_county_gender/*.parquet' ORDER BY 1")
q("covid 發病月份 distinct",
  f"SELECT DISTINCT 發病月份 FROM '{RAW}/covid_age_county_gender/*.parquet' ORDER BY 1")

# --- dengue ---
q("dengue 性別 distinct",
  f"SELECT DISTINCT 性別 FROM '{RAW}/dengue_daily/*.parquet'")
q("dengue 是否境外移入 distinct",
  f"SELECT DISTINCT 是否境外移入 FROM '{RAW}/dengue_daily/*.parquet'")
q("dengue 年齡層 distinct",
  f"SELECT DISTINCT 年齡層 FROM '{RAW}/dengue_daily/*.parquet' ORDER BY 1")
q("dengue 居住縣市 distinct (check 臺/台)",
  f"SELECT DISTINCT 居住縣市 FROM '{RAW}/dengue_daily/*.parquet' ORDER BY 1")
q("dengue 發病日 length distribution (detect truncated dates)",
  f"SELECT LENGTH(發病日) AS len, COUNT(*) FROM '{RAW}/dengue_daily/*.parquet' GROUP BY 1 ORDER BY 1")
q("dengue 發病日 sample of shortest",
  f"SELECT 發病日, COUNT(*) FROM '{RAW}/dengue_daily/*.parquet' WHERE LENGTH(發病日) < 10 GROUP BY 1 ORDER BY 1 LIMIT 10")
q("dengue 血清型 distinct",
  f"SELECT DISTINCT 血清型 FROM '{RAW}/dengue_daily/*.parquet' ORDER BY 1")
q("dengue centroid X/Y null/empty count",
  f"SELECT SUM(CASE WHEN 最小統計區中心點X IS NULL OR 最小統計區中心點X='' THEN 1 ELSE 0 END) AS empty_x, COUNT(*) FROM '{RAW}/dengue_daily/*.parquet'")

# --- cross-source county name overlap ---
q("county names: is 臺 used anywhere?",
  f"""
  SELECT '流感' src, 縣市 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' WHERE 縣市 LIKE '%臺%'
  UNION SELECT 'covid', 縣市 FROM '{RAW}/covid_age_county_gender/*.parquet' WHERE 縣市 LIKE '%臺%'
  UNION SELECT 'dengue', 居住縣市 FROM '{RAW}/dengue_daily/*.parquet' WHERE 居住縣市 LIKE '%臺%'
  LIMIT 20
  """)
