-- Vsupport Agent: Supabase PostgreSQL schema
-- Migrated from Airtable to remove 5 req/sec rate limit, add proper indexing,
-- and enable atomic dedup via UNIQUE constraint on vapi_call_id.

-- ============================================================
-- Customers table (read-only for the voice agent)
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    phone_number TEXT NOT NULL,          -- E.164 format, e.g. +14155551234
    claim_number TEXT NOT NULL UNIQUE,
    claim_status TEXT NOT NULL CHECK (claim_status IN ('approved', 'pending', 'requires_documentation')),
    claim_details TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes matching the three lookup modes used by the voice agent
CREATE INDEX idx_customers_phone ON customers (phone_number);
CREATE INDEX idx_customers_last_name ON customers (LOWER(last_name));
CREATE INDEX idx_customers_claim_number ON customers (UPPER(claim_number));

-- ============================================================
-- Interactions table (written by log_interaction + end-of-call-report)
-- ============================================================
CREATE TABLE IF NOT EXISTS interactions (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    caller_name  TEXT DEFAULT 'Unknown',
    phone_number TEXT DEFAULT '',
    summary      TEXT DEFAULT '',
    sentiment    TEXT DEFAULT 'neutral' CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    timestamp    TIMESTAMPTZ DEFAULT NOW(),
    vapi_call_id TEXT UNIQUE,            -- KEY FIX: enables INSERT ON CONFLICT DO NOTHING for atomic dedup
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interactions_vapi_call_id ON interactions (vapi_call_id);
CREATE INDEX idx_interactions_timestamp ON interactions (timestamp DESC);
