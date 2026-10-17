import sqlite3
from unittest.mock import patch
from tests_v2.support import DatabaseCase
from tests_v2.security_support import seed_legacy_pin
from salva_ai_v2.security.service import SecurityService
from salva_ai_v2.common.errors import BusinessError,AuthorizationError


class AccountTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("salva_ai_v2.security.accounts"),"Conta offline ainda não implementada")
        from salva_ai_v2.security.accounts import AccountService
        self.AccountService=AccountService;self.security=SecurityService(self.db,self.clock)
        self.accounts=AccountService(self.db,self.security,self.clock)

    def create(self,password='Senha fictícia 42'):
        return self.accounts.create(' Meu Bar ',password,'007')

    def test_single_account_validates_username_password_pin_and_hashes_secrets(self):
        self.assertEqual(self.accounts.mode,'SETUP')
        for user,password,pin in [('','12345678','007'),('bar','1234567','007'),('bar','12345678','12')]:
            with self.assertRaises(BusinessError):self.accounts.create(user,password,pin)
        key=self.create();self.assertEqual(self.accounts.mode,'LOGIN')
        session=self.accounts.login('MEU BAR','Senha fictícia 42');self.accounts.validate_session(session)
        with self.assertRaises(BusinessError):self.create()
        dump='\n'.join(self.db.conn.iterdump())
        for secret in ('Senha fictícia 42','007',key):self.assertNotIn(repr(secret),dump)

    def test_password_whitespace_and_unicode_roundtrip(self):
        self.create('  café 42 ')
        with self.assertRaises(AuthorizationError):self.accounts.login('meu bar','café 42')
        self.accounts.validate_session(self.accounts.login('meu bar','  café 42 '))

    def test_transition_requires_existing_pin_or_recovery_proof(self):
        seed_legacy_pin(self.db);self.assertEqual(self.accounts.mode,'TRANSITION')
        with self.assertRaises(AuthorizationError):self.create()
        wrong=self.security.authorize('681942','stock.adjust')
        with self.assertRaises(AuthorizationError):self.accounts.create('bar','12345678','007',wrong)
        proof=self.security.authorize('681942','access.configure')
        self.accounts.create('bar','12345678','007',proof)
        self.assertEqual(self.security.pin_length,3)
        self.security.authorize('007','stock.adjust')
        with self.assertRaises(BusinessError):self.security.authorize('681942','stock.adjust')
        with self.assertRaises(AuthorizationError):self.security.validate(proof,'access.configure')

    def test_transition_failure_rolls_back_credentials(self):
        key=seed_legacy_pin(self.db);before=tuple(self.db.conn.execute('SELECT * FROM admin_credentials').fetchone())
        proof=self.security.authorize('681942','access.configure')
        # A DB trigger fails after the PIN change but before the account insert commits.
        self.db.conn.execute("CREATE TRIGGER fail_account BEFORE INSERT ON establishment_account BEGIN SELECT RAISE(ABORT,'disk failure'); END")
        with self.assertRaises(sqlite3.Error):self.accounts.create('bar','12345678','007',proof)
        row=self.db.conn.execute('SELECT * FROM admin_credentials').fetchone()
        self.assertEqual(row['pin_hash'],before[2]);self.assertEqual(row['pin_length'],6)
        self.assertEqual(self.accounts.mode,'TRANSITION')
        self.security.authorize_recovery(key,'access.configure')
        self.db.conn.execute('DROP TRIGGER fail_account')
        self.accounts.create('bar','12345678','007',proof)

    def test_five_failures_wait_survives_restart_and_clock_rollback(self):
        self.create()
        for index in range(5):
            with self.assertRaises(AuthorizationError):self.accounts.login('inexistente' if index%2 else 'meu bar','incorreta')
        self.assertEqual(self.accounts.remaining_wait(),30)
        self.accounts=self.AccountService(self.db,self.security,self.clock);self.clock.advance(-100)
        with self.assertRaises(AuthorizationError):self.accounts.login('meu bar','Senha fictícia 42')
        self.assertEqual(self.security.remaining_wait(),0)
        self.clock.advance(131);self.accounts.login('meu bar','Senha fictícia 42')

    def test_recovery_rotates_key_and_invalidates_session_and_grants(self):
        key=self.create();session=self.accounts.login('meu bar','Senha fictícia 42');grant=self.security.authorize('007','stock.adjust')
        newkey=self.accounts.recover(key,'Outra senha 42','009')
        self.assertNotEqual(key,newkey)
        with self.assertRaises(AuthorizationError):self.accounts.validate_session(session)
        with self.assertRaises(AuthorizationError):self.security.validate(grant,'stock.adjust')
        with self.assertRaises(AuthorizationError):self.accounts.recover(key,'Outra senha 43','008')
        with self.assertRaises(AuthorizationError):self.accounts.login('meu bar','Senha fictícia 42')
        self.accounts.login('meu bar','Outra senha 42');self.security.authorize('009','stock.adjust')

    def test_legacy_recovery_proof_and_logout(self):
        key=seed_legacy_pin(self.db);proof=self.security.authorize_recovery(key,'access.configure')
        self.accounts.create('bar','12345678','007',proof)
        session=self.accounts.login('bar','12345678');self.accounts.logout()
        with self.assertRaises(AuthorizationError):self.accounts.validate_session(session)
