CREATE TABLE delivery_settings(id INTEGER PRIMARY KEY CHECK(id=1), customer_fee_cents INTEGER NOT NULL CHECK(customer_fee_cents>=0), courier_fee_cents INTEGER NOT NULL CHECK(courier_fee_cents>=0));
INSERT INTO delivery_settings VALUES(1,0,0);
CREATE TABLE delivery_orders(order_id INTEGER PRIMARY KEY REFERENCES orders(id), phone TEXT NOT NULL, address TEXT NOT NULL, reference TEXT NOT NULL, method TEXT NOT NULL, collection TEXT NOT NULL, delivery_fee_cents INTEGER NOT NULL, courier_fee_cents INTEGER NOT NULL, previous_order_id INTEGER REFERENCES orders(id));
CREATE TABLE trips(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), dispatched_at TEXT NOT NULL, fee_cents INTEGER NOT NULL CHECK(fee_cents>=0));
CREATE TABLE collections(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id), amount_cents INTEGER NOT NULL CHECK(amount_cents>0), method TEXT NOT NULL, custodian TEXT NOT NULL, tendered_cents INTEGER, change_cents INTEGER NOT NULL, collected_at TEXT NOT NULL, settled_cents INTEGER NOT NULL DEFAULT 0 CHECK(settled_cents>=0), refunded_cents INTEGER NOT NULL DEFAULT 0 CHECK(refunded_cents>=0));
CREATE TABLE custody_entries(id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, delta_cents INTEGER NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL UNIQUE);
CREATE TABLE courier_floats(id INTEGER PRIMARY KEY, amount_cents INTEGER NOT NULL CHECK(amount_cents>0), returned_cents INTEGER NOT NULL DEFAULT 0);
CREATE TABLE settlements(id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, handed_in_cents INTEGER NOT NULL, paid_out_cents INTEGER NOT NULL, offset_cents INTEGER NOT NULL);
CREATE TABLE settlement_items(id INTEGER PRIMARY KEY, settlement_id INTEGER NOT NULL REFERENCES settlements(id), source_type TEXT NOT NULL, source_id INTEGER NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
CREATE TABLE delivery_returns(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>0), cogs_cents INTEGER NOT NULL);

