"""Generate reports/kpi_kri_memo.md from model outputs. Every number is computed here.

Run: python -m src.report
"""
from __future__ import annotations

import json

import pandas as pd

from . import config as C
from .forecast import shock_start_month


def fmt(unit: str, v) -> str:
    if v is None or pd.isna(v):
        return "n/a"
    if unit == "pct":
        return f"{v:.1%}"
    if unit == "min":
        return f"{v:.1f}"
    if unit == "per_week":
        return f"{v:.1f}"
    return f"{v:,.0f}"


def threshold_text(r) -> str:
    if r["direction"] == "monitor" or pd.isna(r["amber"]):
        return "trend only"
    f = lambda x: fmt(r["unit"], x)
    if r["direction"] == "higher_is_worse":
        return f"amber >= {f(r['amber'])}, red >= {f(r['red'])}"
    return f"amber < {f(r['amber'])}, red < {f(r['red'])}"


def metric_row(sc: pd.DataFrame, metric_id: str):
    return sc.set_index("metric_id").loc[metric_id]


def productivity_summary(inv: pd.DataFrame, last_month: pd.Timestamp) -> tuple[str, str]:
    """Table of alerts closed per productive hour and per week by tenure band (last 6 months)
    and a sentence on the spread across fully ramped investigators."""
    d = inv.copy()
    d["month_start"] = pd.to_datetime(d["month_start"])
    d = d[(d["month_start"] > last_month - pd.DateOffset(months=C.AHT_WINDOW_MONTHS))
          & d["tenure_months"].notna() & (d["business_days_employed"] >= 15)].copy()
    d["productive_hours"] = d["business_days_employed"] * C.HOURS_PER_DAY * C.UTILIZATION * (1 - C.SHRINKAGE)
    d["per_hour"] = d["alerts_closed"] / d["productive_hours"]
    d["band"] = pd.cut(d["tenure_months"], [-1, 2, 11, 1e9], labels=["0-2 months", "3-11 months", "12+ months"])
    rows = []
    for b, g in d.groupby("band", observed=True):
        rows.append(
            f"| {b} | {len(g)} | {g['per_hour'].median():.2f} | {g['alerts_closed_per_week'].median():.1f} | "
            f"{g['alerts_closed_per_week'].quantile(0.1):.1f} to {g['alerts_closed_per_week'].quantile(0.9):.1f} |"
        )
    table = "\n".join(rows)
    ramped = d[d["tenure_months"] >= C.RAMP[-1][0]].groupby("investigator_id")["alerts_closed_per_week"].mean()
    spread = (
        f"Across the {len(ramped)} investigators with at least {C.RAMP[-1][0]} months of tenure, average alerts closed per week "
        f"over the same window ranged from {ramped.min():.1f} to {ramped.max():.1f} "
        f"(median {ramped.median():.1f}; highest is {ramped.max() / ramped.min():.2f}x the lowest)."
    )
    return table, spread


def build() -> str:
    sc = pd.read_csv(C.OUT_DIR / "mart_scorecard.csv")
    m = pd.read_csv(C.OUT_DIR / "mart_monthly.csv", parse_dates=["month_start"])
    scen = pd.read_csv(C.OUT_DIR / "mart_scenario_kpis.csv")
    fc = pd.read_csv(C.OUT_DIR / "forecast.csv", parse_dates=["month_start"])
    cap = pd.read_csv(C.OUT_DIR / "capacity.csv", parse_dates=["month_start"])
    fs = json.loads((C.OUT_DIR / "forecast_summary.json").read_text())
    cm = json.loads((C.OUT_DIR / "capacity_meta.json").read_text())
    inv = pd.read_csv(C.OUT_DIR / "mart_investigator_month.csv")

    last = m.iloc[-1]
    asof = f"{last['month_start']:%B %Y}"
    launch = shock_start_month()
    post = m[m["month_start"] >= launch]
    peak = m.loc[m["backlog_eom"].idxmax()]
    first_backlog = m[(m["backlog_eom"] > 0) & (m["month_start"] >= launch)].iloc[0]
    shortfall_months = post[post["alerts_created"] > post["alerts_closed"]]
    net_inflow = int((post["alerts_created"] - post["alerts_closed"]).sum())
    fte_low = m[m["month_start"] >= launch].loc[lambda d: d["effective_fte"].idxmin()]
    pre_fte = m[m["month_start"] < launch]["effective_fte"].mean()

    new = scen[(scen["period"] == "last_6m") & (scen["scenario"] == C.SHOCK_SCENARIO)].iloc[0]
    old = scen[(scen["period"] == "last_6m") & (scen["scenario"] != C.SHOCK_SCENARIO)]
    old_fp = 1 - (old["escalation_rate"] * old["alerts_closed"]).sum() / old["alerts_closed"].sum()
    old_aht = (old["aht_min"] * old["alerts_closed"]).sum() / old["alerts_closed"].sum()
    old_sar = (old["sar_conversion_rate"] * old["cases_closed"]).sum() / old["cases_closed"].sum()
    all6 = scen[scen["period"] == "last_6m"]
    new_hours_share = new["handle_hours"] / all6["handle_hours"].sum()
    new_alert_share = new["alerts_closed"] / all6["alerts_closed"].sum()

    # scorecard table
    rows = []
    for _, r in sc.iterrows():
        rows.append(
            f"| {r['metric_name']} | {r['metric_type']} | {fmt(r['unit'], r['value'])} | "
            f"{fmt(r['unit'], r['prior_value'])} | {threshold_text(r)} | {r['rag']} |"
        )
    table = "\n".join(rows)

    # forecast table
    frows = "\n".join(
        f"| {r['month_start']:%b %Y} | {r['forecast']:,.0f} | {r['lower_95']:,.0f} to {r['upper_95']:,.0f} |"
        for _, r in fc.iterrows()
    )

    # capacity summary
    crows = []
    for s, d in cap.groupby("scenario", sort=False):
        pk = d.loc[d["gap_fte"].idxmax()]
        short = (d["gap_fte"] > 0).sum()
        crows.append(
            f"| {s} | {d['gap_fte'].mean():+.1f} | {pk['gap_fte']:+.1f} ({pk['month_start']:%b %Y}, {pk['business_days']} business days) | "
            f"{d['gap_fte_3mo_avg'].max():+.1f} ({d.loc[d['gap_fte_3mo_avg'].idxmax(), 'month_start']:%b %Y}) | "
            f"{short} of {len(d)} | {pk['gap_incl_backlog_fte']:+.1f} |"
        )
    crows = "\n".join(crows)
    base = cap[cap["scenario"] == "Base"]
    base_pk = base.loc[base["gap_fte"].idxmax()]
    clear = base["backlog_clearance_fte"].iloc[0]
    launch_scen = cap[cap["scenario"].str.startswith("Rule")]
    launch_pk = launch_scen.loc[launch_scen["gap_fte"].idxmax()]
    attr_scen = cap[cap["scenario"] == "Attrition shock"]
    attr_pk = attr_scen.loc[attr_scen["gap_fte"].idxmax()]

    def v(mid):
        return metric_row(sc, mid)["value"]

    sar_pct = v("sar_clock_overdue_pct")
    prod_table, prod_spread = productivity_summary(inv, last["month_start"])
    base_mean = base["gap_fte"].mean()
    launch_short = int((launch_scen["gap_fte"] > 0).sum())
    balance = "roughly balanced on average" if abs(base_mean) < 1 else (
        "short on average" if base_mean > 0 else "above requirement on average")
    base_roll = base.loc[base["gap_fte_3mo_avg"].idxmax()]

    # SLA attainment vs backlog, last two months of the backlog decline
    prev = m.iloc[-3]
    sla_explained = (last["backlog_eom"] < prev["backlog_eom"] and last["pct_within_sla"] < prev["pct_within_sla"]
                     and last["avg_age_at_close_days"] > prev["avg_age_at_close_days"])
    sla_why = (
        f" SLA attainment fell from {prev['pct_within_sla']:.1%} in {prev['month_start']:%B} to {last['pct_within_sla']:.1%} while the "
        f"backlog fell from {prev['backlog_eom']:,.0f} to {last['backlog_eom']:,.0f}: alerts closed in {last['month_start']:%B} were on "
        f"average {last['avg_age_at_close_days']:.1f} days old at closure ({prev['avg_age_at_close_days']:.1f} in {prev['month_start']:%B}), "
        "so the team is now closing older alerts that had already breached."
        if sla_explained else ""
    )
    routing = (
        f"- Open High-risk alerts have a median age of {last['median_age_open_high']:.0f} days at {asof} month end, against "
        f"{last['median_age_open_low']:.0f} days for Low-risk alerts. If High-risk work were prioritized, it would be younger; "
        "the equal ages suggest some High-risk alerts are sitting in the general queue."
        if last["median_age_open_high"] >= last["median_age_open_low"] else ""
    )

    # sensitivity: FTE freed by a 10% cut in the new rule's alert volume (arithmetic only)
    monthly_new_hours = new["handle_hours"] / 6
    avg_ph = cap["productive_hours_per_fte"].mean()
    fte_per_10pct = 0.10 * monthly_new_hours / avg_ph

    memo = f"""# KPI/KRI Memo, {asof}

**To:** Head of AML Operations (illustrative) | **From:** Siyuan (David) Zhu | **Data:** synthetic, illustrative only (seeded simulation of a {int(m['headcount_mid'].iloc[0])}-investigator alert queue; no real institution's figures or rates)

## 1. Current state

- The alert backlog stands at **{v('backlog_eom'):,.0f}** open alerts at {asof} month end (red; threshold {C.threshold('backlog_eom')[1]:,}). It peaked at **{peak['backlog_eom']:,.0f}** in {peak['month_start']:%B %Y} and has fallen since.
- **{v('pct_within_sla'):.1%}** of alerts closed in {asof} met their SLA (red; target {C.threshold('pct_within_sla')[0]:.0%}). The SLA rate held near 100% until the backlog began to form after the {launch:%B %Y} detection-rule launch.{sla_why}
- Open alerts aged over 30 days are **{v('open_gt30_pct'):.1%}** of the backlog; High-risk alerts past SLA are **{v('high_overdue_pct'):.1%}** of open High-risk alerts ({last['high_overdue_open']:,.0f} of {last['high_open']:,.0f}).
{routing}
- **{sar_pct:.1%}** of open cases ({last['sar_clock_overdue']:,.0f} of {last['open_cases']:,.0f}) are more than {C.SAR_CLOCK_DAYS} calendar days from alert detection without a decision. This is the SAR-timeliness KRI, based on the US 30-day filing window (31 CFR 1020.320(b)(3)); its thresholds here are placeholders.

## 2. KPI/KRI scorecard ({asof}, with prior month)

| Metric | Type | {asof[:3]} | Prior month | Threshold | RAG |
|---|---|---|---|---|---|
{table}

Definitions, grain and thresholds are in `docs/metric_definitions.md`. Metrics marked "trend only" have no policy threshold in this exercise. SLA breach rate and false-positive rate are the complements of % closed within SLA and of escalation rate (as disposition shares), shown because they carry thresholds or a tuning signal.

## 3. Drivers

- **Volume step.** The forecast model estimates the {launch:%B %Y} rule launch added about **{fs['launch_effect_alerts_per_month']:,.0f} alerts per month** on top of a trend of {fs['trend_alerts_per_month']:,.1f} alerts per month.
- **Low-yield alerts.** The new rule ({C.SHOCK_SCENARIO}) was {new_alert_share:.0%} of alerts closed and {new_hours_share:.0%} of handle hours over the last six months. Its false-positive rate is {1 - new['escalation_rate']:.1%} (other rules: {old_fp:.1%}) and its SAR conversion is {new['sar_conversion_rate']:.1%} (other rules: {old_sar:.1%}).
- **Throughput shortfall.** Created alerts exceeded closures in {len(shortfall_months)} of {len(post)} months since launch, adding {net_inflow:,} alerts net. Average handle time rose from {m[m['month_start'] < launch]['aht_min'].mean():.1f} to {post['aht_min'].mean():.1f} minutes after the launch.
- **Staffing.** Ramp-weighted FTE averaged {pre_fte:.1f} before launch and reached a low of {fte_low['effective_fte']:.1f} in {fte_low['month_start']:%B %Y} (departures plus new-hire ramp-up). It was {last['effective_fte']:.1f} in {asof}.

## 4. Investigator productivity

Alerts closed per investigator by tenure band, last {C.AHT_WINDOW_MONTHS} months (investigator-months with at least 15 business days on the roster). Productive hours = business days x {C.HOURS_PER_DAY} h x {C.UTILIZATION:.0%} x {1 - C.SHRINKAGE:.0%}.

| Tenure band | Investigator-months | Median alerts closed per productive hour | Median alerts closed per week | P10 to P90 per week |
|---|---|---|---|---|
{prod_table}

{prod_spread}

## 5. Volume forecast

Model: OLS on linear trend, annual seasonality (one sine/cosine pair) and a post-launch step. Holdout backtest (fit on first {fs['train_months']} months, test on last {fs['holdout_months']}): **MAPE {fs['backtest_mape']:.1%}**, against {fs['seasonal_naive_mape']:.1%} for a seasonal-naive forecast (same month one year earlier). The model has the same form as the process that generated the data, so its MAPE is flattering.

| Month | Forecast alerts | 95% prediction interval |
|---|---|---|
{frows}

## 6. Capacity gap

Required FTE = forecast volume x handle time ({cm['aht_hours'] * 60:.1f} min, trailing {C.AHT_WINDOW_MONTHS} months) / productive hours per FTE (business days x {C.HOURS_PER_DAY} h x {C.UTILIZATION:.0%} utilization x {1 - C.SHRINKAGE:.0%} attendance). Available FTE starts from the current roster of {cm['starting_headcount']} with ramp-up ({', '.join(f'{t}+ mo: {f:.0%}' for t, f in C.RAMP)}) and {C.BASE_ATTRITION:.2%} monthly attrition backfilled after {C.BASE_BACKFILL_LAG_MONTHS} months. {cm['pending_backfills']} pending backfill hire{'s' if cm['pending_backfills'] != 1 else ''} for recent leavers {'are' if cm['pending_backfills'] != 1 else 'is'} added at the midpoint of the {C.BACKFILL_LAG_DAYS[0]} to {C.BACKFILL_LAG_DAYS[1]} day lag. Gap = required minus available; positive is a shortfall.

| Scenario | Mean gap (FTE) | Peak monthly gap (FTE) | Peak 3-month average gap (FTE, month ending) | Months short | Peak gap incl. backlog clearance |
|---|---|---|---|---|---|
{crows}

Monthly gaps move with business-day counts, so the 3-month average gap is the steadier view. Backlog clearance adds {clear:.1f} FTE if the current backlog is to be worked off over {C.BACKLOG_CLEARANCE_MONTHS} months. Scenarios: +{C.VOLUME_SCENARIO_UPLIFT:.0%} volume from forecast month {C.VOLUME_SCENARIO_START}; {sum(k for _, k in C.ATTRITION_SCENARIO)} additional departures (months {', '.join(str(a) for a, _ in C.ATTRITION_SCENARIO)}) with {sum(k for _, k in C.ATTRITION_SCENARIO_HIRES)} hires in month {C.ATTRITION_SCENARIO_HIRES[0][0]}.

## 7. Recommendations

1. **Review the {C.SHOCK_SCENARIO} rule's tuning.** At a {1 - new['escalation_rate']:.0%} false-positive rate it consumes {new_hours_share:.0%} of handle hours. Each 10% reduction in its alert volume frees about {fte_per_10pct:.1f} FTE of capacity (arithmetic on current handle hours, not a forecast of what tuning would achieve).
2. **Add temporary capacity now and tie permanent hiring to the next rule launch.** Add about {clear:.0f} FTE of temporary capacity (overtime, contractors or loaned staff) for {C.BACKLOG_CLEARANCE_MONTHS} months to clear the backlog. Base-case demand is {balance} ({base_mean:+.1f} FTE) with a {base_pk['gap_fte']:+.1f} FTE peak in {base_pk['month_start']:%B}, a {base_pk['business_days']}-business-day month (the highest 3-month average gap is {base_roll['gap_fte_3mo_avg']:+.1f} FTE), so permanent hiring depends on the next rule launch: the +{C.VOLUME_SCENARIO_UPLIFT:.0%} volume scenario is short in {launch_short} of {len(launch_scen)} months and peaks at {launch_pk['gap_fte']:+.1f} FTE.
3. **Turn the KRIs into escalation triggers and fix High-risk routing.** Link amber/red KRI states to named actions (overtime, queue reallocation). Prioritize clearing the {last['high_overdue_open']:,.0f} High-risk alerts past SLA, and check whether High-risk alerts are being routed to the general queue (section 1). Add the SAR-timeliness KRI to the same trigger set.

## 8. Limitations

- All data is simulated from stated assumptions (`docs/simulation_assumptions.md`); results show the method, not a real institution's performance.
- The forecast uses {len(m)} monthly points and a single seasonal harmonic; the interval reflects model error, not future rule launches or policy changes.
- The capacity model uses average handle time and a single utilization figure. It ignores skill mix and holidays. Case (L2) work uses no investigator capacity in the simulator, and escalated and non-escalated alerts share handle-time distributions.
- Pending backfills are inferred from leavers in the last {C.BACKFILL_LAG_DAYS[1]} days, using the midpoint of the backfill lag range; actual start dates are not in the roster.
- The forecast has the same form as the data-generating process, so its backtest MAPE is flattering; the seasonal-naive comparison in section 5 is a weak baseline that ignores trend and the rule launch.
- Thresholds are placeholders chosen for illustration, not regulatory or policy limits.
"""
    return memo


def main() -> None:
    C.REPORT_DIR.mkdir(exist_ok=True)
    (C.REPORT_DIR / "kpi_kri_memo.md").write_text(build())
    print("Wrote", C.REPORT_DIR / "kpi_kri_memo.md")


if __name__ == "__main__":
    main()
