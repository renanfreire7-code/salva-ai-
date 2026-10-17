from pathlib import Path
from tests_v2.support import DatabaseCase


class CashTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.security.service import SecurityService
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.cash = CashService(self.db, self.security, self.clock)

    def grant(self, kind):
        return self.security.authorize('681942', kind)

    def test_movement_and_duplicate(self):
        session = self.cash.open(10000, 'open1')
        self.cash.move('WITHDRAWAL', 2000, 'Retirada teste', self.grant('cash.withdraw'), 'move1')
        self.cash.move('WITHDRAWAL', 2000, 'Retirada teste', None, 'move1')
        self.assertEqual(self.cash.position(session).expected_cents, 8000)
        self.cash.move('REINFORCEMENT', 1000, 'Reforço teste', self.grant('cash.reinforce'), 'move2')
        self.assertEqual(self.cash.position(session).expected_cents, 9000)

    def test_single_open_and_no_negative_balance(self):
        from salva_ai_v2.common.errors import BusinessError
        session = self.cash.open(1000, 'open1')
        with self.assertRaises(BusinessError):
            self.cash.open(0, 'open2')
        with self.assertRaises(BusinessError):
            self.cash.move('WITHDRAWAL', 2000, 'Retirada teste', self.grant('cash.withdraw'), 'bad1')
        self.assertEqual(self.cash.position(session).expected_cents, 1000)

    def test_invalid_or_unauthorized_movement(self):
        from salva_ai_v2.common.errors import BusinessError
        self.cash.open(0, 'open1')
        with self.assertRaises(BusinessError):
            self.cash.move('REINFORCEMENT', 100, 'Reforço teste', None, 'bad1')
        self.assertEqual(self.scalar('SELECT count(*) FROM cash_entries'), 0)
