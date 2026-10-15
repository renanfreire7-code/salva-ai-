import unittest
from pathlib import Path
from unittest import mock

try:
    import tkinter  # noqa: F401
    HAS_TK = True
except ImportError:
    HAS_TK = False


@unittest.skipUnless(HAS_TK, 'tkinter indisponível neste Python')
class OpenFolderTest(unittest.TestCase):
    """Bug: 'Abrir pasta de backups' usava os.startfile, que só existe no Windows."""

    def setUp(self):
        import app
        self.app = app
        self.folder = Path('/tmp/backups')

    def test_windows_uses_startfile(self):
        with mock.patch.object(self.app.sys, 'platform', 'win32'), \
             mock.patch.object(self.app.os, 'startfile', create=True) as startfile:
            self.app.open_folder(self.folder)
        startfile.assert_called_once_with(str(self.folder))

    def test_macos_uses_open(self):
        with mock.patch.object(self.app.sys, 'platform', 'darwin'), \
             mock.patch.object(self.app.subprocess, 'run') as run:
            self.app.open_folder(self.folder)
        run.assert_called_once_with(['open', str(self.folder)], check=True)

    def test_linux_uses_xdg_open(self):
        with mock.patch.object(self.app.sys, 'platform', 'linux'), \
             mock.patch.object(self.app.subprocess, 'run') as run:
            self.app.open_folder(self.folder)
        run.assert_called_once_with(['xdg-open', str(self.folder)], check=True)

    def test_importing_app_does_not_open_the_database(self):
        """Importar app.py não deve criar/abrir o banco em ~/SalvaAiHeadshop."""
        self.assertIsNone(self.app.STORE)



@unittest.skipUnless(HAS_TK, 'tkinter indisponível neste Python')
class AppSmokeTest(unittest.TestCase):
    """Monta a janela real com um banco temporário e exercita os fluxos principais."""

    def setUp(self):
        import tempfile
        import tkinter
        import app
        import finance
        from core import Store
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name) / 'SalvaAiHeadshop'
        self._patches = [mock.patch.object(app, 'ROOT', root)]
        for p in self._patches:
            p.start()
        app.STORE = Store(root / 'dados' / 'bar.sqlite3')
        finance.migrate(app.STORE)
        self.store = app.STORE
        self.store.add_product('Seda', '5,00', 10)
        self.store.adjust_stock(self.store.products()[0]['id'], 1, 'Caixa/Fardo (entrada)', '')
        try:
            self.ui = app.App()
        except tkinter.TclError as e:  # sem display (CI headless)
            self.skipTest(f'sem display: {e}')
        self.ui.withdraw()
        self.app = app

    def tearDown(self):
        if hasattr(self, 'ui'):
            self.ui.quit_app()
        else:
            self.store.close()
        self.app.STORE = None
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def test_every_tab_renders(self):
        for i in range(self.ui.tabs.index('end')):
            self.ui.tabs.select(i)
            self.ui.update()

    def test_cash_buttons_follow_cash_state(self):
        self.assertIn('disabled', self.ui.close_cash_btn.state())
        self.assertNotIn('disabled', self.ui.open_cash_btn.state())
        self.assertIn('fechado', self.ui.header_cash.cget('text'))
        self.ui.open_cash()
        self.assertIn('disabled', self.ui.open_cash_btn.state())
        self.assertNotIn('disabled', self.ui.close_cash_btn.state())
        self.assertIn('aberto', self.ui.header_cash.cget('text'))
        self.assertIn('Caixa aberto', self.ui.status_var.get())

    def test_return_opens_tab_selects_it_and_reports_status(self):
        self.assertTrue(self.ui.customer.bind('<Return>'), 'Return deve abrir a comanda')
        self.ui.customer.insert(0, 'Marina')
        self.ui.open_tab()
        tid = self.store.open_tabs()[0]['id']
        self.assertEqual(self.ui.tabs_tree.selection(), (str(tid),))
        self.assertEqual(self.ui.customer.get(), '')
        self.assertIn(f'Comanda nº {tid} aberta', self.ui.status_var.get())

    def test_numeric_columns_are_right_aligned(self):
        self.assertEqual(str(self.ui.products_tree.column('Preço', 'anchor')), 'e')
        self.assertEqual(str(self.ui.products_tree.column('Produto', 'anchor')), 'w')

    def test_errors_do_not_update_status(self):
        with mock.patch.object(self.app.messagebox, 'showerror') as showerror:
            self.ui.add_to_tab()  # nenhuma comanda selecionada
        showerror.assert_called_once()
        self.assertEqual(self.ui.status_var.get(), 'Pronto.')


if __name__ == '__main__':
    unittest.main()
