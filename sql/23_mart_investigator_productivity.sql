-- Investigator productivity. Grain: investigator x month (work closed in month).
CREATE OR REPLACE TABLE mart_investigator_month AS
SELECT
    CAST(date_trunc('month', a.closed_date) AS DATE)                 AS month_start,
    a.assigned_investigator_id                                       AS investigator_id,
    COUNT(*)                                                         AS alerts_closed,
    COUNT(*) FILTER (WHERE a.disposition = 'escalated_to_case')      AS cases_opened,
    AVG(a.handle_minutes)                                            AS aht_min,
    SUM(a.handle_minutes) / 60.0                                     AS handle_hours,
    im.tenure_months,
    im.ramp_factor
FROM stg_alerts a
LEFT JOIN stg_investigator_month im
  ON im.investigator_id = a.assigned_investigator_id
 AND im.month_start = CAST(date_trunc('month', a.closed_date) AS DATE)
WHERE a.is_closed
GROUP BY ALL
ORDER BY 1, 2;
