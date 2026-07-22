"""Build the DuckDB star-schema warehouse from the raw parquet layer.

Pipeline:  schema -> staging views -> load dims -> load facts -> QA report.
The warehouse file is a build artifact; it is deleted and rebuilt on every run so
the process is fully idempotent.

Run:  python src/build_warehouse.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
DB = ROOT / "warehouse.duckdb"
SNAPSHOT = ROOT / "data" / "snapshot"   # committed source of truth for the build
RAW = ROOT / "data" / "raw"             # local timestamped history (fallback)

STAGES = [
    ("schema",     SQL / "schema.sql"),
    ("staging",    SQL / "10_staging.sql"),
    ("load dims",  SQL / "20_load_dims.sql"),
    ("load facts", SQL / "30_load_facts.sql"),
    ("analytics",  SQL / "40_analytics.sql"),
]

# raw view name -> dataset directory. Staging/dim SQL reads these views, never the
# parquet glob directly, so only the LATEST ingest per dataset is used (the raw dir
# keeps every timestamped version for lineage).
RAW_VIEWS = {
    "raw_flu":    "nhi_influenza_like_illness",
    "raw_ev":     "nhi_enteroviral_infection",
    "raw_covid":  "covid_age_county_gender",
    "raw_dengue": "dengue_daily",
}


def register_raw(con: duckdb.DuckDBPyConnection) -> None:
    """Bind each raw_* view to the committed snapshot (or newest local raw file)."""
    for view, dataset in RAW_VIEWS.items():
        snap = SNAPSHOT / f"{dataset}.parquet"
        if snap.exists():
            src = snap
        else:  # local fallback: newest timestamped file (timestamps sort in order)
            files = sorted((RAW / dataset).glob(f"{dataset}_*.parquet"))
            if not files:
                raise FileNotFoundError(
                    f"no snapshot or raw parquet for {dataset} — run extract_raw.py")
            src = files[-1]
        # CREATE VIEW can't take a bind parameter; inline the path (ours, not user
        # input). Forward slashes + escaped quotes keep it valid on Windows too.
        posix = src.as_posix().replace("'", "''")
        con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{posix}')")
        print(f"  raw {view:<11} <- {src.relative_to(ROOT).as_posix()}")

FACT_TABLES = ["fact_nhi_visits", "fact_covid_cases", "fact_dengue_cases"]
DIM_TABLES = ["dim_date", "dim_geography", "dim_disease", "dim_age_group", "dim_gender"]


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    con.execute(path.read_text(encoding="utf-8"))


def qa(con: duckdb.DuckDBPyConnection) -> bool:
    print("\n--- row counts ---")
    for t in DIM_TABLES + FACT_TABLES:
        n = con.sql(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t:<20} {n:>9,}")

    print("\n--- QA checks ---")
    checks = {
        # every staging row must land (no silent drops from inner joins)
        "nhi rows landed":
            "SELECT (SELECT count(*) FROM stg_nhi) = (SELECT count(*) FROM fact_nhi_visits)",
        "covid rows landed":
            "SELECT (SELECT count(*) FROM stg_covid) = (SELECT count(*) FROM fact_covid_cases)",
        "dengue rows landed":
            "SELECT (SELECT count(*) FROM stg_dengue) = (SELECT count(*) FROM fact_dengue_cases)",
        # measures should be non-negative
        "no negative visit_count":
            "SELECT count(*) = 0 FROM fact_nhi_visits WHERE visit_count < 0",
        # dengue geocoded share (for the Folium map)
        "dengue has some geocoded":
            "SELECT count(*) > 0 FROM fact_dengue_cases WHERE centroid_x IS NOT NULL",
    }
    all_ok = True
    for name, sql in checks.items():
        ok = con.sql(sql).fetchone()[0]
        all_ok &= bool(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # a couple of headline numbers to eyeball
    print("\n--- sanity samples ---")
    geo = con.sql(
        "SELECT count(*) FILTER (WHERE geo_level='county') c, "
        "count(*) FILTER (WHERE geo_level='town') t FROM dim_geography").fetchone()
    print(f"  geography: {geo[0]} counties, {geo[1]} towns")
    dengue_geo = con.sql(
        "SELECT round(100.0*count(*) FILTER (WHERE centroid_x IS NOT NULL)/count(*),1) "
        "FROM fact_dengue_cases").fetchone()[0]
    print(f"  dengue geocoded: {dengue_geo}% of cases have coordinates")
    top = con.sql("""
        SELECT g.county_name, sum(f.visit_count) v
        FROM fact_nhi_visits f
        JOIN dim_disease d USING (disease_key)
        JOIN dim_geography g USING (geo_key)
        WHERE d.disease_code='FLU'
        GROUP BY 1 ORDER BY v DESC LIMIT 3""").fetchall()
    print(f"  top-3 flu counties (all-time visits): {top}")

    print(f"\n{'ALL QA PASSED' if all_ok else 'QA FAILURES PRESENT'}")
    return all_ok


def main() -> int:
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    try:
        register_raw(con)          # bind raw_* views to the latest ingest
        for label, path in STAGES:
            run_sql_file(con, path)
            print(f"[ok] {label}")
        ok = qa(con)
    finally:
        con.close()
    print(f"\nWarehouse built -> {DB.relative_to(ROOT)}")
    return 0 if ok else 1          # non-zero on QA failure so CI catches regressions


if __name__ == "__main__":
    import sys
    sys.exit(main())
