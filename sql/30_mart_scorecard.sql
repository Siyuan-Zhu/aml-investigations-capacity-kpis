-- Scorecard: latest month vs prior month for every KPI/KRI with RAG status.
-- Grain: one row per metric for the as-of month.
CREATE OR REPLACE TABLE mart_scorecard AS
WITH long AS (
    UNPIVOT (
        SELECT month_start,
               CAST(alerts_created AS DOUBLE) AS alerts_created,
               CAST(alerts_closed AS DOUBLE) AS alerts_closed,
               CAST(backlog_eom AS DOUBLE) AS backlog_eom,
               pct_within_sla, aht_min, cases_per_inv_week, escalation_rate,
               sar_conversion_rate, fp_rate, sla_breach_rate,
               open_gt30_pct, open_gt60_pct, high_overdue_pct
        FROM mart_monthly
    )
    ON COLUMNS(* EXCLUDE month_start)
    INTO NAME metric_id VALUE value
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (ORDER BY month_start DESC) AS rk FROM long
),
cur AS (SELECT * FROM ranked WHERE rk = 1),
prev AS (SELECT metric_id, value AS prior_value FROM ranked WHERE rk = 2)
SELECT
    t.metric_id, t.metric_name, t.metric_type, t.unit, t.direction, t.amber, t.red,
    cur.month_start AS as_of_month,
    cur.value,
    prev.prior_value,
    CASE
        WHEN t.direction = 'monitor' THEN 'Monitor'
        WHEN cur.value IS NULL THEN 'n/a'
        WHEN t.direction = 'higher_is_worse'  AND cur.value >= t.red   THEN 'Red'
        WHEN t.direction = 'higher_is_worse'  AND cur.value >= t.amber THEN 'Amber'
        WHEN t.direction = 'higher_is_better' AND cur.value <  t.red   THEN 'Red'
        WHEN t.direction = 'higher_is_better' AND cur.value <  t.amber THEN 'Amber'
        ELSE 'Green'
    END AS rag
FROM ref_thresholds t
LEFT JOIN cur  USING (metric_id)
LEFT JOIN prev USING (metric_id)
ORDER BY t.sort_order;
