-- Staging: investigator roster. Grain: one row per investigator.
CREATE OR REPLACE VIEW stg_investigators AS
SELECT
    investigator_id,
    CAST(hire_date AS DATE) AS hire_date,
    CAST(term_date AS DATE) AS term_date
FROM raw_investigators;
