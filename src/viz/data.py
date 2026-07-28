"""Data-access layer for the dashboard — thin query functions over warehouse.duckdb.

Framework-agnostic (returns pandas DataFrames) so the same functions serve both
the Streamlit app and standalone HTML export. Connections are read-only.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "warehouse.duckdb"

WEEKLY_DISEASES = ["FLU", "EV", "DENGUE"]   # served by v_weekly_trend


def _writable_db_path() -> Path:
    """Where the warehouse can be built on a fresh deployment.

    Prefer the repo root; fall back to the system temp dir when the checkout is
    read-only (some hosted runtimes mount it that way).
    """
    try:
        probe = ROOT / ".write-probe"
        probe.touch()
        probe.unlink()
        return DB_PATH
    except OSError:
        return Path(tempfile.gettempdir()) / "tw_disease_warehouse.duckdb"


def ensure_warehouse(db_path: Path | str | None = None) -> Path:
    """Return a path to an existing warehouse, building it first if needed.

    The .duckdb file is a build artifact and deliberately not in git, so a fresh
    deployment (e.g. Streamlit Community Cloud) starts without it. The snapshot
    parquet *is* committed, so the warehouse can be rebuilt from it on first run.
    """
    if db_path is not None:
        db_path = Path(db_path)
        if db_path.exists():
            return db_path
    else:
        if DB_PATH.exists():
            return DB_PATH
        db_path = _writable_db_path()
        if db_path.exists():
            return db_path

    # Build from the committed snapshot. build_warehouse reads its target from a
    # module-level global, so point that at our chosen (writable) location.
    src_dir = str(ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    import build_warehouse

    build_warehouse.DB = db_path
    if build_warehouse.main() != 0:
        raise RuntimeError("warehouse build failed QA — see stdout for details")
    return db_path


def connect(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Open the warehouse read-only, building it from the snapshot if absent."""
    return duckdb.connect(str(ensure_warehouse(db_path)), read_only=True)


def diseases(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.sql(
        "SELECT disease_code, disease_name FROM dim_disease ORDER BY disease_key"
    ).df()


def counties(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.sql(
        "SELECT county_name FROM dim_geography "
        "WHERE geo_level='county' AND county_name <> '未知' ORDER BY county_name"
    ).fetchall()
    return [r[0] for r in rows]


def weekly_trend(con, disease_code: str, county_name: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT week_start_date, metric_value, ma4, ma8, wow_growth_pct
        FROM v_weekly_trend
        WHERE disease_code = ? AND county_name = ?
        ORDER BY week_start_date
        """,
        [disease_code, county_name],
    ).df()


def weekly_kpis(con, disease_code: str, county_name: str) -> dict:
    """Headline numbers for the dashboard's stat row.

    `latest` is the most recent week that actually carries data for this
    combination; peak is the all-time weekly maximum.
    """
    row = con.execute(
        """
        WITH t AS (
            SELECT * FROM v_weekly_trend
            WHERE disease_code = ? AND county_name = ?
        ),
        latest AS (SELECT * FROM t ORDER BY week_start_date DESC LIMIT 1),
        peak   AS (SELECT * FROM t ORDER BY metric_value DESC, week_start_date LIMIT 1)
        SELECT (SELECT metric_value    FROM latest) AS latest_value,
               (SELECT week_start_date FROM latest) AS latest_week,
               (SELECT wow_growth_pct  FROM latest) AS latest_wow,
               (SELECT ma4             FROM latest) AS latest_ma4,
               (SELECT metric_value    FROM peak)   AS peak_value,
               (SELECT week_start_date FROM peak)   AS peak_week,
               (SELECT sum(metric_value) FROM t)    AS total_value
        """,
        [disease_code, county_name],
    ).fetchone()
    keys = ["latest_value", "latest_week", "latest_wow", "latest_ma4",
            "peak_value", "peak_week", "total_value"]
    return dict(zip(keys, row))


def weekly_weeks(con, disease_code: str) -> list:
    rows = con.execute(
        "SELECT DISTINCT week_start_date FROM v_weekly_dense "
        "WHERE disease_code = ? ORDER BY week_start_date",
        [disease_code],
    ).fetchall()
    return [r[0] for r in rows]


def county_rank_week(con, disease_code: str, week_start_date) -> pd.DataFrame:
    return con.execute(
        """
        SELECT county_name, metric_value, county_rank, pct_of_national
        FROM v_county_rank_weekly
        WHERE disease_code = ? AND week_start_date = ?
        ORDER BY county_rank
        """,
        [disease_code, week_start_date],
    ).df()


def covid_trend(con, county_name: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT month_start, cases, ma3, mom_growth_pct
        FROM v_covid_monthly_trend
        WHERE county_name = ?
        ORDER BY month_start
        """,
        [county_name],
    ).df()


def dengue_points(con, year: int | None = None) -> pd.DataFrame:
    """Geocoded dengue cases (lat/lon already WGS84) for the hotspot map."""
    sql = """
        SELECT centroid_y AS lat, centroid_x AS lon, dt.year AS onset_year
        FROM fact_dengue_cases f
        JOIN dim_date dt ON dt.date_key = f.onset_date_key
        WHERE f.centroid_x IS NOT NULL AND f.centroid_y IS NOT NULL
    """
    params: list = []
    if year is not None:
        sql += " AND dt.year = ?"
        params.append(year)
    return con.execute(sql, params).df()


def dengue_years(con) -> list[int]:
    """Years with geocoded cases (coordinates only exist from 2021 onward).

    Ascending order — this feeds a select_slider, which reads left-to-right
    in list order, so oldest-to-newest is the natural reading direction.
    """
    rows = con.sql(
        """
        SELECT DISTINCT dt.year
        FROM fact_dengue_cases f JOIN dim_date dt ON dt.date_key = f.onset_date_key
        WHERE f.centroid_x IS NOT NULL
        ORDER BY dt.year ASC
        """
    ).fetchall()
    return [int(r[0]) for r in rows]


def dengue_top_year(con) -> int:
    """Year with the most geocoded cases (2023 outbreak) — a sensible map default."""
    return int(con.sql(
        """
        SELECT dt.year
        FROM fact_dengue_cases f JOIN dim_date dt ON dt.date_key = f.onset_date_key
        WHERE f.centroid_x IS NOT NULL
        GROUP BY dt.year ORDER BY count(*) DESC LIMIT 1
        """
    ).fetchone()[0])
