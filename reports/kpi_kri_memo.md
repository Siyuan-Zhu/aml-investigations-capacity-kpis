# AML Investigations Capacity & KPIs: KPI/KRI Memo (June 2026)

**To:** Head of AML Operations | **From:** Operations Performance & Analytics | **Data:** synthetic, illustrative only (seeded simulation of a 25-investigator alert queue; no real institution's figures or rates)

## 1. Current state

- The alert backlog stands at **2,811** open alerts at June 2026 month end (red; threshold 2,500). It peaked at **3,630** in April 2026 and has fallen since.
- **39.5%** of alerts closed in June 2026 met their SLA (red; target 95%). The SLA rate held near 100% until the backlog began to form after the June 2025 detection-rule launch.
- Open alerts aged over 30 days are **39.0%** of the backlog; High-risk alerts past SLA are **88.6%** of open High-risk alerts (93 of 105).

## 2. KPI/KRI scorecard (June 2026, with prior month)

| Metric | Type | Jun | Prior month | Threshold | RAG |
|---|---|---|---|---|---|
| Alert volume (month) | KPI | 3,313 | 3,499 | trend only | Monitor |
| Alerts closed (month) | KPI | 4,044 | 3,587 | trend only | Monitor |
| Open alert backlog (month end) | KRI | 2,811 | 3,542 | amber >= 1,500, red >= 2,500 | Red |
| % closed within SLA | KPI | 39.5% | 46.7% | amber < 95.0%, red < 90.0% | Red |
| Average handle time | KPI | 50.8 | 51.4 | trend only | Monitor |
| Cases opened per investigator per week | KPI | 2.91 | 3.12 | trend only | Monitor |
| Escalation rate | KPI | 9.2% | 10.6% | trend only | Monitor |
| SAR conversion rate (closed cases) | KPI | 34.3% | 38.9% | trend only | Monitor |
| False-positive rate | KPI | 90.8% | 89.4% | trend only | Monitor |
| SLA breach rate (closed alerts) | KRI | 60.5% | 53.3% | amber >= 5.0%, red >= 10.0% | Red |
| Open alerts aged > 30 days (% of open) | KRI | 39.0% | 48.5% | amber >= 5.0%, red >= 10.0% | Red |
| Open alerts aged > 60 days (% of open) | KRI | 0.0% | 0.0% | amber >= 2.0%, red >= 5.0% | Green |
| High-risk open alerts past SLA (% of High-risk open) | KRI | 88.6% | 91.3% | amber >= 10.0%, red >= 25.0% | Red |

Definitions, grain and thresholds are in `docs/metric_definitions.md`. Metrics marked "trend only" have no policy threshold in this exercise.

## 3. Drivers

- **Volume step.** The forecast model estimates the June 2025 rule launch added about **476 alerts per month** on top of a trend of 14.6 alerts per month.
- **Low-yield alerts.** The new rule (Network Link Analysis) was 13% of alerts closed and 14% of handle hours over the last six months. Its false-positive rate is 95.1% (other rules: 89.1%) and its SAR conversion is 21.0%.
- **Throughput shortfall.** Created alerts exceeded closures in 9 of 13 months since launch, adding 2,811 alerts net. Average handle time rose from 49.7 to 51.3 minutes with the new rule mix.
- **Staffing.** Ramp-weighted FTE averaged 24.3 before launch and reached a low of 22.8 in March 2026 (departures plus new-hire ramp-up). It was 27.4 in June 2026.

## 4. Volume forecast

Model: OLS on linear trend, annual seasonality (one sine/cosine pair) and a post-launch step. Holdout backtest (fit on first 24 months, test on last 6): **MAPE 5.1%**.

| Month | Forecast alerts | 95% prediction interval |
|---|---|---|
| Jul 2026 | 3,650 | 3,332 to 3,969 |
| Aug 2026 | 3,756 | 3,430 to 4,081 |
| Sep 2026 | 3,905 | 3,574 to 4,236 |
| Oct 2026 | 4,061 | 3,726 to 4,396 |
| Nov 2026 | 4,188 | 3,850 to 4,525 |
| Dec 2026 | 4,254 | 3,915 to 4,592 |

## 5. Capacity gap

Required FTE = forecast volume x handle time (51.4 min, trailing 6 months) / productive hours per FTE (business days x 7.5 h x 80% utilization x 95% attendance). Available FTE starts from the current roster of 28 with ramp-up (0+ mo: 40%, 1+ mo: 60%, 2+ mo: 80%, 3+ mo: 100%) and 1.25% monthly attrition backfilled after 2 months. Gap = required minus available; positive is a shortfall.

| Scenario | Mean gap (FTE) | Peak gap (FTE) | Months short | Peak gap incl. backlog clearance |
|---|---|---|---|---|
| Base | -0.1 | +3.0 (Nov 2026) | 3 of 6 | +6.4 |
| Rule launch (+20% volume) | +4.5 | +9.0 (Nov 2026) | 5 of 6 | +12.3 |
| Attrition shock | +3.0 | +7.1 (Nov 2026) | 5 of 6 | +10.4 |

Backlog clearance adds 3.1 FTE if the current backlog is to be worked off over 6 months. Scenarios: +20% volume from forecast month 2; 5 additional departures (months 2, 4) with 2 hires in month 5.

## 6. Recommendations

1. **Review the Network Link Analysis rule's tuning.** At a 95% false-positive rate it consumes 14% of handle hours. Each 10% reduction in its alert volume frees about 0.4 FTE of capacity (arithmetic on current handle hours, not a forecast of what tuning would achieve).
2. **Start hiring against the base-case peak.** The base case peaks at a +3.0 FTE gap in November 2026 (+6.4 with backlog clearance). New hires take 3 months to reach full productivity, so hires would need to start by August 2026 to be fully ramped at the peak. The +20% volume scenario peaks at +9.0 FTE, so a decision on that rule launch should come with a staffing plan.
3. **Turn the KRIs into escalation triggers and fix High-risk routing.** Link amber/red KRI states to named actions (overtime, queue reallocation). Prioritize clearing the 93 High-risk alerts past SLA, and check whether High-risk alerts are being routed to the general queue.

## 7. Limitations

- All data is simulated from stated assumptions (`docs/simulation_assumptions.md`); results show the method, not a real institution's performance.
- The forecast uses 30 monthly points and a single seasonal harmonic; the interval reflects model error, not future rule launches or policy changes.
- The capacity model uses average handle time and a single utilization figure. It ignores skill mix, holidays, and the case-stage workload after escalation.
- Thresholds are placeholders chosen for illustration, not regulatory or policy limits.
