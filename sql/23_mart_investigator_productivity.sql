-- Investigator productivity. Grain: investigator x month (work closed in month).
-- business_days_employed counts Monday-Friday days in the month on which the
-- investigator was on the roster (hire date through the day before term date).
CREATE OR REPLACE TABLE mart_investigator_month AS
WITH work AS (
    SELECT
        CAST(date_trunc('month', a.closed_date) AS DATE)                 AS month_start,
        a.assigned_investigator_id                                       AS investigator_id,
        COUNT(*)                                                         AS alerts_closed,
        COUNT(*) FILTER (WHERE a.disposition = 'escalated_to_case')      AS cases_opened,
        AVG(a.handle_minutes)                                            AS aht_min,
        SUM(a.handle_minutes) / 60.0                                     AS handle_hours
    FROM stg_alerts a
    WHERE a.is_closed
    GROUP BY ALL
),
emp_days AS (
    SELECT
        CAST(date_trunc('month', d.day) AS DATE) AS month_start,
        i.investigator_id,
        COUNT(*)                                 AS business_days_employed
    FROM dim_day d
    JOIN stg_investigators i
      ON d.day >= i.hire_date AND (i.term_date IS NULL OR d.day < i.term_date)
    WHERE isodow(d.day) <= 5
    GROUP BY ALL
)
SELECT
    w.month_start,
    w.investigator_id,
    w.alerts_closed,
    w.cases_opened,
    w.aht_min,
    w.handle_hours,
    im.tenure_months,
    im.ramp_factor,
    e.business_days_employed,
    w.alerts_closed * 1.0 / (e.business_days_employed / 5.0)             AS alerts_closed_per_week
FROM work w
LEFT JOIN stg_investigator_month im USING (month_start, investigator_id)
LEFT JOIN emp_days e USING (month_start, investigator_id)
ORDER BY 1, 2;
