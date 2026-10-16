CREATE TABLE obligation_payments(id INTEGER PRIMARY KEY, obligation_id INTEGER NOT NULL REFERENCES obligations(id), amount_cents INTEGER NOT NULL CHECK(amount_cents>0), paid_on TEXT NOT NULL, method TEXT NOT NULL, from_drawer INTEGER NOT NULL, cash_entry_id INTEGER REFERENCES cash_entries(id), corrected INTEGER NOT NULL DEFAULT 0);
CREATE TABLE payment_corrections(id INTEGER PRIMARY KEY, payment_id INTEGER NOT NULL UNIQUE REFERENCES obligation_payments(id), action TEXT NOT NULL, physical_return_cents INTEGER NOT NULL, reason TEXT NOT NULL, occurred_at TEXT NOT NULL);

