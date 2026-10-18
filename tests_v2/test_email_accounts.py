import sqlite3
from unittest.mock import patch
from tests_v2.support import DatabaseCase
from tests_v2.email_support import EmailHarness
from tests_v2.test_email_provider import EMAIL
from salva_ai_v2.security.accounts import AccountService
from salva_ai_v2.security.service import SecurityService
from salva_ai_v2.maintenance.backup import BackupService
from salva_ai_v2.common.errors import BusinessError


class EmailAccountsTests(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.security=SecurityService(self.db,self.clock)
        self.h=EmailHarness(self.db,self.clock)
        self.backups=BackupService(self.db,self.root/'backups')
        self.accounts=AccountService(self.db,self.security,self.clock,emails=self.h.flow,backups=self.backups)

    def old(self):
        self.accounts.create('old-user','old-password','007')
        return self.accounts.login('old-user','old-password')

    def account(self):return dict(self.db.conn.execute('SELECT * FROM establishment_account').fetchone())
    def pin(self):
        row=dict(self.db.conn.execute('SELECT * FROM admin_credentials').fetchone())
        return {key:row[key] for key in ('salt','pin_hash','recovery_salt','recovery_hash','iterations','pin_length')}

    def test_reenroll_preserves_business_pin_and_account_id(self):
        session=self.old();before=self.pin();revision=self.account()['revision']
        proof=self.h.proof()
        self.accounts.reenroll_with_email(proof,' New User ',' new-password ','007')
        row=self.account();self.assertEqual((row['id'],row['username'],row['email'],row['revision']),(1,'new user',EMAIL,revision+1))
        self.assertEqual(before,self.pin());self.assertEqual(len(self.backups.list_backups()),1)
        self.security.authorize('007','fixture')
        with self.assertRaises(BusinessError):self.accounts.validate_session(session)
        self.accounts.login('new user',' new-password ')

    def test_wrong_pin_or_bound_account_does_not_change_credentials(self):
        self.old();proof=self.h.proof();before=self.account()
        with self.assertRaises(BusinessError):self.accounts.reenroll_with_email(proof,'new','new-password','008')
        self.assertEqual(before,self.account());self.assertEqual(self.scalar('SELECT failures FROM admin_credentials'),1)
        self.accounts.reenroll_with_email(proof,'new','new-password','007')
        bound=self.account()
        with self.assertRaises(BusinessError):self.accounts.reenroll_with_email(proof,'other','other-password','007')
        self.assertEqual(bound,self.account())

    def test_backup_failure_blocks_reenrollment(self):
        session=self.old();proof=self.h.proof();before=self.account()
        for method in ('create','verify'):
            with patch.object(self.backups,method,side_effect=BusinessError('backup unavailable')):
                with self.assertRaises(BusinessError):self.accounts.reenroll_with_email(proof,'new','new-password','007')
            self.assertEqual(before,self.account());self.accounts.validate_session(session)
        self.accounts.login('old-user','old-password')

    def test_database_failure_after_remote_otp_keeps_previous_access(self):
        session=self.old();proof=self.h.proof();before=self.account();pin=self.pin()
        self.db.conn.execute("CREATE TRIGGER fail_email BEFORE UPDATE OF username ON establishment_account BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.Error):self.accounts.reenroll_with_email(proof,'new','new-password','007')
        self.assertEqual(before,self.account());self.assertEqual(pin,self.pin());self.accounts.validate_session(session)
        self.h.flow.validate(proof,'ENROLL')
        self.db.conn.execute('DROP TRIGGER fail_email')
        self.accounts.reenroll_with_email(proof,'new','new-password','007')

    def test_email_recovery_changes_login_only(self):
        self.old();self.accounts.reenroll_with_email(self.h.proof(),'new','new-password','007')
        session=self.accounts.login('new','new-password');pin=self.pin();bound=self.account()
        self.h.advance(61);proof=self.h.proof('RECOVER')
        self.accounts.recover_with_email(proof,'recovered','recovered-password')
        row=self.account()
        for key in ('email','email_subject','email_issuer','email_verified_at'):self.assertEqual(bound[key],row[key])
        self.assertEqual(pin,self.pin());self.security.authorize('007','fixture')
        with self.assertRaises(BusinessError):self.accounts.validate_session(session)
        self.accounts.login('recovered','recovered-password')

    def test_create_and_legacy_transition_require_confirmed_email_in_new_api(self):
        with self.assertRaises(BusinessError):self.accounts.create_with_email(None,'new','new-password','007')
        self.assertFalse(self.security.configured)
        self.accounts.create_with_email(self.h.proof('SETUP'),'new','new-password','007')
        self.assertEqual(self.account()['email'],EMAIL)

    def test_legacy_transition_requires_admin_authorization(self):
        self.security.setup('007');proof=self.h.proof('SETUP')
        with self.assertRaises(BusinessError):self.accounts.create_with_email(proof,'new','new-password','009')
        grant=self.security.authorize('007','access.configure')
        self.accounts.create_with_email(proof,'new','new-password','009',legacy_proof=grant)
        self.security.authorize('009','fixture')
