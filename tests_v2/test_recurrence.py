from pathlib import Path
from datetime import date
from tests_v2.support import DatabaseCase


class RecurrenceTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.finance.recurrence import RecurrenceService
        from salva_ai_v2.finance.service import FinanceService
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.cash.service import CashService
        self.security = SecurityService(self.db)
        self.security.setup('681')
        cash = CashService(self.db, self.security)
        self.finance = FinanceService(self.db, cash, self.security)
        self.recurrence = RecurrenceService(self.db, self.finance, self.clock)

    def test_short_month_once_and_pending(self):
        from salva_ai_v2.finance.models import ExpenseDraft
        template = ExpenseDraft('Aluguel', 'Aluguel', 100000, date(2028,2,1), date(2028,2,29))
        rule = self.recurrence.create_rule(template, 31, '2028-02', 'rule1')
        a = self.recurrence.generate(rule, '2028-02', 'gen1')
        b = self.recurrence.generate(rule, '2028-02', 'gen2')
        self.assertEqual(a, b)
        self.assertEqual(self.db.conn.execute('SELECT due_on FROM obligations WHERE id=?', (a,)).fetchone()[0], '2028-02-29')
        self.assertEqual(self.finance.paid_cents(a), 0)

    def test_rule_edit_does_not_rewrite_occurrence(self):
        from salva_ai_v2.finance.models import ExpenseDraft
        template = ExpenseDraft('Aluguel', 'Aluguel', 100000, date(2026,1,1), date(2026,1,31))
        rule = self.recurrence.create_rule(template, 31, '2026-01', 'rule1')
        first = self.recurrence.generate(rule, '2026-01', 'gen1')
        changed = ExpenseDraft('Aluguel', 'Aluguel', 110000, date(2026,1,1), date(2026,1,31))
        grant = self.security.authorize('681', 'recurrence.edit')
        self.recurrence.update_rule(rule, changed, 31, True, grant, 'Reajuste aluguel', 'edit1')
        second = self.recurrence.generate(rule, '2026-02', 'gen2')
        self.assertEqual(self.db.conn.execute('SELECT amount_cents FROM obligations WHERE id=?', (first,)).fetchone()[0], 100000)
        self.assertEqual(self.db.conn.execute('SELECT due_on,amount_cents FROM obligations WHERE id=?', (second,)).fetchone()[:], ('2026-02-28', 110000))
