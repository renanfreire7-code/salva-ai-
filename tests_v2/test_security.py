from pathlib import Path
from tests_v2.support import DatabaseCase


class SecurityTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.security.service import SecurityService
        self.Service = SecurityService
        self.security = self.Service(self.db, self.clock)
        self.key = self.security.setup('681942')

    def test_recovery_rotates_and_pin_not_plaintext(self):
        from salva_ai_v2.common.errors import AuthorizationError
        new_key = self.security.recover(self.key, '729516')
        self.assertNotEqual(new_key, self.key)
        with self.assertRaises(AuthorizationError):
            self.security.recover(self.key, '123456')
        grant = self.security.authorize('729516', 'expense.delete')
        self.assertEqual(grant.action, 'expense.delete')
        dump = '\n'.join(self.db.conn.iterdump())
        for secret in (self.key, new_key, '681942', '729516'):
            self.assertNotIn(secret, dump)

    def test_action_and_use_once(self):
        from salva_ai_v2.common.errors import AuthorizationError
        grant = self.security.authorize('681942', 'expense.delete')
        with self.assertRaises(AuthorizationError):
            with self.db.transaction():
                self.security.consume(grant, 'stock.adjust')
        with self.db.transaction():
            self.security.consume(grant, 'expense.delete')
        with self.assertRaises(AuthorizationError):
            with self.db.transaction():
                self.security.consume(grant, 'expense.delete')

    def test_rollback_does_not_consume_grant(self):
        grant = self.security.authorize('681942', 'stock.adjust')
        with self.assertRaises(ValueError):
            with self.db.transaction():
                self.security.consume(grant, 'stock.adjust')
                raise ValueError('falha')
        with self.db.transaction():
            self.security.consume(grant, 'stock.adjust')

    def test_expired_or_forged_grant(self):
        from salva_ai_v2.common.errors import AuthorizationError
        from salva_ai_v2.security.models import AdminGrant
        grant = self.security.authorize('681942', 'stock.adjust')
        self.clock.advance(61)
        with self.assertRaises(AuthorizationError):
            with self.db.transaction():
                self.security.consume(grant, 'stock.adjust')
        with self.assertRaises(AuthorizationError):
            with self.db.transaction():
                self.security.consume(AdminGrant('fake', 'stock.adjust', 9999999999), 'stock.adjust')

    def test_lock_survives_restart_and_clock_rollback(self):
        from salva_ai_v2.common.errors import AuthorizationError
        for _ in range(5):
            with self.assertRaises(AuthorizationError):
                self.security.authorize('000000', 'x')
        self.security = self.Service(self.db, self.clock)
        self.clock.advance(-100)
        with self.assertRaises(AuthorizationError):
            self.security.authorize('681942', 'x')
        self.clock.advance(131)
        self.assertEqual(self.security.authorize('681942', 'x').action, 'x')

    def test_pin_format_and_repeated_setup(self):
        from salva_ai_v2.common.errors import BusinessError
        for value in ('123', 'abcdef', '１２３４５６'):
            with self.assertRaises(BusinessError):
                self.security.recover(self.key, value)
        with self.assertRaises(BusinessError):
            self.security.setup('123456')
