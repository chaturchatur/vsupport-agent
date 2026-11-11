-- Persist call outcomes on interactions so containment can be computed from data.
--
-- All new columns are nullable: rows written before this migration, and rows
-- written only by the log_interaction tool (which knows nothing about outcomes),
-- keep NULLs. NULL means "not scored", which is different from FALSE.
--
-- Written by the end-of-call-report workflow from VAPI's
-- analysisPlan.structuredDataPlan output plus call metadata.

ALTER TABLE interactions
    ADD COLUMN IF NOT EXISTS call_reason            TEXT,
    ADD COLUMN IF NOT EXISTS authenticated          BOOLEAN,
    ADD COLUMN IF NOT EXISTS claim_number           TEXT,
    ADD COLUMN IF NOT EXISTS claim_status           TEXT,
    ADD COLUMN IF NOT EXISTS resolved_without_human BOOLEAN,
    ADD COLUMN IF NOT EXISTS escalation_requested   BOOLEAN,
    ADD COLUMN IF NOT EXISTS follow_up_needed       BOOLEAN,
    ADD COLUMN IF NOT EXISTS follow_up_reason       TEXT,
    ADD COLUMN IF NOT EXISTS duration_seconds       INTEGER,
    ADD COLUMN IF NOT EXISTS ended_reason           TEXT,
    -- Caller ID as VAPI saw it, digits only (e.g. 14155551234). interactions.phone_number
    -- is whatever the caller *said* (free-form, written by the LLM), so it cannot be used
    -- to find "this caller's last call". Digits only for the same reason as
    -- customers.phone_digits: no '+' to be mangled in a PostgREST filter.
    ADD COLUMN IF NOT EXISTS caller_phone_digits    TEXT;

CREATE INDEX IF NOT EXISTS idx_interactions_caller_phone_digits
    ON interactions (caller_phone_digits, timestamp DESC);

-- ============================================================
-- Daily outcome rollup (UTC days)
-- ============================================================
-- contained   = resolved_without_human AND NOT escalation_requested
-- scored_calls = calls that have an outcome at all (resolved_without_human IS NOT NULL)
-- containment_rate = contained_calls / scored_calls, so unscored legacy rows
--                    do not drag the rate down. NULL when nothing was scored.
-- security_invoker: the view runs with the querying role's privileges (Postgres 15+),
-- instead of the view owner's.
CREATE OR REPLACE VIEW v_call_outcomes_daily
WITH (security_invoker = true) AS
SELECT
    (timestamp AT TIME ZONE 'UTC')::date                                   AS day,
    COUNT(*)                                                               AS calls,
    COUNT(*) FILTER (WHERE authenticated)                                  AS authenticated_calls,
    COUNT(*) FILTER (WHERE resolved_without_human IS NOT NULL)             AS scored_calls,
    COUNT(*) FILTER (WHERE resolved_without_human
                       AND NOT COALESCE(escalation_requested, FALSE))      AS contained_calls,
    COUNT(*) FILTER (WHERE escalation_requested)                           AS escalations,
    ROUND(
        COUNT(*) FILTER (WHERE resolved_without_human
                           AND NOT COALESCE(escalation_requested, FALSE))::numeric
        / NULLIF(COUNT(*) FILTER (WHERE resolved_without_human IS NOT NULL), 0),
        4
    )                                                                      AS containment_rate
FROM interactions
GROUP BY 1;
