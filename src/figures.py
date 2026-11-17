"""Static figures from model outputs. Run: python -m src.figures"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from . import config as C
from .forecast import shock_start_month

BLUE, ORANGE, GREY, GREEN, RED, PURPLE = "#2b6cb0", "#dd6b20", "#718096", "#2f855a", "#c53030", "#6b46c1"
plt.rcParams.update({
    "figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9, "axes.titlesize": 10,
    "axes.titleweight": "bold",
})
NOTE = "Synthetic data (seeded simulation), illustrative only"


def _fmt(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def _launch(ax):
    ax.axvline(shock_start_month(), color=GREY, ls="--", lw=1)


def kpi_panel(m: pd.DataFrame) -> None:
    x = pd.to_datetime(m["month_start"])
    fig, axs = plt.subplots(2, 3, figsize=(13, 6.6))
    a = axs[0, 0]
    a.plot(x, m["alerts_created"], color=BLUE, label="Created")
    a.plot(x, m["alerts_closed"], color=ORANGE, label="Closed")
    a.set_title("Alert volume per month"); a.legend(frameon=False)
    a = axs[0, 1]
    a.plot(x, m["backlog_eom"], color=BLUE)
    for t, c in [(1500, ORANGE), (2500, RED)]:
        a.axhline(t, color=c, ls=":", lw=1.2)
    a.text(x.iloc[0], 1560, "amber 1,500", color=ORANGE, fontsize=8)
    a.text(x.iloc[0], 2560, "red 2,500", color=RED, fontsize=8)
    a.set_title("Open backlog at month end")
    a = axs[0, 2]
    a.plot(x, m["pct_within_sla"] * 100, color=BLUE)
    for t, c in [(95, ORANGE), (90, RED)]:
        a.axhline(t, color=c, ls=":", lw=1.2)
    a.set_ylim(0, 105); a.set_title("% closed within SLA")
    a = axs[1, 0]
    a.plot(x, m["aht_min"], color=PURPLE)
    a.set_title("Average handle time (min)")
    a = axs[1, 1]
    a.plot(x, m["escalation_rate"] * 100, color=BLUE, label="Escalation rate")
    a.plot(x, m["sar_conversion_rate"] * 100, color=GREEN, label="SAR conversion (closed cases)")
    a.set_title("Escalation and SAR conversion (%)"); a.legend(frameon=False, fontsize=8)
    a = axs[1, 2]
    a.plot(x, m["cases_per_inv_week"], color=BLUE, label="Cases / investigator / week")
    a.set_title("Cases opened per investigator per week")
    for a in axs.flat:
        _fmt(a); _launch(a)
    axs[0, 0].text(shock_start_month(), axs[0, 0].get_ylim()[0], " rule launch", color=GREY, fontsize=8, va="bottom")
    fig.suptitle("AML alert operations: KPI/KRI trends, Jan 2024 to Jun 2026", fontweight="bold", y=0.995)
    fig.text(0.01, 0.005, NOTE, fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(C.FIG_DIR / "kpi_trend_panel.png"); plt.close(fig)


def aging(ag: pd.DataFrame, m: pd.DataFrame) -> None:
    last = ag["month_start"].max()
    cur = ag[ag["month_start"] == last]
    order = ["0-7", "8-14", "15-30", "31-60", ">60"]
    piv = cur.pivot_table(index="aging_bucket", columns="risk_band", values="open_alerts", aggfunc="sum").reindex(order).fillna(0)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.1, 1]})
    a = axs[0]
    bottom = pd.Series(0.0, index=piv.index)
    for band, col in [("High", RED), ("Medium", ORANGE), ("Low", BLUE)]:
        if band in piv:
            a.bar(piv.index, piv[band], bottom=bottom, color=col, label=band)
            bottom += piv[band]
    a.set_title(f"Open alerts by age, {pd.to_datetime(last):%b %Y} month end")
    a.set_xlabel("Age (days)"); a.set_ylabel("Open alerts"); a.legend(title="Risk band", frameon=False)
    a = axs[1]
    x = pd.to_datetime(m["month_start"])
    a.plot(x, m["open_gt30_pct"] * 100, color=BLUE, label="> 30 days")
    a.plot(x, m["open_gt60_pct"] * 100, color=ORANGE, label="> 60 days")
    a.set_title("Share of open alerts aged over 30 / 60 days (%)"); a.legend(frameon=False)
    _fmt(a); _launch(a)
    fig.text(0.01, 0.005, NOTE, fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(C.FIG_DIR / "aging_distribution.png"); plt.close(fig)


def forecast(fit: pd.DataFrame, bt: pd.DataFrame, fc: pd.DataFrame, mape: float) -> None:
    fig, a = plt.subplots(figsize=(10, 4.6))
    a.plot(pd.to_datetime(fit["month_start"]), fit["actual"], color=BLUE, marker="o", ms=3, label="Actual")
    a.plot(pd.to_datetime(bt["month_start"]), bt["predicted"], color=ORANGE, marker="s", ms=3,
           label=f"Backtest (fit on first 24 months), MAPE {mape:.1%}")
    a.plot(pd.to_datetime(fc["month_start"]), fc["forecast"], color=GREEN, marker="o", ms=3, label="6-month forecast")
    a.fill_between(pd.to_datetime(fc["month_start"]), fc["lower_95"], fc["upper_95"], color=GREEN, alpha=0.2, label="95% prediction interval")
    _launch(a); a.text(shock_start_month(), a.get_ylim()[0] + 40, " rule launch", color=GREY, fontsize=8)
    a.set_ylabel("Alerts created per month"); a.set_title("Monthly alert volume: actual, backtest and forecast")
    a.legend(frameon=False, loc="upper left", fontsize=8)
    a.xaxis.set_major_locator(mdates.MonthLocator(interval=3)); a.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.text(0.01, 0.005, NOTE, fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(C.FIG_DIR / "forecast_vs_actual.png"); plt.close(fig)


def capacity(cap: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    colors = {"Base": BLUE, "Rule launch (+20% volume)": ORANGE, "Attrition shock": PURPLE}
    a = axs[0]
    g = {k: d.sort_values("month_start") for k, d in cap.groupby("scenario", sort=False)}
    x = [pd.to_datetime(v).strftime("%b %y") for v in g["Base"]["month_start"]]
    a.plot(x, g["Base"]["required_fte"], color=BLUE, marker="o", ms=3, label="Required, base volume")
    a.plot(x, g["Rule launch (+20% volume)"]["required_fte"], color=ORANGE, marker="o", ms=3, label="Required, +20% volume")
    a.plot(x, g["Base"]["available_fte"], color=BLUE, ls="--", label="Available, base staffing")
    a.plot(x, g["Attrition shock"]["available_fte"], color=PURPLE, ls="--", label="Available, attrition shock")
    a.set_title("Required vs available investigator FTE"); a.set_ylabel("FTE")
    a.legend(frameon=False, fontsize=8)
    a = axs[1]
    scen = list(colors)
    months = sorted(cap["month_start"].unique())
    w = 0.26
    for k, s in enumerate(scen):
        d = cap[cap["scenario"] == s].sort_values("month_start")
        a.bar([i + (k - 1) * w for i in range(len(d))], d["gap_fte"], width=w, color=colors[s], label=s)
    a.axhline(0, color="black", lw=0.8)
    a.set_xticks(range(len(months))); a.set_xticklabels([pd.to_datetime(x).strftime("%b %y") for x in months])
    a.set_title("Staffing gap by month (positive = shortfall)"); a.set_ylabel("FTE"); a.legend(frameon=False, fontsize=8)
    fig.text(0.01, 0.005, NOTE + "; gap excludes backlog clearance", fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(C.FIG_DIR / "capacity_gap.png"); plt.close(fig)


def main() -> None:
    C.FIG_DIR.mkdir(parents=True, exist_ok=True)
    import json
    m = pd.read_csv(C.OUT_DIR / "mart_monthly.csv")
    kpi_panel(m)
    aging(pd.read_csv(C.OUT_DIR / "mart_aging_snapshot.csv"), m)
    s = json.loads((C.OUT_DIR / "forecast_summary.json").read_text())
    forecast(pd.read_csv(C.OUT_DIR / "fitted.csv"), pd.read_csv(C.OUT_DIR / "backtest.csv"),
             pd.read_csv(C.OUT_DIR / "forecast.csv"), s["backtest_mape"])
    capacity(pd.read_csv(C.OUT_DIR / "capacity.csv"))
    print("Figures written to", C.FIG_DIR)


if __name__ == "__main__":
    main()
