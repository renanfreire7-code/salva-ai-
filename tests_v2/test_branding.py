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
                    controls=[*app.access_view.inputs.values(),app.access_view.primary_button]+[w for w in descendants(app.access_view.form) if isinstance(w,ttk.Button)]
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
            view=app.access_view
            for key,value in dict(username='bar',password='12345678',password_confirm='12345678',pin='007',pin_confirm='007').items():view.inputs[key].insert(0,value)
            with patch('salva_ai_v2.ui.access.messagebox.showinfo'):self.assertTrue(view.submit())
            self.assertEqual(len(app.services.inventory.products()),3)
            self.assertTrue(app.data_dir.name.startswith('salva_ai_v2_demo_'))
        with patch('salva_ai_v2.bootstrap.Application.run',run):main()
