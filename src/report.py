"""Generate reports/kpi_kri_memo.md from model outputs. Every number is computed here.

Run: python -m src.report
"""
from __future__ import annotations

import json

import pandas as pd

from . import config as C
from .forecast import shock_start_month


def fmt(metric_id: str, unit: str, v) -> str:
    if v is None or pd.isna(v):
        return "n/a"
    if unit == "pct":
        return f"{v:.1%}"
    if unit == "min":
        return f"{v:.1f}"
    if unit == "cases":
        return f"{v:.2f}"
    return f"{v:,.0f}"


def threshold_text(r) -> str:
    if r["direction"] == "monitor" or pd.isna(r["amber"]):
        return "trend only"
    f = lambda x: fmt(r["metric_id"], r["unit"], x)
    if r["direction"] == "higher_is_worse":
        return f"amber >= {f(r['amber'])}, red >= {f(r['red'])}"
    return f"amber < {f(r['amber'])}, red < {f(r['red'])}"


def build() -> str:
    sc = pd.read_csv(C.OUT_DIR / "mart_scorecard.csv")
    m = pd.read_csv(C.OUT_DIR / "mart_monthly.csv", parse_dates=["month_start"])
    scen = pd.read_csv(C.OUT_DIR / "mart_scenario_kpis.csv")
    fc = pd.read_csv(C.OUT_DIR / "forecast.csv", parse_dates=["month_start"])
    cap = pd.read_csv(C.OUT_DIR / "capacity.csv", parse_dates=["month_start"])
    fs = json.loads((C.OUT_DIR / "forecast_summary.json").read_text())
    cm = json.loads((C.OUT_DIR / "capacity_meta.json").read_text())

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
    all6 = scen[scen["period"] == "last_6m"]
    new_hours_share = new["handle_hours"] / all6["handle_hours"].sum()
    new_alert_share = new["alerts_closed"] / all6["alerts_closed"].sum()

    # scorecard table
    rows = []
    for _, r in sc.iterrows():
        rows.append(
            f"| {r['metric_name']} | {r['metric_type']} | {fmt(r['metric_id'], r['unit'], r['value'])} | "
            f"{fmt(r['metric_id'], r['unit'], r['prior_value'])} | {threshold_text(r)} | {r['rag']} |"
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
            f"| {s} | {d['gap_fte'].mean():+.1f} | {pk['gap_fte']:+.1f} ({pk['month_start']:%b %Y}) | "
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
        return sc.set_index("metric_id").loc[mid, "value"]

    # sensitivity: FTE freed by a 10% cut in the new rule's alert volume (arithmetic only)
    monthly_new_hours = new["handle_hours"] / 6
    avg_ph = cap["productive_hours_per_fte"].mean()
    fte_per_10pct = 0.10 * monthly_new_hours / avg_ph

    memo = f"""# AML Alert Operations: KPI/KRI Memo ({asof})

**To:** Head of AML Operations | **From:** Operations Performance & Analytics | **Data:** synthetic, illustrative only (seeded simulation of a {int(m['headcount_mid'].iloc[0])}-investigator alert queue; no real institution's figures or rates)

## 1. Current state

- The alert backlog stands at **{v('backlog_eom'):,.0f}** open alerts at {asof} month end (red; threshold {C.THRESHOLDS[2][6]:,}). It peaked at **{peak['backlog_eom']:,.0f}** in {peak['month_start']:%B %Y} and has fallen since.
- **{v('pct_within_sla'):.1%}** of alerts closed in {asof} met their SLA (red; target 95%). The SLA rate held near 100% until the backlog began to form after the {launch:%B %Y} detection-rule launch.
- Open alerts aged over 30 days are **{v('open_gt30_pct'):.1%}** of the backlog; High-risk alerts past SLA are **{v('high_overdue_pct'):.1%}** of open High-risk alerts ({last['high_overdue_open']:,.0f} of {last['high_open']:,.0f}).

## 2. KPI/KRI scorecard ({asof}, with prior month)

| Metric | Type | {asof[:3]} | Prior month | Threshold | RAG |
|---|---|---|---|---|---|
{table}

Definitions, grain and thresholds are in `docs/metric_definitions.md`. Metrics marked "trend only" have no policy threshold in this exercise.

## 3. Drivers

- **Volume step.** The forecast model estimates the {launch:%B %Y} rule launch added about **{fs['launch_effect_alerts_per_month']:,.0f} alerts per month** on top of a trend of {fs['trend_alerts_per_month']:,.1f} alerts per month.
- **Low-yield alerts.** The new rule ({C.SHOCK_SCENARIO}) was {new_alert_share:.0%} of alerts closed and {new_hours_share:.0%} of handle hours over the last six months. Its false-positive rate is {1 - new['escalation_rate']:.1%} (other rules: {old_fp:.1%}) and its SAR conversion is {new['sar_conversion_rate']:.1%}.
- **Throughput shortfall.** Created alerts exceeded closures in {len(shortfall_months)} of {len(post)} months since launch, adding {net_inflow:,} alerts net. Average handle time rose from {m[m['month_start'] < launch]['aht_min'].mean():.1f} to {post['aht_min'].mean():.1f} minutes with the new rule mix.
- **Staffing.** Ramp-weighted FTE averaged {pre_fte:.1f} before launch and reached a low of {fte_low['effective_fte']:.1f} in {fte_low['month_start']:%B %Y} (departures plus new-hire ramp-up). It was {last['effective_fte']:.1f} in {asof}.

## 4. Volume forecast

Model: OLS on linear trend, annual seasonality (one sine/cosine pair) and a post-launch step. Holdout backtest (fit on first {fs['train_months']} months, test on last {fs['holdout_months']}): **MAPE {fs['backtest_mape']:.1%}**.

| Month | Forecast alerts | 95% prediction interval |
|---|---|---|
{frows}

## 5. Capacity gap

Required FTE = forecast volume x handle time ({cm['aht_hours'] * 60:.1f} min, trailing {C.AHT_WINDOW_MONTHS} months) / productive hours per FTE (business days x {C.HOURS_PER_DAY} h x {C.UTILIZATION:.0%} utilization x {1 - C.SHRINKAGE:.0%} attendance). Available FTE starts from the current roster of {cm['starting_headcount']} with ramp-up ({', '.join(f'{t}+ mo: {f:.0%}' for t, f in C.RAMP)}) and {C.BASE_ATTRITION:.2%} monthly attrition backfilled after {C.BASE_BACKFILL_LAG_MONTHS} months. Gap = required minus available; positive is a shortfall.

| Scenario | Mean gap (FTE) | Peak gap (FTE) | Months short | Peak gap incl. backlog clearance |
|---|---|---|---|---|
{crows}

Backlog clearance adds {clear:.1f} FTE if the current backlog is to be worked off over {C.BACKLOG_CLEARANCE_MONTHS} months. Scenarios: +{C.VOLUME_SCENARIO_UPLIFT:.0%} volume from forecast month {C.VOLUME_SCENARIO_START}; {sum(k for _, k in C.ATTRITION_SCENARIO)} additional departures (months {', '.join(str(a) for a, _ in C.ATTRITION_SCENARIO)}) with {sum(k for _, k in C.ATTRITION_SCENARIO_HIRES)} hires in month {C.ATTRITION_SCENARIO_HIRES[0][0]}.

## 6. Recommendations

1. **Review the {C.SHOCK_SCENARIO} rule's tuning.** At a {1 - new['escalation_rate']:.0%} false-positive rate it consumes {new_hours_share:.0%} of handle hours. Each 10% reduction in its alert volume frees about {fte_per_10pct:.1f} FTE of capacity (arithmetic on current handle hours, not a forecast of what tuning would achieve).
2. **Start hiring against the base-case peak.** The base case peaks at a {base_pk['gap_fte']:+.1f} FTE gap in {base_pk['month_start']:%B %Y} ({base_pk['gap_incl_backlog_fte']:+.1f} with backlog clearance). New hires take {C.RAMP[-1][0]} months to reach full productivity, so hires would need to start by {(base_pk['month_start'] - pd.DateOffset(months=C.RAMP[-1][0])):%B %Y} to be fully ramped at the peak. The +{C.VOLUME_SCENARIO_UPLIFT:.0%} volume scenario peaks at {launch_pk['gap_fte']:+.1f} FTE, so a decision on that rule launch should come with a staffing plan.
3. **Turn the KRIs into escalation triggers and fix High-risk routing.** Link amber/red KRI states to named actions (overtime, queue reallocation). Prioritize clearing the {last['high_overdue_open']:,.0f} High-risk alerts past SLA, and check whether High-risk alerts are being routed to the general queue.

## 7. Limitations

- All data is simulated from stated assumptions (`docs/simulation_assumptions.md`); results show the method, not a real institution's performance.
- The forecast uses {len(m)} monthly points and a single seasonal harmonic; the interval reflects model error, not future rule launches or policy changes.
- The capacity model uses average handle time and a single utilization figure. It ignores skill mix, holidays, and the case-stage workload after escalation.
- Thresholds are placeholders chosen for illustration, not regulatory or policy limits.
"""
    return memo


def main() -> None:
    C.REPORT_DIR.mkdir(exist_ok=True)
    (C.REPORT_DIR / "kpi_kri_memo.md").write_text(build())
    print("Wrote", C.REPORT_DIR / "kpi_kri_memo.md")


if __name__ == "__main__":
    main()
