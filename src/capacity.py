"""Investigator capacity model: required FTE vs available FTE under three scenarios.

required_fte = volume * AHT_hours / productive_hours_per_fte_month
productive_hours_per_fte_month = business_days * hours_per_day * utilization * (1 - shrinkage)
available_fte = sum over investigators of ramp_factor(tenure), projected with attrition/backfill.
gap_fte = required_fte - available_fte  (positive = shortfall)
Run: python -m src.capacity
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from . import config as C


def business_days_in_month(month_start: pd.Timestamp) -> int:
    end = month_start + pd.offsets.MonthEnd(0)
    return int(np.busday_count(month_start.date(), (end + pd.Timedelta(days=1)).date()))


def productive_hours_per_fte(business_days: int) -> float:
    return business_days * C.HOURS_PER_DAY * C.UTILIZATION * (1 - C.SHRINKAGE)


def required_fte(volume: float, aht_hours: float, productive_hours: float) -> float:
    return volume * aht_hours / productive_hours


def project_available_fte(
    tenures: list[float],
    n_months: int,
    monthly_attrition: float = 0.0,
    backfill_lag_months: int = 2,
    extra_departures: list[tuple[int, float]] | None = None,
    extra_hires: list[tuple[int, float]] | None = None,
) -> list[float]:
    """Expected ramp-weighted FTE for months 1..n_months.

    Cohorts hold (headcount, tenure in months at month 1). Each month every cohort
    loses `monthly_attrition` of its headcount; leavers are backfilled
    `backfill_lag_months` later as tenure-0 hires. `extra_departures` removes fully
    ramped people (oldest cohort first) in a given month; `extra_hires` adds tenure-0
    hires starting in a given month. Month indices are 1-based.
    """
    extra_departures = extra_departures or []
    extra_hires = extra_hires or []
    cohorts = [[1.0, float(t)] for t in tenures]
    leavers_by_month: dict[int, float] = {}
    out = []
    for m in range(1, n_months + 1):
        if m > 1:
            for c in cohorts:
                c[1] += 1
        # attrition (applies from month 2 onward) and scheduled departures
        if m > 1:
            lost = 0.0
            for c in cohorts:
                l = c[0] * monthly_attrition
                c[0] -= l
                lost += l
            leavers_by_month[m] = lost
        for mm, k in extra_departures:
            if mm == m:
                remaining = float(k)
                for c in sorted(cohorts, key=lambda c: -c[1]):
                    take = min(c[0], remaining)
                    c[0] -= take
                    remaining -= take
                    if remaining <= 0:
                        break
        back = leavers_by_month.get(m - backfill_lag_months, 0.0) if monthly_attrition > 0 else 0.0
        if back > 0:
            cohorts.append([back, 0.0])
        for mm, k in extra_hires:
            if mm == m:
                cohorts.append([float(k), 0.0])
        out.append(sum(c[0] * C.ramp_factor(c[1]) for c in cohorts))
    return out


def run(monthly: pd.DataFrame, forecast: pd.DataFrame, roster: pd.DataFrame, as_of: date) -> dict:
    m = monthly.copy()
    m["month_start"] = pd.to_datetime(m["month_start"])
    recent = m.tail(C.AHT_WINDOW_MONTHS)
    aht_hours = float((recent["aht_min"] * recent["alerts_closed"]).sum() / recent["alerts_closed"].sum() / 60)
    backlog_now = float(m["backlog_eom"].iloc[-1])

    # Roster at the last month's first of next month = first forecast month.
    first_fc = pd.to_datetime(forecast["month_start"]).iloc[0]
    r = roster.copy()
    r["hire_date"] = pd.to_datetime(r["hire_date"])
    r["term_date"] = pd.to_datetime(r["term_date"])
    mid = first_fc + pd.Timedelta(days=14)
    active = r[(r["hire_date"] <= mid) & (r["term_date"].isna() | (r["term_date"] > mid))]
    tenures = ((mid - active["hire_date"]).dt.days / C.DAYS_PER_MONTH).apply(np.floor).tolist()
    n = len(forecast)

    avail = {
        "Base": project_available_fte(tenures, n, C.BASE_ATTRITION, C.BASE_BACKFILL_LAG_MONTHS),
        "Rule launch (+20% volume)": project_available_fte(tenures, n, C.BASE_ATTRITION, C.BASE_BACKFILL_LAG_MONTHS),
        "Attrition shock": project_available_fte(
            tenures, n, C.BASE_ATTRITION, C.BASE_BACKFILL_LAG_MONTHS,
            extra_departures=C.ATTRITION_SCENARIO, extra_hires=C.ATTRITION_SCENARIO_HIRES,
        ),
    }
    rows = []
    for scen, av in avail.items():
        for k, (_, fr) in enumerate(forecast.iterrows(), start=1):
            ms = pd.to_datetime(fr["month_start"])
            vol = fr["forecast"]
            if scen.startswith("Rule launch") and k >= C.VOLUME_SCENARIO_START:
                vol *= 1 + C.VOLUME_SCENARIO_UPLIFT
            ph = productive_hours_per_fte(business_days_in_month(ms))
            req = required_fte(vol, aht_hours, ph)
            rows.append(
                {
                    "scenario": scen,
                    "month_start": ms,
                    "volume": vol,
                    "aht_hours": aht_hours,
                    "productive_hours_per_fte": ph,
                    "required_fte": req,
                    "available_fte": av[k - 1],
                    "gap_fte": req - av[k - 1],
                    "backlog_clearance_fte": backlog_now * aht_hours / (C.BACKLOG_CLEARANCE_MONTHS * ph),
                }
            )
    out = pd.DataFrame(rows)
    out["gap_incl_backlog_fte"] = out["gap_fte"] + out["backlog_clearance_fte"]
    meta = {"aht_hours": aht_hours, "starting_headcount": len(active), "backlog_now": backlog_now}
    return {"table": out, "meta": meta}


def main() -> None:
    monthly = pd.read_csv(C.OUT_DIR / "mart_monthly.csv")
    fc = pd.read_csv(C.OUT_DIR / "forecast.csv")
    roster = pd.read_csv(C.RAW_DIR / "investigators.csv")
    as_of = pd.to_datetime(monthly["month_end"]).iloc[-1].date()
    res = run(monthly, fc, roster, as_of)
    res["table"].to_csv(C.OUT_DIR / "capacity.csv", index=False)
    (C.OUT_DIR / "capacity_meta.json").write_text(json.dumps(res["meta"], indent=2))
    t = res["table"]
    print(t.groupby("scenario")["gap_fte"].agg(["mean", "max"]).round(2))


if __name__ == "__main__":
    main()
