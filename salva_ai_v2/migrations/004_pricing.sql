CREATE TABLE promotions(product_id INTEGER PRIMARY KEY REFERENCES products(id), group_qty INTEGER NOT NULL CHECK(group_qty>=2), group_cents INTEGER NOT NULL CHECK(group_cents>0), active INTEGER NOT NULL);

