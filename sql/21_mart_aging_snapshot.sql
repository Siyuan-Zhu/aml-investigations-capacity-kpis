-- Aging buckets of open alerts at each month end. Grain: month x bucket x risk band.
CREATE OR REPLACE TABLE mart_aging_snapshot AS
WITH open_alerts AS (
    SELECT
        m.month_start,
        a.risk_band,
        date_diff('day', a.created_date, m.month_end) AS age_days
    FROM dim_month m
    JOIN stg_alerts a
      ON a.created_date <= m.month_end AND (a.closed_date IS NULL OR a.closed_date > m.month_end)
)
SELECT
    month_start,
    CASE WHEN age_days <= 7  THEN '0-7'
         WHEN age_days <= 14 THEN '8-14'
         WHEN age_days <= 30 THEN '15-30'
         WHEN age_days <= 60 THEN '31-60'
         ELSE '>60' END AS aging_bucket,
    CASE WHEN age_days <= 7  THEN 1
         WHEN age_days <= 14 THEN 2
         WHEN age_days <= 30 THEN 3
         WHEN age_days <= 60 THEN 4
         ELSE 5 END AS bucket_order,
    risk_band,
    COUNT(*) AS open_alerts
FROM open_alerts
GROUP BY ALL
ORDER BY month_start, bucket_order, risk_band;
