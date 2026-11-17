-- Staging: cases. Grain: one row per case (one case per escalated alert).
CREATE OR REPLACE VIEW stg_cases AS
SELECT
    case_id,
    alert_id,
    opened_at,
    CAST(opened_at AS DATE) AS opened_date,
    closed_at,
    CAST(closed_at AS DATE) AS closed_date,
    investigator_id,
    sar_filed
FROM raw_cases;
