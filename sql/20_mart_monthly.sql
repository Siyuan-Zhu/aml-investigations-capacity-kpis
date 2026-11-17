-- Wide monthly KPI/KRI mart. Grain: one row per calendar month.
-- Month-end snapshot metrics (backlog, aging) use alerts open at month_end.
CREATE OR REPLACE TABLE mart_monthly AS
WITH created AS (
    SELECT CAST(date_trunc('month', created_date) AS DATE) AS month_start, COUNT(*) AS alerts_created
    FROM stg_alerts GROUP BY 1
),
closed AS (
    SELECT
        CAST(date_trunc('month', closed_date) AS DATE)                           AS month_start,
        COUNT(*)                                                                 AS alerts_closed,
        AVG(handle_minutes)                                                      AS aht_min,
        AVG(CASE WHEN breached_at_close THEN 0.0 ELSE 1.0 END)                   AS pct_within_sla,
        AVG(CASE WHEN breached_at_close THEN 1.0 ELSE 0.0 END)                   AS sla_breach_rate,
        AVG(CASE WHEN disposition = 'escalated_to_case' THEN 1.0 ELSE 0.0 END)   AS escalation_rate,
        AVG(CASE WHEN disposition = 'closed_no_action' THEN 1.0 ELSE 0.0 END)    AS fp_rate
    FROM stg_alerts WHERE is_closed GROUP BY 1
),
cases_opened AS (
    SELECT CAST(date_trunc('month', opened_date) AS DATE) AS month_start, COUNT(*) AS cases_opened
    FROM stg_cases GROUP BY 1
),
cases_closed AS (
    SELECT
        CAST(date_trunc('month', closed_date) AS DATE) AS month_start,
        COUNT(*)                                       AS cases_closed,
        COUNT(*) FILTER (WHERE sar_filed)              AS sars_filed
    FROM stg_cases WHERE closed_date IS NOT NULL GROUP BY 1
),
open_snap AS (
    SELECT
        m.month_start,
        COUNT(a.alert_id)                                                                    AS backlog_eom,
        COUNT(*) FILTER (WHERE date_diff('day', a.created_date, m.month_end) > 30)           AS open_gt30,
        COUNT(*) FILTER (WHERE date_diff('day', a.created_date, m.month_end) > 60)           AS open_gt60,
        COUNT(*) FILTER (WHERE m.month_end > a.sla_due_date)                                 AS overdue_open,
        COUNT(*) FILTER (WHERE m.month_end > a.sla_due_date AND a.risk_band = 'High')        AS high_overdue_open,
        COUNT(*) FILTER (WHERE a.risk_band = 'High')                                         AS high_open
    FROM dim_month m
    LEFT JOIN stg_alerts a
      ON a.created_date <= m.month_end AND (a.closed_date IS NULL OR a.closed_date > m.month_end)
    GROUP BY 1
),
staff AS (
    SELECT month_start, COUNT(*) AS headcount_mid, SUM(ramp_factor) AS effective_fte
    FROM stg_investigator_month GROUP BY 1
)
SELECT
    m.month_start,
    m.month_end,
    m.business_days,
    COALESCE(c.alerts_created, 0)                              AS alerts_created,
    COALESCE(cl.alerts_closed, 0)                              AS alerts_closed,
    o.backlog_eom,
    o.open_gt30,
    o.open_gt60,
    o.overdue_open,
    o.high_overdue_open,
    o.high_open,
    cl.pct_within_sla,
    cl.sla_breach_rate,
    cl.aht_min,
    cl.escalation_rate,
    cl.fp_rate,
    COALESCE(co.cases_opened, 0)                               AS cases_opened,
    COALESCE(cc.cases_closed, 0)                               AS cases_closed,
    COALESCE(cc.sars_filed, 0)                                 AS sars_filed,
    CASE WHEN cc.cases_closed > 0 THEN cc.sars_filed * 1.0 / cc.cases_closed END AS sar_conversion_rate,
    s.headcount_mid,
    s.effective_fte,
    COALESCE(co.cases_opened, 0) * 1.0 / s.headcount_mid / (m.business_days / 5.0) AS cases_per_inv_week,
    COALESCE(cl.alerts_closed, 0) * 1.0 / s.headcount_mid / (m.business_days / 5.0) AS alerts_closed_per_inv_week,
    CASE WHEN o.backlog_eom > 0 THEN o.open_gt30 * 1.0 / o.backlog_eom END       AS open_gt30_pct,
    CASE WHEN o.backlog_eom > 0 THEN o.open_gt60 * 1.0 / o.backlog_eom END       AS open_gt60_pct,
    CASE WHEN o.overdue_open > 0 THEN o.high_overdue_open * 1.0 / o.overdue_open END AS high_overdue_share,
    CASE WHEN o.high_open > 0 THEN o.high_overdue_open * 1.0 / o.high_open END       AS high_overdue_pct
FROM dim_month m
LEFT JOIN created c       USING (month_start)
LEFT JOIN closed cl       USING (month_start)
LEFT JOIN cases_opened co USING (month_start)
LEFT JOIN cases_closed cc USING (month_start)
LEFT JOIN open_snap o     USING (month_start)
LEFT JOIN staff s         USING (month_start)
ORDER BY m.month_start;
