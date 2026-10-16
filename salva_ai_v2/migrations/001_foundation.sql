CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, checksum TEXT NOT NULL);
CREATE TABLE command_results(id TEXT PRIMARY KEY, kind TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE audit_events(id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL, kind TEXT NOT NULL, object_id TEXT NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL, reason TEXT);

