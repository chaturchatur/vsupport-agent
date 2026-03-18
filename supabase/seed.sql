-- Seed data: same 5 sample customers as Airtable
-- Two Johnsons for multi-match testing. Emily Chen has claim_details populated.

INSERT INTO customers (first_name, last_name, phone_number, claim_number, claim_status, claim_details, date_of_birth) VALUES
    ('Sarah',   'Johnson',  '+14155551234', 'CLM-2024-001', 'approved',                '',                                                '1985-03-15'),
    ('Michael', 'Johnson',  '+14155555678', 'CLM-2024-002', 'pending',                 '',                                                '1990-07-22'),
    ('Emily',   'Chen',     '+12125559876', 'CLM-2024-003', 'requires_documentation',  'Missing proof of loss form and photos of damage', '1978-11-04'),
    ('David',   'Martinez', '+13105554321', 'CLM-2024-004', 'approved',                '',                                                '1995-01-30'),
    ('Lisa',    'Park',     '+17185557777', 'CLM-2024-005', 'pending',                 '',                                                '1988-09-12')
ON CONFLICT (claim_number) DO NOTHING;
