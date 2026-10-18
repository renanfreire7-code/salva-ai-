from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from salva_ai_v2.bootstrap import build_application


class BrandingTest(unittest.TestCase):
    def test_traditional_branding_assets_local_and_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            app=build_application(Path(folder))
            try:
                self.assertIn('Bar Simples',app.window.title())
                from salva_ai_v2.ui.branding import load_logo,load_icon
                for load,size in [(load_logo,240),(load_icon,56)]:
                    im=load(app.window,size);self.assertLessEqual(im.width(),size);self.assertLessEqual(im.height(),size)
                self.assertTrue(app.access_view.logo_label['image'])
            finally:app.close()

    def test_identity_changes_with_authenticated_state(self):
        with tempfile.TemporaryDirectory() as folder:
            app=build_application(Path(folder))
            try:
                self.assertIn('Bar Simples',app.window.title())
                app.accounts.create('bar','Senha fictícia 42','007')
                app.unlock(app.accounts.login('bar','Senha fictícia 42'))
                self.assertIn('SALVA AI HEADSHOP',app.window.title())
                self.assertNotIn('Bar Simples',app.window.title())
                self.assertEqual(app.window.brand_label.cget('text'),'SALVA AI HEADSHOP')
                from salva_ai_v2.ui.branding import load_store_logo,load_icon
                expected=load_store_logo(app.window,64)
                actual=app.window.brand_logo
                self.assertEqual(actual.tk.call(str(actual),'data','-format','png'),expected.tk.call(str(expected),'data','-format','png'))
                self.assertLessEqual(max(actual.width(),actual.height()),64)
                self.assertTrue(app.delivery_view.motorcycle_label['image'])
                app.require_login()
                self.assertIn('Bar Simples',app.window.title())
                self.assertEqual(app.window.brand_label.cget('text'),'Bar Simples')
                expected=load_icon(app.window,56);actual=app.window.brand_logo
                self.assertEqual(actual.tk.call(str(actual),'data','-format','png'),expected.tk.call(str(expected),'data','-format','png'))
            finally:app.close()

    def test_access_fields_and_primary_action_fit_1366x768(self):
        with tempfile.TemporaryDirectory() as folder:
            app=build_application(Path(folder))
            try:
                app.window.geometry('1260x680');app.window.update()
                for mode in ['SETUP','RECOVERY','TRANSITION']:
                    if mode=='TRANSITION':
                        from tests_v2.security_support import seed_legacy_pin
                        seed_legacy_pin(app.db)
                    app.access_view.set_mode(mode);app.window.update()
                    def descendants(widget):
                        for child in widget.winfo_children():
                            yield child
                            yield from descendants(child)
                    from tkinter import ttk
                    w=app.access_view.wizard
                    controls=[*w.inputs.values(),w.primary_button]+[w for w in descendants(app.access_view.form) if isinstance(w,ttk.Button)]
                    for control in controls:
                        ancestor=control.master
                        while ancestor!=app.window:
                            self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),ancestor.winfo_rooty()+ancestor.winfo_height(),str(control))
                            ancestor=ancestor.master
                        self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),app.window.winfo_rooty()+app.window.winfo_height())
                        self.assertGreaterEqual(control.winfo_rootx(),app.window.winfo_rootx())
            finally:app.close()

    def test_demo_uses_setup_flow_without_real_store_data(self):
        from scripts.demo_v2 import main
        def run(app):
            self.assertFalse(app.accounts.configured)
            from tests_v2.email_support import EmailHarness
            from tests_v2.support import FakeClock
            from tests_v2.test_email_provider import EMAIL,session,user
            start=app.access_view.on_authenticated
            h=EmailHarness(app.db,FakeClock());app.emails=h.flow;app.accounts.emails=h.flow;app.require_login();app.access_view.on_authenticated=start
            view=app.access_view;w=view.wizard
            w.inputs['email'].insert(0,EMAIL);h.transport.responses.append((200,{},{}));w.submit();h.runner.run_next()
            w.inputs['code'].insert(0,'654321');h.transport.responses.extend([(200,{},session()),(200,{},user())]);w.submit();h.runner.run_next()
            for key,value in dict(username='bar',password='12345678',password_confirm='12345678',pin='007',pin_confirm='007').items():w.inputs[key].insert(0,value)
            with patch('salva_ai_v2.ui.email_access.messagebox.showinfo'):self.assertTrue(w.submit())
            view.inputs['password'].insert(0,'12345678');self.assertTrue(view.submit())
            self.assertEqual(len(app.services.inventory.products()),3)
            self.assertTrue(app.data_dir.name.startswith('salva_ai_v2_demo_'))
        with patch('salva_ai_v2.bootstrap.Application.run',run):main()
