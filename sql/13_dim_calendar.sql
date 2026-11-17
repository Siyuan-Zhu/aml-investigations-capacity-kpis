-- Calendar dimensions. Business days = Monday-Friday (no holiday calendar).
CREATE OR REPLACE TABLE dim_day AS
SELECT CAST(d AS DATE) AS day
FROM generate_series(
    CAST(date_trunc('month', (SELECT MIN(created_date) FROM stg_alerts)) AS DATE),
    (SELECT as_of FROM run_params),
    INTERVAL 1 DAY) t(d);

CREATE OR REPLACE TABLE dim_month AS
SELECT
    CAST(date_trunc('month', day) AS DATE)                   AS month_start,
    CAST(last_day(day) AS DATE)                              AS month_end,
    COUNT(*) FILTER (WHERE isodow(day) <= 5)                 AS business_days
FROM dim_day
GROUP BY 1, 2
ORDER BY 1;
