# Metric definitions

All metrics are computed in DuckDB SQL (`sql/`) on synthetic data. "Month" means calendar month; month-end snapshots count alerts created on or before month end and not yet closed by that date. Thresholds are illustrative placeholders held in `src/config.py` (`THRESHOLDS`) and loaded into `ref_thresholds`; they are not regulatory or policy limits. RAG: for "higher is worse" metrics, Amber at or above the amber value and Red at or above the red value; for "higher is better", Amber below the amber value and Red below the red value.

SLA: an alert meets SLA if its closure date is on or before creation date plus `sla_days` (High 5, Medium 10, Low 20). An open alert is overdue if the snapshot date is after its due date.

## KPIs

| Metric (id) | Formula | Grain | Meaning for operations | Threshold |
|---|---|---|---|---|
| Alert volume (`alerts_created`) | count of alerts by creation month | month | Inflow the team must absorb | trend only |
| Alerts closed (`alerts_closed`) | count of alerts by closure month | month | Throughput; compare with inflow | trend only |
| Backlog (`backlog_eom`) | open alerts at month end | month-end snapshot | Work waiting; also a KRI (below) | see KRI |
| Aging buckets | open alerts at month end by age (0-7, 8-14, 15-30, 31-60, >60 days) and risk band (`mart_aging_snapshot`) | month x bucket x band | Where waiting work sits relative to SLA | trend only |
| % within SLA (`pct_within_sla`) | alerts closed in month within SLA / alerts closed in month | month (by closure) | Service level delivered to the SLA target | Amber < 95%, Red < 90% |
| Alerts closed per investigator per week (`alerts_closed_per_inv_week`) | alerts closed in month / headcount on the 15th / (business days / 5) | month | Productivity per head; on the scorecard | trend only |
| Cases per investigator per week (`cases_per_inv_week`) | cases opened in month / headcount on the 15th / (business days / 5) | month | Case-generation load per person; in `mart_monthly` only | trend only |
| Investigator productivity (`mart_investigator_month`) | alerts closed per investigator per month, with `business_days_employed` and `alerts_closed_per_week` | investigator x month | Spread across investigators and by tenure band | trend only |
| Average handle time (`aht_min`) | mean `handle_minutes` of alerts closed in month | month | Effort per alert; the capacity model input | trend only |
| Escalation rate (`escalation_rate`) | alerts closed as `escalated_to_case` / alerts closed | month; also scenario | Share of alerts judged to need a case | trend only |
| SAR conversion rate (`sar_conversion_rate`) | cases with `sar_filed` true / cases closed in month | month; also scenario | Yield of cases | trend only |
| False-positive rate (`fp_rate`) | alerts closed as `closed_no_action` / alerts closed | month; also scenario (`mart_scenario_kpis`) | Share of effort spent on alerts with no action; tuning signal. Complement of escalation rate | trend only |
| Effective FTE (`effective_fte`) | sum of ramp factor over investigators employed on the 15th | month | Ramp-weighted staffing | n/a |

## KRIs

| Metric (id) | Formula | Grain | Meaning for operations | Threshold |
|---|---|---|---|---|
| Backlog above threshold (`backlog_eom`) | open alerts at month end | month-end snapshot | Backlog beyond roughly two to four weeks of inflow signals SLA risk | Amber >= 1,500, Red >= 2,500 |
| SLA breach rate (`sla_breach_rate`) | alerts closed in month after SLA due date / alerts closed in month (1 minus % within SLA) | month | Share of reviewed work that was late. Complement of % within SLA, kept because it carries the KRI threshold | Amber >= 5%, Red >= 10% |
| Aging over 30 days (`open_gt30_pct`; count `open_gt30`) | open alerts older than 30 days at month end / open alerts | month-end snapshot | Backlog that is far past every SLA target | Amber >= 5%, Red >= 10% |
| Aging over 60 days (`open_gt60_pct`; count `open_gt60`) | open alerts older than 60 days at month end / open alerts | month-end snapshot | Severely aged work | Amber >= 2%, Red >= 5% |
| High-risk overdue concentration (`high_overdue_pct`) | open High-risk alerts past SLA / open High-risk alerts | month-end snapshot | Exposure on the highest-risk work; the context metric `high_overdue_share` gives High-risk as a share of all overdue open alerts | Amber >= 10%, Red >= 25% |
| SAR timeliness (`sar_clock_overdue_pct`; count `sar_clock_overdue`) | cases open at month end whose alert was created more than 30 calendar days earlier (`run_params.sar_clock_days`, from `SAR_CLOCK_DAYS`) / cases open at month end | month-end snapshot | Cases still without a decision after the 30-day window that the US rule sets for filing a SAR from initial detection (31 CFR 1020.320(b)(3)). Counts cases only, not alerts still in the queue | Amber >= 10%, Red >= 25% (placeholders) |

Month-end context columns in `mart_monthly`: `median_age_open`, `median_age_open_high` and `median_age_open_low` (median age in days of open alerts, overall and by risk band) and `avg_age_at_close_days` (mean age at closure of alerts closed in the month).

If the denominator is zero (for example no open alerts), the metric is null and reported as "n/a".
