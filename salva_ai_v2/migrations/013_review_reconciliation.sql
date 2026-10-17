CREATE TABLE receipt_events(
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES cash_sessions(id),
    occurred_at TEXT NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('MONEY','PIX','DEBIT','CREDIT')),
    delta_cents INTEGER NOT NULL,
    custodian TEXT NOT NULL CHECK(custodian IN ('BAR','COURIER')),
    source TEXT NOT NULL UNIQUE
);
CREATE TABLE supplier_credit_settlements(
    id INTEGER PRIMARY KEY,
    credit_id INTEGER NOT NULL REFERENCES supplier_credits(id),
    amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
    mode TEXT NOT NULL CHECK(mode IN ('RECEIPT','OFFSET')),
    method TEXT,
    paid_on TEXT NOT NULL,
    payment_id INTEGER REFERENCES obligation_payments(id),
    cash_entry_id INTEGER REFERENCES cash_entries(id)
);

-- Recover facts from earlier development snapshots without changing cash entries.
INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source)
SELECT s.session_id,s.sold_at,s.method,s.total_cents,'BAR','sale:'||s.id
FROM sales s JOIN orders o ON o.id=s.order_id WHERE o.kind<>'DELIVERY';

INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source)
SELECT COALESCE((SELECT id FROM cash_sessions WHERE opened_at<=c.collected_at AND (closed_at IS NULL OR closed_at>=c.collected_at) ORDER BY id DESC LIMIT 1),o.session_id),
c.collected_at,c.method,c.amount_cents,c.custodian,'collection:'||c.id
FROM collections c JOIN orders o ON o.id=c.order_id;

INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source)
SELECT sc.session_id,a.occurred_at,s.method,-s.total_cents,'BAR','historic-refund:'||a.id
FROM audit_events a JOIN sales s ON s.id=json_extract(a.after_json,'$.sale_id')
JOIN sale_corrections sc ON sc.sale_id=s.id
WHERE a.kind='sale.reversed' AND json_type(a.after_json,'$.refund')='object';

INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source)
SELECT COALESCE((SELECT id FROM cash_sessions WHERE opened_at<=a.occurred_at AND (closed_at IS NULL OR closed_at>=a.occurred_at) ORDER BY id DESC LIMIT 1),s.session_id),
a.occurred_at,s.method,-s.total_cents,'BAR','historic-refund:'||a.id
FROM audit_events a JOIN sales s ON s.id=json_extract(a.after_json,'$.sale_id') WHERE a.kind='sale.refunded';

INSERT INTO receipt_events(session_id,occurred_at,method,delta_cents,custodian,source)
SELECT COALESCE((SELECT id FROM cash_sessions WHERE opened_at<=a.occurred_at AND (closed_at IS NULL OR closed_at>=a.occurred_at) ORDER BY id DESC LIMIT 1),o.session_id),
a.occurred_at,json_extract(a.after_json,'$.method'),-json_extract(a.after_json,'$.amount_cents'),
CASE WHEN json_extract(a.after_json,'$.method')='MONEY' AND json_extract(a.after_json,'$.from_drawer')=0 THEN 'COURIER' ELSE 'BAR' END,
'historic-refund:'||a.id
FROM audit_events a JOIN orders o ON o.id=json_extract(a.after_json,'$.order_id') WHERE a.kind='delivery.refunded';

UPDATE audit_events SET object_id=(SELECT CAST(json_extract(c.result,'$.id') AS TEXT) FROM command_results c WHERE c.id=audit_events.object_id AND c.kind=audit_events.kind)
WHERE kind IN ('sale.confirmed','delivery.sale') AND EXISTS(SELECT 1 FROM command_results c WHERE c.id=audit_events.object_id AND json_extract(c.result,'$.id') IS NOT NULL);
