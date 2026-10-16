from datetime import date
from pathlib import Path
from tests_v2.support import DatabaseCase


class ObligationPaymentsTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.finance.service import FinanceService
        self.assertTrue(hasattr(FinanceService, 'pay_obligation'), 'Pagamento ainda não implementado')
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.finance.models import ExpenseDraft
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.cash = CashService(self.db, self.security)
        self.finance = FinanceService(self.db, self.cash, self.security, self.clock)
        self.session = self.cash.open(10000, 'open1')
        self.expense = self.finance.add_expense(ExpenseDraft('Energia', 'Energia', 2000, date(2026,10,1), date(2026,10,16)), False, 'exp1')

    def grant(self, action):
        return self.security.authorize('681942', action)

    def test_paid_by_drawer_once_delete_does_not_return_cash(self):
        p = self.finance.pay_obligation(self.expense, 2000, self.clock.today(), 'MONEY', True, self.grant('cash.withdraw'), 'paid1')
        self.assertEqual(self.finance.pay_obligation(self.expense, 2000, self.clock.today(), 'MONEY', True, None, 'paid1'), p)
        self.assertEqual(self.cash.position(self.session).expected_cents, 8000)
        self.finance.delete_expense(self.expense, self.grant('expense.delete'), 'Registro incorreto', 'del1')
        self.assertEqual(self.cash.position(self.session).expected_cents, 8000)

    def test_digital_does_not_touch_drawer_or_accept_overpayment(self):
        from salva_ai_v2.common.errors import BusinessError
        self.finance.pay_obligation(self.expense, 2000, self.clock.today(), 'PIX', False, None, 'paid1')
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)
        with self.assertRaises(BusinessError):
            self.finance.pay_obligation(self.expense, 1, self.clock.today(), 'PIX', False, None, 'over1')

    def test_correction_requires_explicit_money_return(self):
        p = self.finance.pay_obligation(self.expense, 2000, self.clock.today(), 'MONEY', True, self.grant('cash.withdraw'), 'paid1')
        self.finance.correct_payment(p, 'VOID', 0, self.grant('payment.correct'), 'Pagamento incorreto', 'correct1')
        self.assertEqual(self.cash.position(self.session).expected_cents, 8000)
        self.assertEqual(self.finance.paid_cents(self.expense), 0)
