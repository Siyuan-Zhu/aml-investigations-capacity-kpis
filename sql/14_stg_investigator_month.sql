-- Investigator x month roster snapshot at mid-month (15th) with ramp factor.
-- Grain: one row per investigator employed on the 15th of the month.
CREATE OR REPLACE TABLE stg_investigator_month AS
WITH emp AS (
    SELECT
        m.month_start,
        i.investigator_id,
        FLOOR(date_diff('day', i.hire_date, m.month_start + 14) / 30.4375) AS tenure_months
    FROM dim_month m
    JOIN stg_investigators i
      ON i.hire_date <= m.month_start + 14
     AND (i.term_date IS NULL OR i.term_date > m.month_start + 14)
)
SELECT e.month_start, e.investigator_id, e.tenure_months, r.ramp_factor
FROM emp e
JOIN ref_ramp r ON r.tenure_from <= e.tenure_months
QUALIFY ROW_NUMBER() OVER (PARTITION BY e.month_start, e.investigator_id ORDER BY r.tenure_from DESC) = 1;
