"""Load raw tables into DuckDB and run the SQL model layer in file order.

Run: python -m src.models
"""
from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from . import config as C


def load_raw(con: duckdb.DuckDBPyConnection, tables: dict[str, pd.DataFrame]) -> None:
    """Register raw_alerts, raw_cases, raw_investigators."""
    for name, df in tables.items():
        con.register(f"_tmp_{name}", df)
        con.execute(f"CREATE OR REPLACE TABLE raw_{name} AS SELECT * FROM _tmp_{name}")
        con.unregister(f"_tmp_{name}")


def build_ref(con: duckdb.DuckDBPyConnection, as_of: date) -> None:
    con.execute(
        "CREATE OR REPLACE TABLE run_params AS SELECT CAST(? AS DATE) AS as_of, CAST(? AS INTEGER) AS sar_clock_days",
        [as_of, C.SAR_CLOCK_DAYS],
    )
    con.execute("CREATE OR REPLACE TABLE ref_ramp(tenure_from INTEGER, ramp_factor DOUBLE)")
    con.executemany("INSERT INTO ref_ramp VALUES (?, ?)", C.RAMP)
    con.execute(
        "CREATE OR REPLACE TABLE ref_thresholds(metric_id VARCHAR, metric_name VARCHAR, "
        "metric_type VARCHAR, unit VARCHAR, direction VARCHAR, amber DOUBLE, red DOUBLE, sort_order INTEGER)"
    )
    con.executemany(
        "INSERT INTO ref_thresholds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(*t, i) for i, t in enumerate(C.THRESHOLDS)],
    )


def run_sql(con: duckdb.DuckDBPyConnection) -> list[str]:
    ran = []
    for path in sorted(C.SQL_DIR.glob("*.sql")):
        con.execute(path.read_text())
        ran.append(path.name)
    return ran


def build_models(con: duckdb.DuckDBPyConnection, tables: dict[str, pd.DataFrame], as_of: date) -> None:
    load_raw(con, tables)
    build_ref(con, as_of)
    run_sql(con)


def read_raw_csv() -> dict[str, pd.DataFrame]:
    a = pd.read_csv(C.RAW_DIR / "alerts.csv", parse_dates=["created_at", "closed_at"])
    c = pd.read_csv(C.RAW_DIR / "cases.csv", parse_dates=["opened_at", "closed_at"])
    c["sar_filed"] = c["sar_filed"].astype("boolean")
    i = pd.read_csv(C.RAW_DIR / "investigators.csv", parse_dates=["hire_date", "term_date"])
    return {"alerts": a, "cases": c, "investigators": i}


def main() -> None:
    tables = read_raw_csv()
    last = tables["alerts"]["created_at"].max()
    as_of = (last + pd.offsets.MonthEnd(0)).date()
    C.DATA_DIR.mkdir(exist_ok=True)
    C.OUT_DIR.mkdir(exist_ok=True)
    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    con = duckdb.connect(str(C.DB_PATH))
    build_models(con, tables, as_of)
    for t in ["mart_monthly", "mart_aging_snapshot", "mart_scenario_kpis", "mart_investigator_month", "mart_scorecard"]:
        con.execute(f"SELECT * FROM {t}").df().to_csv(C.OUT_DIR / f"{t}.csv", index=False)
    print(f"SQL models built as of {as_of}: {len(list(C.SQL_DIR.glob('*.sql')))} files -> {C.DB_PATH.name}")
    con.close()


if __name__ == "__main__":
    main()
