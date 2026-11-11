-- Work queue for humans: one row per thing somebody has to do after a call.
-- Written by the end-of-call-report workflow.
--
--   escalation: caller asked for a human, or the call ended with negative sentiment
--   callback:   the agent promised or the analysis flagged a follow-up
--
-- vapi_call_id is a soft reference to interactions.vapi_call_id (no FK on purpose:
-- a follow-up must still be recorded if the interactions write failed).

CREATE TABLE IF NOT EXISTS follow_ups (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vapi_call_id TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('escalation', 'callback')),
    reason       TEXT DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Same dedup idea as interactions.vapi_call_id: a re-delivered end-of-call
    -- report cannot open the same follow-up twice.
    CONSTRAINT follow_ups_call_kind_unique UNIQUE (vapi_call_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_follow_ups_open
    ON follow_ups (created_at DESC) WHERE status = 'open';

-- n8n writes with the service role key, which bypasses RLS. Enabling RLS with no
-- policies keeps the table invisible to the anon/authenticated API roles.
ALTER TABLE follow_ups ENABLE ROW LEVEL SECURITY;
