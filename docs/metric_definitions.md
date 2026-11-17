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
| Cases per investigator per week (`cases_per_inv_week`) | cases opened in month / headcount on the 15th / (business days / 5) | month | Case-generation load per person | trend only |
| Alerts closed per investigator per week (`alerts_closed_per_inv_week`) | alerts closed in month / headcount on the 15th / (business days / 5) | month | Productivity per head | trend only |
| Average handle time (`aht_min`) | mean `handle_minutes` of alerts closed in month | month | Effort per alert; the capacity model input | trend only |
| Escalation rate (`escalation_rate`) | alerts closed as `escalated_to_case` / alerts closed | month; also scenario | Share of alerts judged to need a case | trend only |
| SAR conversion rate (`sar_conversion_rate`) | cases with `sar_filed` true / cases closed in month | month; also scenario | Yield of cases | trend only |
| False-positive rate (`fp_rate`) | alerts closed as `closed_no_action` / alerts closed | month; also scenario (`mart_scenario_kpis`) | Share of effort spent on alerts with no action; tuning signal | trend only |
| Effective FTE (`effective_fte`) | sum of ramp factor over investigators employed on the 15th | month | Ramp-weighted staffing | n/a |

## KRIs

| Metric (id) | Formula | Grain | Meaning for operations | Threshold |
|---|---|---|---|---|
| Backlog above threshold (`backlog_eom`) | open alerts at month end | month-end snapshot | Backlog beyond roughly two to four weeks of inflow signals SLA risk | Amber >= 1,500, Red >= 2,500 |
| SLA breach rate (`sla_breach_rate`) | alerts closed in month after SLA due date / alerts closed in month (1 minus % within SLA) | month | Share of reviewed work that was late | Amber >= 5%, Red >= 10% |
| Aging over 30 days (`open_gt30_pct`; count `open_gt30`) | open alerts older than 30 days at month end / open alerts | month-end snapshot | Backlog that is far past every SLA target | Amber >= 5%, Red >= 10% |
| Aging over 60 days (`open_gt60_pct`; count `open_gt60`) | open alerts older than 60 days at month end / open alerts | month-end snapshot | Severely aged work | Amber >= 2%, Red >= 5% |
| High-risk overdue concentration (`high_overdue_pct`) | open High-risk alerts past SLA / open High-risk alerts | month-end snapshot | Exposure on the highest-risk work; the context metric `high_overdue_share` gives High-risk as a share of all overdue open alerts | Amber >= 10%, Red >= 25% |

If the denominator is zero (for example no open alerts), the metric is null and reported as "n/a".
