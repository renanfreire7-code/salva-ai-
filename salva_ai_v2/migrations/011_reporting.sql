CREATE TABLE financial_settings(key TEXT PRIMARY KEY, value_cents INTEGER);
ALTER TABLE delivery_returns ADD COLUMN returned_at TEXT;
ALTER TABLE collections ADD COLUMN rate_bp INTEGER;
ALTER TABLE collections ADD COLUMN fee_cents INTEGER NOT NULL DEFAULT 0;

