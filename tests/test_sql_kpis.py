"""KPI/KRI SQL correctness on a tiny hand-computed fixture (Jan-Feb 2026)."""
from datetime import date

import duckdb
import pandas as pd
import pytest

from src.models import build_models

TS = pd.Timestamp


@pytest.fixture(scope="module")
def con():
    alerts = pd.DataFrame(
        [
            # id, created, scenario, band, score, sla, handle, inv, closed, disposition
            ("A1", "2026-01-05 02:00", "S1", "High", 80, 5, 30.0, "INV-A", "2026-01-08 10:00", "closed_no_action"),
            ("A2", "2026-01-05 02:00", "S2", "Low", 10, 20, 60.0, "INV-B", "2026-01-30 10:00", "escalated_to_case"),
            ("A3", "2026-01-12 02:00", "S1", "Medium", 50, 10, 45.0, "INV-A", "2026-01-20 10:00", "closed_no_action"),
            ("A4", "2026-01-20 02:00", "S2", "High", 90, 5, 90.0, "INV-B", "2026-02-10 10:00", "escalated_to_case"),
            ("A5", "2026-02-03 02:00", "S1", "Low", 10, 20, None, None, None, None),
            ("A6", "2026-02-10 02:00", "S1", "High", 85, 5, None, None, None, None),
            ("A7", "2026-02-25 02:00", "S1", "Medium", 55, 10, None, None, None, None),
            ("A8", "2026-02-02 02:00", "S1", "Low", 5, 20, 30.0, "INV-A", "2026-02-05 10:00", "closed_no_action"),
        ],
        columns=["alert_id", "created_at", "scenario", "risk_band", "risk_score", "sla_days",
                 "handle_minutes", "assigned_investigator_id", "closed_at", "disposition"],
    )
    alerts["created_at"] = pd.to_datetime(alerts["created_at"])
    alerts["closed_at"] = pd.to_datetime(alerts["closed_at"])
    cases = pd.DataFrame(
        [
            ("C1", "A2", "2026-01-30 10:00", "2026-02-15 10:00", "INV-B", True),
            ("C2", "A4", "2026-02-10 10:00", "2026-02-20 10:00", "INV-B", False),
        ],
        columns=["case_id", "alert_id", "opened_at", "closed_at", "investigator_id", "sar_filed"],
    )
    cases["opened_at"] = pd.to_datetime(cases["opened_at"])
    cases["closed_at"] = pd.to_datetime(cases["closed_at"])
    cases["sar_filed"] = cases["sar_filed"].astype("boolean")
    inv = pd.DataFrame(
        {"investigator_id": ["INV-A", "INV-B"],
         "hire_date": pd.to_datetime(["2025-01-01", "2026-01-02"]),
         "term_date": pd.to_datetime([None, None])}
    )
    c = duckdb.connect()
    build_models(c, {"alerts": alerts, "cases": cases, "investigators": inv}, date(2026, 2, 28))
    return c


def monthly(con, month):
    return con.execute("SELECT * FROM mart_monthly WHERE month_start = ?", [month]).df().iloc[0]


def test_january_kpis(con):
    j = monthly(con, date(2026, 1, 1))
    assert j["alerts_created"] == 4 and j["alerts_closed"] == 3
    assert j["pct_within_sla"] == pytest.approx(2 / 3)
    assert j["sla_breach_rate"] == pytest.approx(1 / 3)
    assert j["aht_min"] == pytest.approx(45.0)
    assert j["escalation_rate"] == pytest.approx(1 / 3)
    assert j["fp_rate"] == pytest.approx(2 / 3)
    assert j["backlog_eom"] == 1
    assert j["cases_opened"] == 1
    assert pd.isna(j["sar_conversion_rate"])  # no case closed in January
    assert j["business_days"] == 22


def test_february_kpis_and_kris(con):
    f = monthly(con, date(2026, 2, 1))
    assert f["alerts_created"] == 4 and f["alerts_closed"] == 2
    assert f["pct_within_sla"] == pytest.approx(0.5)
    assert f["aht_min"] == pytest.approx(60.0)
    assert f["backlog_eom"] == 3
    assert f["open_gt30"] == 0
    assert f["overdue_open"] == 2 and f["high_overdue_open"] == 1 and f["high_open"] == 1
    assert f["high_overdue_pct"] == pytest.approx(1.0)
    assert f["sar_conversion_rate"] == pytest.approx(0.5)
    assert f["business_days"] == 20


def test_investigator_productivity_and_ramp(con):
    f = monthly(con, date(2026, 2, 1))
    assert f["headcount_mid"] == 2
    assert f["effective_fte"] == pytest.approx(1.0 + 0.6)  # INV-B tenure 1 month
    assert f["cases_per_inv_week"] == pytest.approx(1 / 2 / (20 / 5))
    j = monthly(con, date(2026, 1, 1))
    assert j["effective_fte"] == pytest.approx(1.0 + 0.4)


def test_aging_buckets(con):
    df = con.execute(
        "SELECT aging_bucket, risk_band, open_alerts FROM mart_aging_snapshot WHERE month_start = DATE '2026-02-01'"
    ).df()
    got = {(r.aging_bucket, r.risk_band): r.open_alerts for r in df.itertuples()}
    assert got == {("15-30", "Low"): 1, ("15-30", "High"): 1, ("0-7", "Medium"): 1}


def test_scenario_kpis(con):
    df = con.execute("SELECT * FROM mart_scenario_kpis WHERE period = 'all'").df().set_index("scenario")
    assert df.loc["S1", "fp_rate"] == pytest.approx(1.0)
    assert df.loc["S2", "fp_rate"] == pytest.approx(0.0)
    assert df.loc["S2", "sar_conversion_rate"] == pytest.approx(0.5)


def test_scorecard_rag(con):
    sc = con.execute("SELECT * FROM mart_scorecard").df().set_index("metric_id")
    assert sc.loc["backlog_eom", "rag"] == "Green"          # 3 < 1,500
    assert sc.loc["pct_within_sla", "rag"] == "Red"         # 50% < 90%
    assert sc.loc["high_overdue_pct", "rag"] == "Red"       # 100% >= 25%
    assert sc.loc["alerts_created", "rag"] == "Monitor"
    assert sc.loc["backlog_eom", "prior_value"] == 1
