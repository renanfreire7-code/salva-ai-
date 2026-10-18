from pathlib import Path
import tempfile,unittest
from salva_ai_v2.bootstrap import build_application
from tests_v2.email_support import EmailHarness
from tests_v2.support import FakeClock
from tests_v2.test_email_provider import EMAIL,session,user

class EmailAccessUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=build_application(Path(self.tmp.name));self.addCleanup(self.app.close)
        self.h=EmailHarness(self.app.db,FakeClock());self.app.emails=self.h.flow;self.app.accounts.emails=self.h.flow
        self.app.require_login()

    def fill(self,view,**fields):
        for name,value in fields.items():view.inputs[name].delete(0,'end');view.inputs[name].insert(0,value)

    def confirm_email(self,wizard):
        self.fill(wizard,email=EMAIL);self.h.transport.responses.append((200,{},{}));wizard.submit();self.h.runner.run_next()
        self.fill(wizard,code='654321');self.h.transport.responses.extend([(200,{},session()),(200,{},user())]);wizard.submit();self.h.runner.run_next()

    def test_setup_cancel_leaves_no_partial_account(self):
        wizard=self.app.access_view.wizard;self.confirm_email(wizard)
        self.assertFalse(self.app.accounts.configured);wizard.cancel()
        reopened=build_application(Path(self.tmp.name))
        try:self.assertFalse(reopened.security.configured);self.assertFalse(reopened.accounts.configured)
        finally:reopened.close()

    def test_reenroll_wizard_retains_fields_and_never_unlocks_early(self):
        self.app.accounts.create('old','old-password','007');self.app.require_login()
        self.app.access_view.set_mode('ENROLL');w=self.app.access_view.wizard;self.confirm_email(w)
        self.fill(w,username='new',password='new-password',password_confirm='new-password',pin='008')
        self.assertFalse(w.submit());self.assertEqual(w.inputs['username'].get(),'new');self.assertFalse(self.app.authenticated)
        self.fill(w,pin='007');self.assertTrue(w.submit())
        self.assertFalse(self.app.authenticated);self.assertEqual(self.app.access_view.inputs['username'].get(),'new')
        self.assertEqual(self.app.access_view.inputs['password'].get(),'')

    def test_email_recovery_does_not_request_old_username_key_or_pin(self):
        self.app.accounts.create('old','old-password','007')
        self.app.accounts.reenroll_with_email(self.h.proof(),'old','old-password','007');self.h.advance(61)
        self.app.require_login();self.app.access_view.set_mode('RECOVERY');w=self.app.access_view.wizard
        self.confirm_email(w);self.assertEqual(set(w.inputs),{'username','password','password_confirm'})
        self.fill(w,username='new',password='new-password',password_confirm='new-password');self.assertTrue(w.submit())
        self.app.accounts.login('new','new-password');self.app.security.authorize('007','fixture')

    def test_navigation_and_close_drop_delayed_callbacks(self):
        w=self.app.access_view.wizard;self.fill(w,email=EMAIL);self.h.transport.responses.append((200,{},{}));w.submit()
        self.app.require_login();self.h.runner.run_next();self.assertFalse(self.app.accounts.configured)
        self.assertEqual(self.app.access_view.wizard.stage,'EMAIL')
        self.h.advance(61);w=self.app.access_view.wizard;self.fill(w,email=EMAIL);self.h.transport.responses.append((200,{},{}));w.submit()
        self.app.close();self.h.runner.run_next();self.assertIsNone(self.app.db.conn)

    def test_legacy_login_without_configuration_or_network(self):
        self.app.accounts.create('old','old-password','007');self.app.emails.client=None;self.app.require_login()
        view=self.app.access_view;self.fill(view,username='old',password='old-password');self.assertTrue(view.submit())
        self.app.require_login();self.app.access_view.set_mode('RECOVERY');w=self.app.access_view.wizard
        self.fill(w,email=EMAIL);self.assertFalse(w.submit());self.assertFalse(self.app.authenticated)
        self.assertIn('Configure',w.error.get());self.assertEqual(self.h.transport.calls,[])

    def test_controls_fit_with_error_at1260x680(self):
        for geometry in ('1260x680','1366x768'):
            self.app.window.geometry(geometry)
            w=self.app.access_view.wizard;w.error.set('Falha de conexão. Confira a internet e tente novamente.');self.app.window.update()
            for control in [*w.inputs.values(),w.primary_button,w.back_button]:
                self.assertTrue(control.winfo_ismapped())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),self.app.window.winfo_rooty()+self.app.window.winfo_height())
