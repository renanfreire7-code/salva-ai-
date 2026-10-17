ALTER TABLE admin_credentials ADD COLUMN pin_length INTEGER NOT NULL DEFAULT 6 CHECK(pin_length IN (3,6));
CREATE TABLE establishment_account(
 id INTEGER PRIMARY KEY CHECK(id=1),
 username TEXT NOT NULL,
 salt BLOB NOT NULL,
 password_hash BLOB NOT NULL,
 iterations INTEGER NOT NULL,
 failures INTEGER NOT NULL DEFAULT 0,
 blocked_until REAL NOT NULL DEFAULT 0,
 last_time REAL NOT NULL DEFAULT 0,
 revision INTEGER NOT NULL DEFAULT 1
);
