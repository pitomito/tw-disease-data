import duckdb, json
con = duckdb.connect()
RAW = "data/raw"
out = {}
out["flu_visit_type"] = [r[0] for r in con.sql(f"SELECT DISTINCT 就診類別 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' ORDER BY 1").fetchall()]
out["flu_age"] = [r[0] for r in con.sql(f"SELECT DISTINCT 年齡別 FROM '{RAW}/nhi_influenza_like_illness/*.parquet' ORDER BY 1").fetchall()]
out["covid_age"] = [r[0] for r in con.sql(f"SELECT DISTINCT 年齡層 FROM '{RAW}/covid_age_county_gender/*.parquet' ORDER BY 1").fetchall()]
out["dengue_age"] = [r[0] for r in con.sql(f"SELECT DISTINCT 年齡層 FROM '{RAW}/dengue_daily/*.parquet' ORDER BY 1").fetchall()]
out["dengue_serotype"] = [r[0] for r in con.sql(f"SELECT DISTINCT 血清型 FROM '{RAW}/dengue_daily/*.parquet' ORDER BY 1").fetchall()]
out["covid_gender"] = [r[0] for r in con.sql(f"SELECT DISTINCT 性別 FROM '{RAW}/covid_age_county_gender/*.parquet'").fetchall()]
out["dengue_imported"] = [r[0] for r in con.sql(f"SELECT DISTINCT 是否境外移入 FROM '{RAW}/dengue_daily/*.parquet'").fetchall()]
# distinct county names across all three (to seed geography by name)
out["counties"] = [r[0] for r in con.sql(f"""
  SELECT DISTINCT c FROM (
    SELECT 縣市 c FROM '{RAW}/nhi_influenza_like_illness/*.parquet'
    UNION SELECT 縣市 FROM '{RAW}/covid_age_county_gender/*.parquet'
    UNION SELECT 居住縣市 FROM '{RAW}/dengue_daily/*.parquet'
  ) WHERE c <> '' ORDER BY 1""").fetchall()]
with open("scripts/profile_out.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
print("written")
