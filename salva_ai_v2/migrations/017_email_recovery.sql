ALTER TABLE establishment_account ADD COLUMN email TEXT;
ALTER TABLE establishment_account ADD COLUMN email_subject TEXT;
ALTER TABLE establishment_account ADD COLUMN email_issuer TEXT;
ALTER TABLE establishment_account ADD COLUMN email_verified_at TEXT;
CREATE TABLE email_auth_clock(id INTEGER PRIMARY KEY CHECK(id=1),last_time REAL NOT NULL DEFAULT 0);
INSERT INTO email_auth_clock VALUES(1,0);
CREATE TABLE email_auth_challenges(
 id TEXT PRIMARY KEY,
 purpose TEXT NOT NULL CHECK(purpose IN ('SETUP','ENROLL','RECOVER')),
 email TEXT NOT NULL,
 issuer TEXT NOT NULL,
 expected_subject TEXT,
 account_revision INTEGER,
 created_at REAL NOT NULL,
 next_send_at REAL NOT NULL,
 expires_at REAL NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0,
 state TEXT NOT NULL CHECK(state IN ('SENDING','SENT','VERIFYING','VERIFIED','FAILED','LOCKED','CANCELED','COMPLETED')),
 verify_after REAL NOT NULL DEFAULT 0
);
