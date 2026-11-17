"""Monthly alert-volume forecast: OLS on trend + annual harmonic + rule-launch dummy.

volume_t = b0 + b1*t + b2*sin(2*pi*m/12) + b3*cos(2*pi*m/12) + b4*post_launch_t + e_t

Backtest: fit on all but the last HOLDOUT_MONTHS, score MAPE on the holdout.
Forecast: refit on all months, predict FORECAST_MONTHS ahead with 95% prediction intervals.
Run: python -m src.forecast
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C


def design(months: pd.DatetimeIndex, t0: pd.Timestamp, shock_start: pd.Timestamp) -> pd.DataFrame:
    t = ((months.year - t0.year) * 12 + (months.month - t0.month)).astype(float)
    ang = 2 * np.pi * months.month / 12
    return pd.DataFrame(
        {
            "const": 1.0,
            "trend": t,
            "sin12": np.sin(ang),
            "cos12": np.cos(ang),
            "post_launch": (months >= shock_start).astype(float),
        },
        index=months,
    )


def mape(actual, pred) -> float:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.mean(np.abs((actual - pred) / actual)))


def shock_start_month() -> pd.Timestamp:
    ms = pd.Timestamp(C.START_DATE) + pd.DateOffset(months=C.SHOCK_MONTH_INDEX)
    return pd.Timestamp(ms.year, ms.month, 1)


def run(monthly: pd.DataFrame) -> dict:
    s = monthly.set_index(pd.to_datetime(monthly["month_start"]))["alerts_created"].astype(float)
    t0, shock = s.index[0], shock_start_month()
    X = design(s.index, t0, shock)
    n_train = len(s) - C.HOLDOUT_MONTHS
    fit_bt = sm.OLS(s.iloc[:n_train], X.iloc[:n_train]).fit()
    bt_pred = fit_bt.predict(X.iloc[n_train:])
    backtest = pd.DataFrame({"actual": s.iloc[n_train:], "predicted": bt_pred})
    bt_mape = mape(backtest["actual"], backtest["predicted"])

    fit = sm.OLS(s, X).fit()
    fut_idx = pd.date_range(s.index[-1] + pd.DateOffset(months=1), periods=C.FORECAST_MONTHS, freq="MS")
    Xf = design(fut_idx, t0, shock)
    pf = fit.get_prediction(Xf).summary_frame(alpha=0.05)
    fc = pd.DataFrame(
        {
            "month_start": fut_idx,
            "forecast": pf["mean"].values,
            "lower_95": pf["obs_ci_lower"].values,
            "upper_95": pf["obs_ci_upper"].values,
        }
    )
    fitted = pd.DataFrame({"month_start": s.index, "actual": s.values, "fitted": fit.fittedvalues.values})
    summary = {
        "backtest_mape": bt_mape,
        "holdout_months": C.HOLDOUT_MONTHS,
        "train_months": n_train,
        "r_squared_full_fit": float(fit.rsquared),
        "coefficients": {k: float(v) for k, v in fit.params.items()},
        "coef_pvalues": {k: float(v) for k, v in fit.pvalues.items()},
        "launch_effect_alerts_per_month": float(fit.params["post_launch"]),
        "trend_alerts_per_month": float(fit.params["trend"]),
    }
    return {"fc": fc, "backtest": backtest, "fitted": fitted, "summary": summary}


def main() -> None:
    monthly = pd.read_csv(C.OUT_DIR / "mart_monthly.csv")
    r = run(monthly)
    r["fc"].to_csv(C.OUT_DIR / "forecast.csv", index=False)
    r["backtest"].reset_index().rename(columns={"index": "month_start"}).to_csv(C.OUT_DIR / "backtest.csv", index=False)
    r["fitted"].to_csv(C.OUT_DIR / "fitted.csv", index=False)
    (C.OUT_DIR / "forecast_summary.json").write_text(json.dumps(r["summary"], indent=2))
    print(f"Backtest MAPE on last {C.HOLDOUT_MONTHS} months: {r['summary']['backtest_mape']:.1%}")


if __name__ == "__main__":
    main()
