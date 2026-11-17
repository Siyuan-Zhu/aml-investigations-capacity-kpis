import pandas as pd
import pytest

from src import config as C
from src import simulate as S


@pytest.fixture(scope="module")
def tables():
    return S.simulate(seed=7)


def test_seed_reproducible(tables):
    again = S.simulate(seed=7)
    for k in tables:
        pd.testing.assert_frame_equal(tables[k], again[k])


def test_different_seed_differs(tables):
    other = S.simulate(seed=8)
    assert not tables["alerts"]["handle_minutes"].equals(other["alerts"]["handle_minutes"])


def test_schema(tables):
    assert list(tables["alerts"].columns) == [
        "alert_id", "created_at", "scenario", "risk_band", "risk_score", "sla_days",
        "handle_minutes", "assigned_investigator_id", "closed_at", "disposition",
    ]
    assert list(tables["cases"].columns) == [
        "case_id", "alert_id", "opened_at", "closed_at", "investigator_id", "sar_filed",
    ]
    assert list(tables["investigators"].columns) == ["investigator_id", "hire_date", "term_date"]
    a = tables["alerts"]
    assert set(a["risk_band"]) == {"Low", "Medium", "High"}
    assert set(a["scenario"]) <= set(C.SCENARIOS)
    assert a["alert_id"].is_unique
    assert (a["sla_days"] == a["risk_band"].map(C.SLA_DAYS)).all()


def test_integrity(tables):
    a, c = tables["alerts"], tables["cases"]
    closed = a[a["closed_at"].notna()]
    assert (closed["closed_at"] > closed["created_at"]).all()
    assert closed["disposition"].isin(["closed_no_action", "escalated_to_case"]).all()
    assert a[a["closed_at"].isna()]["disposition"].isna().all()
    # exactly one case per escalated alert
    esc = a[a["disposition"] == "escalated_to_case"]["alert_id"]
    assert sorted(esc) == sorted(c["alert_id"])
    # SAR flag only known once the case is closed
    assert c[c["closed_at"].isna()]["sar_filed"].isna().all()
    assert c[c["closed_at"].notna()]["sar_filed"].notna().all()


def test_shock_only_after_launch(tables):
    a = tables["alerts"]
    new = a[a["scenario"] == C.SHOCK_SCENARIO]
    assert (new["created_at"] >= pd.Timestamp(C.START_DATE) + pd.DateOffset(months=C.SHOCK_MONTH_INDEX)).all()
    assert len(new) > 0


def test_roster_size_and_ramp():
    inv = S.simulate(seed=7)["investigators"]
    assert (inv["hire_date"] < pd.Timestamp(C.START_DATE)).sum() == C.N_INVESTIGATORS_START
    assert inv["term_date"].notna().sum() > 0
    assert C.ramp_factor(0) == 0.4 and C.ramp_factor(2.5) == 0.8 and C.ramp_factor(12) == 1.0
