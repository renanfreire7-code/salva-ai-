CREATE TABLE closing_jobs(session_id INTEGER PRIMARY KEY REFERENCES cash_sessions(id), command_id TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, complete INTEGER NOT NULL DEFAULT 0, report_path TEXT, backup_path TEXT, external_copy_ok INTEGER);
CREATE TABLE maintenance_settings(key TEXT PRIMARY KEY, value TEXT);

