-- Scenario (rule) KPIs. Grain: scenario x period ('all' or 'last_6m' by alert close date).
CREATE OR REPLACE TABLE mart_scenario_kpis AS
WITH win AS (
    SELECT 'all' AS period, DATE '1900-01-01' AS d0
    UNION ALL
    SELECT 'last_6m', CAST((SELECT as_of FROM run_params) - INTERVAL 6 MONTH AS DATE) + 1
),
base AS (
    SELECT w.period, a.*, c.sar_filed, c.closed_at IS NOT NULL AS case_closed
    FROM win w
    JOIN stg_alerts a ON a.is_closed AND a.closed_date >= w.d0
    LEFT JOIN stg_cases c USING (alert_id)
)
SELECT
    period,
    scenario,
    COUNT(*)                                                                      AS alerts_closed,
    AVG(handle_minutes)                                                           AS aht_min,
    COUNT(*) FILTER (WHERE case_closed)                                           AS cases_closed,
    AVG(CASE WHEN disposition = 'closed_no_action' THEN 1.0 ELSE 0.0 END)         AS fp_rate,
    AVG(CASE WHEN disposition = 'escalated_to_case' THEN 1.0 ELSE 0.0 END)        AS escalation_rate,
    CASE WHEN COUNT(*) FILTER (WHERE case_closed) > 0
         THEN COUNT(*) FILTER (WHERE sar_filed) * 1.0 / COUNT(*) FILTER (WHERE case_closed) END AS sar_conversion_rate,
    AVG(CASE WHEN breached_at_close THEN 0.0 ELSE 1.0 END)                        AS pct_within_sla,
    SUM(handle_minutes) / 60.0                                                    AS handle_hours
FROM base
GROUP BY period, scenario
ORDER BY period, scenario;
