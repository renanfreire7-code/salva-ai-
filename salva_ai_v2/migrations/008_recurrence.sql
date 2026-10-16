CREATE TABLE recurring_rules(id INTEGER PRIMARY KEY, description TEXT NOT NULL, category TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0), due_day INTEGER NOT NULL CHECK(due_day BETWEEN 1 AND 31), start_month TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE recurring_occurrences(rule_id INTEGER NOT NULL REFERENCES recurring_rules(id), competence_month TEXT NOT NULL, obligation_id INTEGER NOT NULL UNIQUE REFERENCES obligations(id), PRIMARY KEY(rule_id,competence_month));

