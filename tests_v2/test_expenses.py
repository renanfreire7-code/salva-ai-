from pathlib import Path
from datetime import date
from tests_v2.support import DatabaseCase


class ExpensesTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.finance.service import FinanceService
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.cash = CashService(self.db, self.security)
        self.finance = FinanceService(self.db, self.cash, self.security, self.clock)

    def grant(self, action):
        return self.security.authorize('681942', action)

    def draft(self, amount=100000, description='Aluguel'):
        from salva_ai_v2.finance.models import ExpenseDraft
        return ExpenseDraft(description, 'Aluguel', amount, date(2026, 10, 1), date(2026, 10, 16))

    def filters(self, **kwargs):
        from salva_ai_v2.finance.models import ExpenseFilter
        return ExpenseFilter(date(2026,10,1), date(2026,10,31), 'incurred', **kwargs)

    def test_duplicate_then_soft_delete(self):
        from salva_ai_v2.finance.service import DuplicateExpenseError
        a = self.finance.add_expense(self.draft(), False, 'rent1')
        with self.assertRaises(DuplicateExpenseError):
            self.finance.add_expense(self.draft(description='  ALUGUÉL '), False, 'dup1')
        b = self.finance.add_expense(self.draft(), True, 'rent2')
        self.finance.delete_expense(b, self.grant('expense.delete'), 'Lançamento duplicado', 'del1')
        self.assertEqual(self.finance.expense_totals(self.filters()).commitments_cents, 100000)
        self.assertEqual(len(self.finance.list_expenses(self.filters(include_deleted=True))), 2)
        self.assertEqual(len(self.finance.list_expenses(self.filters())), 1)

    def test_edit_records_before_after(self):
        id = self.finance.add_expense(self.draft(), False, 'rent1')
        self.finance.edit_expense(id, self.draft(90000), False, self.grant('expense.edit'), 'Valor corrigido', 'edit1')
        row = self.db.conn.execute("SELECT * FROM audit_events WHERE kind='expense.changed' AND object_id=?", (str(id),)).fetchone()
        self.assertIn('100000', row['before_json'])
        self.assertIn('90000', row['after_json'])
        self.assertEqual(self.finance.expense_totals(self.filters()).commitments_cents, 90000)

    def test_due_today_not_overdue_and_filters_are_safe(self):
        self.finance.add_expense(self.draft(description="Aluguel d'Ávila"), False, 'rent1')
        rows = self.finance.list_expenses(self.filters(text="d'ávila"))
        self.assertEqual(rows[0].status, 'PENDING')
        self.clock.advance(86400)
        self.assertEqual(self.finance.list_expenses(self.filters())[0].status, 'OVERDUE')
        self.assertEqual(self.finance.expense_totals(self.filters()).overdue_cents, 100000)
        self.assertEqual(self.finance.list_expenses(self.filters(text="' OR 1=1 --")), [])
