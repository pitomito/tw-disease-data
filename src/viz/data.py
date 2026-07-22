"""Data-access layer for the dashboard — thin query functions over warehouse.duckdb.

Framework-agnostic (returns pandas DataFrames) so the same functions serve both
the Streamlit app and standalone HTML export. Connections are read-only.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[2] / "warehouse.duckdb"

WEEKLY_DISEASES = ["FLU", "EV", "DENGUE"]   # served by v_weekly_trend


def connect(db_path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)


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
