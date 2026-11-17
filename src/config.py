"""Shared constants. Every simulation and capacity assumption lives here.

All values are illustrative and synthetic. See docs/simulation_assumptions.md.
"""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_DIR = ROOT / "outputs"
SQL_DIR = ROOT / "sql"
REPORT_DIR = ROOT / "reports"
FIG_DIR = REPORT_DIR / "figures"
DB_PATH = DATA_DIR / "aml.duckdb"

SEED = 42

# ---- Timeline -------------------------------------------------------------
START_DATE = date(2024, 1, 1)
N_MONTHS = 30                      # 2024-01 .. 2026-06
SHOCK_MONTH_INDEX = 17             # 0-based; 2025-06 = new detection rule launch
SHOCK_SCENARIO = "Network Link Analysis"
SHOCK_VOLUME_SHARE = 0.15          # new-rule alerts as a share of baseline volume

# ---- Volume model ---------------------------------------------------------
BASE_VOLUME = 3050                 # baseline alerts in month 0
TREND_PER_MONTH = 12               # linear trend, alerts per month
SEASON_AMP_1 = 0.07                # first harmonic, peak in December
SEASON_AMP_2 = 0.025               # second harmonic
NOISE_SIGMA = 0.03                 # lognormal noise on monthly volume

# ---- Productive time (shared by simulator and capacity model) ------------
HOURS_PER_DAY = 7.5
UTILIZATION = 0.80                 # share of paid hours spent on case work
SHRINKAGE = 0.05                   # share of working days lost to absence/leave
PRODUCTIVE_MIN_PER_DAY = HOURS_PER_DAY * 60 * UTILIZATION   # 360

# New hire ramp: (months of tenure at or above, productivity factor)
RAMP = [(0, 0.40), (1, 0.60), (2, 0.80), (3, 1.00)]
DAYS_PER_MONTH = 30.4375


def ramp_factor(tenure_months: float) -> float:
    f = RAMP[0][1]
    for t, v in RAMP:
        if tenure_months >= t:
            f = v
    return f


# ---- Staffing -------------------------------------------------------------
N_INVESTIGATORS_START = 25
MONTHLY_ATTRITION = 0.0125         # per investigator per month
BACKFILL_LAG_DAYS = (30, 75)       # uniform range from departure to start date
# (date, count) of additional departures: team reorganization
ATTRITION_CLUSTER = (date(2026, 3, 2), 3)
# (date, count) of approved additional hires after the rule launch
PLANNED_HIRES = [(date(2025, 10, 1), 2), (date(2026, 4, 1), 2)]

# ---- Alert attributes -----------------------------------------------------
SLA_DAYS = {"High": 5, "Medium": 10, "Low": 20}
BAND_ESC_MULT = {"High": 2.0, "Medium": 1.0, "Low": 0.5}
BAND_SAR_MULT = {"High": 1.2, "Medium": 1.0, "Low": 0.8}
BAND_SCORE_RANGE = {"Low": (0, 39), "Medium": (40, 69), "High": (70, 100)}

# scenario: share of baseline volume, handle-time median (min), lognormal sigma,
# base escalation prob, SAR prob given case, risk band probs (Low, Medium, High)
SCENARIOS = {
    "Cash Structuring":        dict(share=0.22, median=40, sigma=0.45, esc=0.12, sar=0.45, bands=(0.45, 0.40, 0.15)),
    "Rapid Fund Movement":     dict(share=0.18, median=55, sigma=0.50, esc=0.15, sar=0.40, bands=(0.35, 0.40, 0.25)),
    "High-Risk Geography":     dict(share=0.15, median=45, sigma=0.40, esc=0.08, sar=0.30, bands=(0.40, 0.40, 0.20)),
    "Unusual Wire Activity":   dict(share=0.15, median=60, sigma=0.50, esc=0.14, sar=0.42, bands=(0.30, 0.45, 0.25)),
    "Profile Mismatch":        dict(share=0.30, median=35, sigma=0.40, esc=0.06, sar=0.25, bands=(0.60, 0.32, 0.08)),
    "Network Link Analysis":   dict(share=0.00, median=50, sigma=0.45, esc=0.05, sar=0.20, bands=(0.50, 0.35, 0.15)),
}
BASELINE_SCENARIOS = [k for k in SCENARIOS if k != SHOCK_SCENARIO]

INVESTIGATOR_SPEED_SIGMA = 0.10    # lognormal spread of individual speed
CASE_DAYS_MEDIAN = 14
CASE_DAYS_SIGMA = 0.5

# ---- Metric thresholds (RAG) ---------------------------------------------
# metric_id, name, type, unit, direction, amber, red
THRESHOLDS = [
    ("alerts_created",       "Alert volume (month)",                  "KPI", "alerts", "monitor",          None,  None),
    ("alerts_closed",        "Alerts closed (month)",                 "KPI", "alerts", "monitor",          None,  None),
    ("backlog_eom",          "Open alert backlog (month end)",        "KRI", "alerts", "higher_is_worse",  1500,  2500),
    ("pct_within_sla",       "% closed within SLA",                   "KPI", "pct",    "higher_is_better", 0.95,  0.90),
    ("aht_min",              "Average handle time",                   "KPI", "min",    "monitor",          None,  None),
    ("alerts_closed_per_inv_week", "Alerts closed per investigator per week", "KPI", "per_week", "monitor", None,  None),
    ("escalation_rate",      "Escalation rate",                       "KPI", "pct",    "monitor",          None,  None),
    ("sar_conversion_rate",  "SAR conversion rate (closed cases)",    "KPI", "pct",    "monitor",          None,  None),
    ("fp_rate",              "False-positive rate (complement of escalation rate)", "KPI", "pct",    "monitor",          None,  None),
    ("sla_breach_rate",      "SLA breach rate (complement of % within SLA)", "KRI", "pct",    "higher_is_worse",  0.05,  0.10),
    ("open_gt30_pct",        "Open alerts aged > 30 days (% of open)","KRI", "pct",    "higher_is_worse",  0.05,  0.10),
    ("open_gt60_pct",        "Open alerts aged > 60 days (% of open)","KRI", "pct",    "higher_is_worse",  0.02,  0.05),
    ("high_overdue_pct",     "High-risk open alerts past SLA (% of High-risk open)", "KRI", "pct", "higher_is_worse", 0.10, 0.25),
    # Placeholder thresholds, not a regulatory limit.
    ("sar_clock_overdue_pct", "Open cases >30 days from alert detection (% of open cases)", "KRI", "pct", "higher_is_worse", 0.10, 0.25),
]

# Calendar days from alert detection after which an open case counts toward the
# SAR-timeliness KRI. Mirrors the US 30-day filing window (31 CFR 1020.320(b)(3));
# the thresholds above are placeholders.
SAR_CLOCK_DAYS = 30

def threshold(metric_id: str) -> tuple[float | None, float | None]:
    """(amber, red) for a metric id."""
    for t in THRESHOLDS:
        if t[0] == metric_id:
            return t[5], t[6]
    raise KeyError(metric_id)


# ---- Forecast / capacity --------------------------------------------------
HOLDOUT_MONTHS = 6
FORECAST_MONTHS = 6
VOLUME_SCENARIO_UPLIFT = 0.20      # +20% volume from forecast month 2
VOLUME_SCENARIO_START = 2
ATTRITION_SCENARIO = [(2, 3), (4, 2)]   # (forecast month, FTE leaving)
ATTRITION_SCENARIO_HIRES = [(5, 2)]     # backfill hires starting
BASE_ATTRITION = MONTHLY_ATTRITION
BASE_BACKFILL_LAG_MONTHS = 2
BACKLOG_CLEARANCE_MONTHS = 6
AHT_WINDOW_MONTHS = 6
