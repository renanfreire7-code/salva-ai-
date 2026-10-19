"""Contrato atual: abertura direta, dados preservados e PIN administrativo."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.common.db import Database
from salva_ai_v2.common.errors import BusinessError
from salva_ai_v2.security.accounts import AccountService
from salva_ai_v2.security.service import SecurityService


class DirectAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def open(self):
        app=build_application(self.root);self.addCleanup(app.close);return app

    def test_first_start_opens_all_operations_without_credentials_or_email(self):
        (self.root/'auth_service.json').write_text('invalid and deliberately unused')
        app=self.open()
        self.assertTrue(app.authenticated);self.assertEqual(len(app.views),11)
        self.assertIs(app.shell.selected_view,app.sales_view)
        self.assertFalse(hasattr(app,'access_view'));self.assertFalse(hasattr(app,'emails'));self.assertFalse(hasattr(app,'network_runner'))
        self.assertEqual(app.db.conn.execute('SELECT count(*) FROM establishment_account').fetchone()[0],0)
        self.assertFalse(app.security.configured);self.assertIn('SALVA AI HEADSHOP',app.window.title())
        self.assertTrue(app.delivery_view.motorcycle_label['image'])

    def test_forgotten_and_blocked_account_and_pin_are_preserved(self):
        db=Database(self.root/'dados'/'salva_ai.sqlite3');db.migrate();security=SecurityService(db)
        AccountService(db,security).create('forgotten','fixture-password','007')
        db.conn.execute('UPDATE establishment_account SET failures=99,blocked_until=9999999999')
        before=tuple(db.conn.execute('SELECT * FROM establishment_account').fetchone())
        credentials=tuple(db.conn.execute('SELECT * FROM admin_credentials').fetchone());db.close()
        app=self.open();self.assertEqual(len(app.views),11)
        self.assertEqual(before,tuple(app.db.conn.execute('SELECT * FROM establishment_account').fetchone()))
        self.assertEqual(credentials,tuple(app.db.conn.execute('SELECT * FROM admin_credentials').fetchone()))
        with self.assertRaises(BusinessError):app.security.authorize('008','stock.adjust')
        app.security.authorize('007','stock.adjust')

    def test_restore_rebuilds_operations_without_login_and_invalidates_grants(self):
        app=self.open();app.security.setup('007')
        p=app.services.inventory.create_product('Produto preservado',500,1,0,'product')
        backup=app.services.backups.create('manual','backup').path
        app.services.inventory.create_product('Depois do backup',900,1,0,'later')
        old=app.sales_view;grant=app.security.authorize('007','product.edit')
        restore=app.services.restore;preview=restore.prepare(backup,app.security.authorize('007','backup.restore'));restore.apply(preview,True)
        self.assertTrue(app.authenticated);self.assertEqual(len(app.views),11);self.assertIsNot(old,app.sales_view)
        self.assertFalse(old.winfo_exists());self.assertFalse(hasattr(app,'access_view'))
        self.assertEqual([r['id'] for r in app.services.inventory.products()],[p])
        with self.assertRaises(BusinessError):app.security.validate(grant,'product.edit')

    def test_new_install_creates_pin_only_when_admin_operation_is_requested(self):
        app=self.open();self.assertFalse(app.security.configured)
        with patch('salva_ai_v2.ui.dialogs.simpledialog.askstring',side_effect=['007','007','007']),patch('salva_ai_v2.ui.dialogs.messagebox.showinfo'),patch('salva_ai_v2.ui.dialogs.messagebox.showerror'):
            grant=app.admin.request('stock.adjust')
        self.assertIsNotNone(grant);app.security.validate(grant,'stock.adjust')
        self.assertEqual(app.db.conn.execute('SELECT count(*) FROM establishment_account').fetchone()[0],0)

    def test_default_data_directory_is_unchanged(self):
        with patch('salva_ai_v2.bootstrap.Path.home',return_value=self.root):app=build_application()
        try:self.assertEqual(app.data_dir,self.root/'SalvaAiHeadshopV2');self.assertTrue(app.authenticated)
        finally:app.close()
