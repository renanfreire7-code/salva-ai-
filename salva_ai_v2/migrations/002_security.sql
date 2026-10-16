CREATE TABLE admin_credentials(id INTEGER PRIMARY KEY CHECK(id=1), salt BLOB NOT NULL, pin_hash BLOB NOT NULL, recovery_salt BLOB NOT NULL, recovery_hash BLOB NOT NULL, iterations INTEGER NOT NULL, failures INTEGER NOT NULL DEFAULT 0, blocked_until REAL NOT NULL DEFAULT 0, last_time REAL NOT NULL DEFAULT 0);
CREATE TABLE consumed_grants(id TEXT PRIMARY KEY);

