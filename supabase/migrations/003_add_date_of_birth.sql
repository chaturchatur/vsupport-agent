-- Add date_of_birth column to customers table for identity verification.
-- The voice agent asks callers for their DOB after phone lookup,
-- and compares it against this field before revealing claim information.

ALTER TABLE customers ADD COLUMN date_of_birth DATE;
