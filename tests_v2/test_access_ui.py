from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.common.errors import AuthorizationError
from tests_v2.security_support import seed_legacy_pin


class AccessUITest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.app=build_application(self.root);self.addCleanup(self.app.close)
        from tests_v2.email_support import EmailHarness
        from tests_v2.support import FakeClock
        self.h=EmailHarness(self.app.db,FakeClock());self.app.emails=self.h.flow;self.app.accounts.emails=self.h.flow;self.app.require_login()

    def fill(self,view,**values):
        for key,value in values.items():view.inputs[key].delete(0,'end');view.inputs[key].insert(0,value)

    def confirm_email(self,wizard):
        from tests_v2.test_email_provider import EMAIL,session,user
        self.fill(wizard,email=EMAIL);self.h.transport.responses.append((200,{},{}));wizard.submit();self.h.runner.run_next()
        self.fill(wizard,code='654321');self.h.transport.responses.extend([(200,{},session()),(200,{},user())]);wizard.submit();self.h.runner.run_next()

    def signup(self):
        w=self.app.access_view.wizard;self.confirm_email(w)
        self.fill(w,username='bar',password='  café 42 ',password_confirm='  café 42 ',pin='007',pin_confirm='007')
        with patch('salva_ai_v2.ui.email_access.messagebox.showinfo'):self.assertTrue(w.submit())
        self.fill(self.app.access_view,password='  café 42 ');self.assertTrue(self.app.access_view.submit())

    def test_operational_views_and_shortcuts_absent_before_login(self):
        self.assertEqual(self.app.views,[])
        self.app.window.update();self.app.window.event_generate('<F1>');self.app.window.update()
        self.assertFalse(self.app.authenticated)
        with self.assertRaises(AuthorizationError):self.app.unlock(None)
        self.assertFalse(hasattr(self.app,'services'))

    def test_login_setup_recovery_and_show_password(self):
        self.signup();self.assertTrue(self.app.authenticated);self.assertEqual(len(self.app.views),11)
        self.app.require_login();view=self.app.access_view
        self.fill(view,username='bar',password='café 42');self.assertFalse(view.submit())
        self.assertEqual(view.inputs['username'].get(),'bar')
        self.fill(view,password='  café 42 ');view.toggle_password()
        self.assertEqual(view.inputs['password'].cget('show'),'');self.assertTrue(view.submit())
        self.app.require_login();self.app.access_view.set_mode('RECOVERY')
        self.assertEqual(set(self.app.access_view.wizard.inputs),{'email'})
        self.assertFalse(self.app.authenticated)

    def test_transition_accepts_old_pin_and_recovery_alternative(self):
        seed_legacy_pin(self.app.db);self.app.require_login();view=self.app.access_view
        self.assertEqual(view.mode,'TRANSITION');self.assertEqual(self.app.security.pin_length,6)
        w=view.wizard;self.confirm_email(w)
        self.fill(w,username='bar',password='12345678',password_confirm='12345678',pin='007',pin_confirm='007',legacy_pin='681942')
        with patch('salva_ai_v2.ui.email_access.messagebox.showinfo'):self.assertTrue(w.submit())
        self.assertEqual(self.app.security.pin_length,3);self.assertFalse(self.app.authenticated)

    def test_enter_focuses_action_before_submitting(self):
        self.signup();self.app.require_login();view=self.app.access_view
        self.fill(view,username='bar',password='  café 42 ');self.app.window.update()
        view.inputs['username'].focus_force();view.inputs['username'].event_generate('<Return>');self.app.window.update()
        self.assertEqual(view.focus_get(),view.inputs['password'])
        view.inputs['password'].event_generate('<Return>');self.app.window.update()
        self.assertEqual(view.focus_get(),view.primary_button);self.assertFalse(self.app.authenticated)
        view.primary_button.event_generate('<Return>');self.app.window.update();self.assertTrue(self.app.authenticated)

    def test_cancel_releases_database_and_instance_lock(self):
        self.app.close();self.assertIsNone(self.app.db.conn)
        reopened=build_application(self.root);reopened.close()

    def test_restore_requires_new_login_for_restored_credentials(self):
        self.signup();s=self.app.services
        backup=s.backups.create('manual','backup').path
        grant=self.app.security.authorize('007','backup.restore');preview=s.restore.prepare(backup,grant)
        s.restore.apply(preview,True)
        self.assertFalse(self.app.authenticated);self.assertEqual(self.app.views,[])
        self.assertEqual(self.app.access_view.mode,'LOGIN')

    def test_fault_during_unlock_closes_resources(self):
        self.assertTrue(hasattr(self.app,'accounts'),'Conta ausente')
        self.app.accounts.create('bar','12345678','007');session=self.app.accounts.login('bar','12345678')
        with patch('salva_ai_v2.ui.sales.SalesView',side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):self.app.unlock(session)
        self.assertIsNone(self.app.db.conn)
        reopened=build_application(self.root);reopened.close()

    def test_access_constructor_fault_still_closes(self):
        from unittest.mock import PropertyMock
        from salva_ai_v2.security.accounts import AccountService
        with patch.object(AccountService,'mode',new_callable=PropertyMock,side_effect=RuntimeError('falha de entrada')):
            with self.assertRaises(RuntimeError):self.app.require_login()
        try:self.app.close()
        except Exception as error:self.fail(f'Fechamento de entrada parcial falhou: {error}')
        self.assertIsNone(self.app.db.conn)

    def test_recovery_defines_username_and_password_without_old_login(self):
        self.app.accounts.create('usuario errado','Senha esquecida 42','007')
        self.app.accounts.reenroll_with_email(self.h.proof(),'usuario errado','Senha esquecida 42','007');self.h.advance(61)
        self.app.require_login();self.app.access_view.set_mode('RECOVERY');w=self.app.access_view.wizard;self.confirm_email(w)
        self.fill(w,username=' Novo Bar ',password='  senha nova 42 ',password_confirm='diferente')
        self.assertFalse(w.submit());self.assertEqual(w.inputs['username'].get(),' Novo Bar ')
        self.fill(w,password_confirm='  senha nova 42 ');self.assertTrue(w.submit())
        view=self.app.access_view;self.assertEqual(view.mode,'LOGIN');self.assertEqual(view.inputs['password'].get(),'')
        self.fill(view,password='  senha nova 42 ');self.assertTrue(view.submit())
        self.assertIn('SALVA AI HEADSHOP',self.app.window.title())
