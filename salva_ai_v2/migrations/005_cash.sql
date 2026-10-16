CREATE TABLE cash_sessions(id INTEGER PRIMARY KEY, opened_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'OPEN' CHECK(state IN ('OPEN','CLOSING','CLOSED')), opening_cents INTEGER NOT NULL CHECK(opening_cents>=0), closed_at TEXT, counted_cents INTEGER, expected_cents INTEGER, variance_cents INTEGER, reason TEXT);
CREATE UNIQUE INDEX one_active_session ON cash_sessions((1)) WHERE state IN ('OPEN','CLOSING');
CREATE TABLE cash_entries(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES cash_sessions(id), occurred_at TEXT NOT NULL, delta_cents INTEGER NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL UNIQUE, reason TEXT);

