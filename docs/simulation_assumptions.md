# Simulation assumptions

All data in this repository is **synthetic**. It is produced by `src/simulate.py` from the parameters in `src/config.py` with a fixed seed (`SEED = 42`). No real institution's data, volumes or rates are used or implied. Every parameter below is an illustrative choice, not a benchmark.

## Timeline
- 30 months, 2024-01 to 2026-06. Alerts are created on business days (Monday to Friday, no holiday calendar).
- Reporting as-of date: last day of the final month (2026-06-30). Work in progress at that date is the open backlog.

## Alert volume
Monthly baseline volume = trend x seasonality x noise.

| Component | Value |
|---|---|
| Trend | 3,050 alerts in month 0, +12 per month |
| Seasonality | `1 + 0.07*cos(2*pi*(month-12)/12) + 0.025*cos(4*pi*(month-3)/12)` (peak in December) |
| Noise | lognormal, sigma 0.03 |
| Daily allocation | monthly count spread uniformly at random over business days |

**Shock (documented, one-time):** a new detection rule, "Network Link Analysis", launches in month index 17 (June 2025). From then on it adds alerts equal to 15% of that month's baseline volume, as a step (no ramp).

## Scenarios (detection rules)
Baseline volume is split across five scenarios by fixed shares. For each: handle time is lognormal with the stated median (minutes) and sigma; escalation probability is the base value times a risk-band multiplier; SAR probability is conditional on a case being opened.

| Scenario | Share | Handle median (min) | Sigma | Base escalation | SAR given case | Risk bands (Low/Med/High) |
|---|---|---|---|---|---|---|
| Cash Structuring | 22% | 40 | 0.45 | 12% | 45% | 45/40/15 |
| Rapid Fund Movement | 18% | 55 | 0.50 | 15% | 40% | 35/40/25 |
| High-Risk Geography | 15% | 45 | 0.40 | 8% | 30% | 40/40/20 |
| Unusual Wire Activity | 15% | 60 | 0.50 | 14% | 42% | 30/45/25 |
| Profile Mismatch | 30% | 35 | 0.40 | 6% | 25% | 60/32/8 |
| Network Link Analysis (new, post-launch) | 15% of baseline, additional | 50 | 0.45 | 5% | 20% | 50/35/15 |

Handle times are clipped to 5 to 480 minutes and multiplied by the working investigator's speed factor (lognormal, sigma 0.10, fixed per investigator).

## Risk band, score and SLA
- Risk score is uniform within the band range: Low 0-39, Medium 40-69, High 70-100.
- SLA target (calendar days from creation): High 5, Medium 10, Low 20.
- Escalation multiplier by band: High 2.0, Medium 1.0, Low 0.5 (capped at 95%). SAR multiplier by band: High 1.2, Medium 1.0, Low 0.8.
- Because of the multipliers and band mix, the realized escalation and false-positive rates are emergent outputs, not inputs.

## Disposition and cases
- Disposition at alert closure is `closed_no_action` or `escalated_to_case`. "False positive" in the KPI layer means `closed_no_action`.
- Each escalated alert opens exactly one case at the alert's closure time. Case duration is lognormal (median 14 days, sigma 0.5). A case closes with `sar_filed` true or false; cases still open at the as-of date have `sar_filed` null.

## Investigators and staffing
- 25 investigators at the start (hire dates before 2024-01-01).
- Productive time per working day: 7.5 h x 80% utilization = 360 minutes. Each investigator is absent on a given day with probability 5% (shrinkage).
- **Ramp-up:** productivity factor by tenure month (0, 1, 2, 3+) = 40%, 60%, 80%, 100%. A new hire's factor scales available minutes; it does not change per-alert handle time.
- **Attrition:** 1.25% per investigator per month, applied daily. Each departure is backfilled with a new hire after a uniform 30 to 75 days.
- **Cluster departure:** 3 tenured investigators leave on 2026-03-02 (team reorganization), also backfilled.
- **Planned hires:** 2 hires start 2025-10-01 and 2 start 2026-04-01, approved after the rule launch.
- Total distinct investigators over the window is about 40; headcount at any time ranges from 23 to 29.

## Queue discipline
Each business day, each present investigator works alerts until their minutes for the day are used. An alert whose handle time exceeds the remaining minutes carries a negative balance into the next day.
- With probability 85% an investigator takes the next alert by risk band (High, then Medium, then Low) and age (oldest first); with probability 15% they take the oldest alert in the queue regardless of band.
- 12% of High and Medium alerts enter the Low-priority lane on arrival (late risk-score enrichment or misrouting), so they wait like Low alerts until reached by the FIFO exception.
- Alerts are created in an overnight batch (00:00 to 05:59) and closed during the working day (09:00 to 17:00).

## Known simplifications
- Pre-launch, capacity exceeds demand, so the backlog is near zero and SLA attainment is near 100%. The backlog is driven by the launch plus the staffing dip.
- No holidays, seasonality in attrition, alert re-opens, quality review or second-level case investigators.
- Case workload after escalation is not modeled as consuming investigator capacity.
- Escalated and non-escalated alerts share the same handle-time distribution within a rule.
