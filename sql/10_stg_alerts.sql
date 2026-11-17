-- Staging: typed alerts with derived SLA fields. Grain: one row per alert.
CREATE OR REPLACE VIEW stg_alerts AS
SELECT
    alert_id,
    created_at,
    CAST(created_at AS DATE)                           AS created_date,
    scenario,
    risk_band,
    risk_score,
    sla_days,
    CAST(created_at AS DATE) + CAST(sla_days AS INTEGER) AS sla_due_date,
    handle_minutes,
    assigned_investigator_id,
    closed_at,
    CAST(closed_at AS DATE)                            AS closed_date,
    disposition,
    closed_at IS NOT NULL                              AS is_closed,
    CASE WHEN closed_at IS NOT NULL
         THEN CAST(closed_at AS DATE) > CAST(created_at AS DATE) + CAST(sla_days AS INTEGER)
    END                                                AS breached_at_close
FROM raw_alerts;
