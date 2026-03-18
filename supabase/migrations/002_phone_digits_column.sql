-- Add generated column for phone lookups without E.164 '+' prefix.
-- The Supabase n8n node applies encodeURI() to filter strings, which
-- preserves '+' literally — PostgREST interprets it as a space.
-- By querying phone_digits (digits only), we avoid the encoding issue
-- while keeping the canonical E.164 format in phone_number.

ALTER TABLE customers
    ADD COLUMN phone_digits TEXT GENERATED ALWAYS AS (replace(phone_number, '+', '')) STORED;

CREATE INDEX idx_customers_phone_digits ON customers (phone_digits);
