ALTER TABLE order_items ADD COLUMN name_snapshot TEXT NOT NULL DEFAULT '';
ALTER TABLE sale_items ADD COLUMN name_snapshot TEXT NOT NULL DEFAULT '';
UPDATE order_items SET name_snapshot=(SELECT name FROM products WHERE products.id=order_items.product_id);
UPDATE sale_items SET name_snapshot=(SELECT name FROM products WHERE products.id=sale_items.product_id);
ALTER TABLE delivery_orders ADD COLUMN payment_timing TEXT NOT NULL DEFAULT 'UNSPECIFIED';
ALTER TABLE delivery_orders ADD COLUMN payment_channel TEXT;
ALTER TABLE delivery_orders ADD COLUMN change_for_cents INTEGER CHECK(change_for_cents IS NULL OR change_for_cents>=0);
ALTER TABLE delivery_orders ADD COLUMN link_reference TEXT NOT NULL DEFAULT '';
