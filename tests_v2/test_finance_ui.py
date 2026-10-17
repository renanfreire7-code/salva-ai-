from pathlib import Path
from datetime import date
import unittest
import tempfile


class FinanceUITest(unittest.TestCase):
    def test_default_period_and_text_states(self):
        from tests_v2.application_support import build_test_application as build_application
        from salva_ai_v2.finance.models import ExpenseDraft
        with tempfile.TemporaryDirectory() as folder:
            app = build_application(Path(folder))
            try:
                today = app.services.clock.today()
                app.services.finance.add_expense(ExpenseDraft('Conta teste', 'Energia', 2000, today, today), False, 'expense1')
                app.refresh()
                view = app.finance_view
                self.assertEqual(view.filters().date_basis, 'incurred')
                self.assertEqual(view.filters().start.month, today.month)
                values = view.tree.item(view.tree.get_children()[0], 'values')
                self.assertIn('Pendente', values)
            finally:
                app.close()
