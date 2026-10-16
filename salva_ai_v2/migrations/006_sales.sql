CREATE TABLE orders(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'OPEN', session_id INTEGER NOT NULL REFERENCES cash_sessions(id), created_at TEXT NOT NULL);
CREATE TABLE order_items(order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>=0), unit_cents INTEGER NOT NULL, group_qty INTEGER, group_cents INTEGER, PRIMARY KEY(order_id,product_id));
CREATE TABLE sales(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), session_id INTEGER NOT NULL REFERENCES cash_sessions(id), sold_at TEXT NOT NULL, method TEXT NOT NULL, total_cents INTEGER NOT NULL, fee_cents INTEGER NOT NULL, rate_bp INTEGER, tendered_cents INTEGER, change_cents INTEGER NOT NULL, reversed INTEGER NOT NULL DEFAULT 0, delivery_fee_cents INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX one_active_sale_per_order ON sales(order_id) WHERE reversed=0;
CREATE TABLE sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES sales(id), product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>0), total_cents INTEGER NOT NULL, cogs_cents INTEGER NOT NULL, unit_cents INTEGER NOT NULL, group_qty INTEGER, group_cents INTEGER);
CREATE TABLE payment_settings(method TEXT PRIMARY KEY, rate_bp INTEGER CHECK(rate_bp>=0 AND rate_bp<=10000));
INSERT INTO payment_settings VALUES('MONEY',0);
INSERT INTO payment_settings VALUES('PIX',0);
INSERT INTO payment_settings VALUES('DEBIT',NULL);
INSERT INTO payment_settings VALUES('CREDIT',NULL);
CREATE TABLE sale_corrections(id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL UNIQUE REFERENCES sales(id), occurred_at TEXT NOT NULL, session_id INTEGER NOT NULL REFERENCES cash_sessions(id), returned INTEGER NOT NULL, reason TEXT NOT NULL);
CREATE TABLE refunds(id INTEGER PRIMARY KEY, sale_id INTEGER REFERENCES sales(id), order_id INTEGER REFERENCES orders(id), pending_cents INTEGER NOT NULL CHECK(pending_cents>=0), refunded_cents INTEGER NOT NULL DEFAULT 0);

