import pandas as pd
import pytest

from src import config as C
from src import capacity as K
from src import forecast as F


def test_required_fte_formula():
    # 4,200 alerts x 0.75 h / 126 productive h per FTE = 25 FTE
    assert K.required_fte(4200, 0.75, 126) == pytest.approx(25.0)


def test_productive_hours():
    # 21 days x 7.5 h x 0.80 x 0.95 = 119.7
    assert K.productive_hours_per_fte(21) == pytest.approx(21 * 7.5 * 0.8 * 0.95)


def test_business_days():
    assert K.business_days_in_month(pd.Timestamp("2026-02-01")) == 20
    assert K.business_days_in_month(pd.Timestamp("2026-01-01")) == 22


def test_projection_no_attrition_with_ramp():
    # one fully ramped person, one new hire at tenure 0: ramps 0.4 -> 0.6 -> 0.8 -> 1.0
    out = K.project_available_fte([12.0, 0.0], 4)
    assert out == pytest.approx([1.4, 1.6, 1.8, 2.0])


def test_projection_departures_and_hires():
    out = K.project_available_fte([12.0] * 5, 4, extra_departures=[(2, 2)], extra_hires=[(3, 1)])
    assert out == pytest.approx([5.0, 3.0, 3.4, 3.6])


def test_attrition_backfilled_after_lag():
    out = K.project_available_fte([12.0] * 100, 4, monthly_attrition=0.01, backfill_lag_months=2)
    # month 2 loses 1; backfill (tenure 0, factor 0.4) arrives in month 4
    assert out[0] == pytest.approx(100.0)
    assert out[1] == pytest.approx(99.0)
    assert out[2] < out[1]
    assert out[3] > out[2] - 1  # backfill contribution begins


def test_gap_sign_and_scenarios():
    months = pd.date_range("2026-01-01", periods=12, freq="MS")
    monthly = pd.DataFrame({
        "month_start": months[:6], "aht_min": 60.0, "alerts_closed": 1000, "backlog_eom": [0, 0, 0, 0, 0, 600],
    })
    fc = pd.DataFrame({"month_start": months[6:12], "forecast": 5000.0})
    roster = pd.DataFrame({"investigator_id": [f"I{i}" for i in range(30)],
                           "hire_date": pd.Timestamp("2020-01-01"), "term_date": pd.NaT})
    res = K.run(monthly, fc, roster, None)["table"]
    base = res[res["scenario"] == "Base"]
    # 5,000 alerts x 1 h / ~125 h ~ 40 FTE required vs ~30 available -> shortfall
    assert (base["gap_fte"] > 0).all()
    up = res[res["scenario"].str.startswith("Rule")]
    assert up["volume"].iloc[-1] == pytest.approx(5000 * (1 + C.VOLUME_SCENARIO_UPLIFT))
    assert up["gap_fte"].iloc[-1] > base["gap_fte"].iloc[-1]
    at = res[res["scenario"] == "Attrition shock"]
    assert at["available_fte"].iloc[2] < base["available_fte"].iloc[2]
    assert base["backlog_clearance_fte"].iloc[0] > 0


def test_forecast_mape_and_design():
    assert F.mape([100, 200], [110, 180]) == pytest.approx(0.10)
    idx = pd.date_range("2025-05-01", periods=3, freq="MS")
    X = F.design(idx, pd.Timestamp("2024-01-01"), pd.Timestamp("2025-06-01"))
    assert list(X["post_launch"]) == [0.0, 1.0, 1.0]
    assert list(X["trend"]) == [16.0, 17.0, 18.0]
