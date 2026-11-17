# KPI/KRI Memo, June 2026

**To:** Head of AML Operations (illustrative) | **From:** Siyuan (David) Zhu | **Data:** synthetic, illustrative only (seeded simulation of a 25-investigator alert queue; no real institution's figures or rates)

## 1. Current state

- The alert backlog stands at **2,811** open alerts at June 2026 month end (red; threshold 2,500). It peaked at **3,630** in April 2026 and has fallen since.
- **39.5%** of alerts closed in June 2026 met their SLA (red; target 95%). The SLA rate held near 100% until the backlog began to form after the June 2025 detection-rule launch. SLA attainment fell from 51.0% in April to 39.5% while the backlog fell from 3,630 to 2,811: alerts closed in June were on average 31.4 days old at closure (24.6 in April), so the team is now closing older alerts that had already breached.
- Open alerts aged over 30 days are **39.0%** of the backlog; High-risk alerts past SLA are **88.6%** of open High-risk alerts (93 of 105).
- Open High-risk alerts have a median age of 26 days at June 2026 month end, against 26 days for Low-risk alerts. If High-risk work were prioritized, it would be younger; the equal ages suggest some High-risk alerts are sitting in the general queue.
- **40.2%** of open cases (78 of 194) are more than 30 calendar days from alert detection without a decision. This is the SAR-timeliness KRI, based on the US 30-day filing window (31 CFR 1020.320(b)(3)); its thresholds here are placeholders.

## 2. KPI/KRI scorecard (June 2026, with prior month)

| Metric | Type | Jun | Prior month | Threshold | RAG |
|---|---|---|---|---|---|
| Alert volume (month) | KPI | 3,313 | 3,499 | trend only | Monitor |
| Alerts closed (month) | KPI | 4,044 | 3,587 | trend only | Monitor |
| Open alert backlog (month end) | KRI | 2,811 | 3,542 | amber >= 1,500, red >= 2,500 | Red |
| % closed within SLA | KPI | 39.5% | 46.7% | amber < 95.0%, red < 90.0% | Red |
| Average handle time | KPI | 50.8 | 51.4 | trend only | Monitor |
| Alerts closed per investigator per week | KPI | 31.7 | 29.4 | trend only | Monitor |
| Escalation rate | KPI | 9.2% | 10.6% | trend only | Monitor |
| SAR conversion rate (closed cases) | KPI | 34.3% | 38.9% | trend only | Monitor |
| False-positive rate (complement of escalation rate) | KPI | 90.8% | 89.4% | trend only | Monitor |
| SLA breach rate (complement of % within SLA) | KRI | 60.5% | 53.3% | amber >= 5.0%, red >= 10.0% | Red |
| Open alerts aged > 30 days (% of open) | KRI | 39.0% | 48.5% | amber >= 5.0%, red >= 10.0% | Red |
| Open alerts aged > 60 days (% of open) | KRI | 0.0% | 0.0% | amber >= 2.0%, red >= 5.0% | Green |
| High-risk open alerts past SLA (% of High-risk open) | KRI | 88.6% | 91.3% | amber >= 10.0%, red >= 25.0% | Red |
| Open cases >30 days from alert detection (% of open cases) | KRI | 40.2% | 28.8% | amber >= 10.0%, red >= 25.0% | Red |

Definitions, grain and thresholds are in `docs/metric_definitions.md`. Metrics marked "trend only" have no policy threshold in this exercise. SLA breach rate and false-positive rate are the complements of % closed within SLA and of escalation rate (as disposition shares), shown because they carry thresholds or a tuning signal.

## 3. Drivers

- **Volume step.** The forecast model estimates the June 2025 rule launch added about **476 alerts per month** on top of a trend of 14.6 alerts per month.
- **Low-yield alerts.** The new rule (Network Link Analysis) was 13% of alerts closed and 14% of handle hours over the last six months. Its false-positive rate is 95.1% (other rules: 89.1%) and its SAR conversion is 21.0% (other rules: 37.8%).
- **Throughput shortfall.** Created alerts exceeded closures in 9 of 13 months since launch, adding 2,811 alerts net. Average handle time rose from 49.7 to 51.3 minutes after the launch.
- **Staffing.** Ramp-weighted FTE averaged 24.3 before launch and reached a low of 22.8 in March 2026 (departures plus new-hire ramp-up). It was 27.4 in June 2026.

## 4. Investigator productivity

Alerts closed per investigator by tenure band, last 6 months (investigator-months with at least 15 business days on the roster). Productive hours = business days x 7.5 h x 80% x 95%.

| Tenure band | Investigator-months | Median alerts closed per productive hour | Median alerts closed per week | P10 to P90 per week |
|---|---|---|---|---|
| 0-2 months | 19 | 0.73 | 20.7 | 14.4 to 25.6 |
| 3-11 months | 27 | 1.12 | 31.8 | 27.3 to 35.9 |
| 12+ months | 113 | 1.17 | 33.2 | 29.1 to 38.0 |

Across the 26 investigators with at least 3 months of tenure, average alerts closed per week over the same window ranged from 27.2 to 40.3 (median 33.2; highest is 1.48x the lowest).

## 5. Volume forecast

Model: OLS on linear trend, annual seasonality (one sine/cosine pair) and a post-launch step. Holdout backtest (fit on first 24 months, test on last 6): **MAPE 5.1%**, against 14.0% for a seasonal-naive forecast (same month one year earlier). The model has the same form as the process that generated the data, so its MAPE is flattering.

| Month | Forecast alerts | 95% prediction interval |
|---|---|---|
| Jul 2026 | 3,650 | 3,332 to 3,969 |
| Aug 2026 | 3,756 | 3,430 to 4,081 |
| Sep 2026 | 3,905 | 3,574 to 4,236 |
| Oct 2026 | 4,061 | 3,726 to 4,396 |
| Nov 2026 | 4,188 | 3,850 to 4,525 |
| Dec 2026 | 4,254 | 3,915 to 4,592 |

## 6. Capacity gap

Required FTE = forecast volume x handle time (51.4 min, trailing 6 months) / productive hours per FTE (business days x 7.5 h x 80% utilization x 95% attendance). Available FTE starts from the current roster of 28 with ramp-up (0+ mo: 40%, 1+ mo: 60%, 2+ mo: 80%, 3+ mo: 100%) and 1.25% monthly attrition backfilled after 2 months. 1 pending backfill hire for recent leavers is added at the midpoint of the 30 to 75 day lag. Gap = required minus available; positive is a shortfall.

| Scenario | Mean gap (FTE) | Peak monthly gap (FTE) | Peak 3-month average gap (FTE, month ending) | Months short | Peak gap incl. backlog clearance |
|---|---|---|---|---|---|
| Base | -0.7 | +2.0 (Nov 2026, 21 business days) | +0.6 (Dec 2026) | 1 of 6 | +5.4 |
| Rule launch (+20% volume) | +3.9 | +8.0 (Nov 2026, 21 business days) | +6.3 (Dec 2026) | 5 of 6 | +11.4 |
| Attrition shock | +2.4 | +6.1 (Nov 2026, 21 business days) | +4.8 (Dec 2026) | 5 of 6 | +9.5 |

Monthly gaps move with business-day counts, so the 3-month average gap is the steadier view. Backlog clearance adds 3.1 FTE if the current backlog is to be worked off over 6 months. Scenarios: +20% volume from forecast month 2; 5 additional departures (months 2, 4) with 2 hires in month 5.

## 7. Recommendations

1. **Review the Network Link Analysis rule's tuning.** At a 95% false-positive rate it consumes 14% of handle hours. Each 10% reduction in its alert volume frees about 0.4 FTE of capacity (arithmetic on current handle hours, not a forecast of what tuning would achieve).
2. **Add temporary capacity now and tie permanent hiring to the next rule launch.** Add about 3 FTE of temporary capacity (overtime, contractors or loaned staff) for 6 months to clear the backlog. Base-case demand is roughly balanced on average (-0.7 FTE) with a +2.0 FTE peak in November, a 21-business-day month (the highest 3-month average gap is +0.6 FTE), so permanent hiring depends on the next rule launch: the +20% volume scenario is short in 5 of 6 months and peaks at +8.0 FTE.
3. **Turn the KRIs into escalation triggers and fix High-risk routing.** Link amber/red KRI states to named actions (overtime, queue reallocation). Prioritize clearing the 93 High-risk alerts past SLA, and check whether High-risk alerts are being routed to the general queue (section 1). Add the SAR-timeliness KRI to the same trigger set.

## 8. Limitations

- All data is simulated from stated assumptions (`docs/simulation_assumptions.md`); results show the method, not a real institution's performance.
- The forecast uses 30 monthly points and a single seasonal harmonic; the interval reflects model error, not future rule launches or policy changes.
- The capacity model uses average handle time and a single utilization figure. It ignores skill mix and holidays. Case (L2) work uses no investigator capacity in the simulator, and escalated and non-escalated alerts share handle-time distributions.
- Pending backfills are inferred from leavers in the last 75 days, using the midpoint of the backfill lag range; actual start dates are not in the roster.
- The forecast has the same form as the data-generating process, so its backtest MAPE is flattering; the seasonal-naive comparison in section 5 is a weak baseline that ignores trend and the rule launch.
- Thresholds are placeholders chosen for illustration, not regulatory or policy limits.
