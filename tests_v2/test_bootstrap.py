import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path('salva_ai_v2/bootstrap.py').exists(), 'Inicialização ainda não implementada')
        from salva_ai_v2.bootstrap import build_application
        self.build = build_application
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_empty_separate_database_and_reopen(self):
        legacy = self.root / 'SalvaAiHeadshop'
        legacy.mkdir()
        (legacy / 'original.txt').write_text('preservado')
        app = self.build(self.root / 'novo')
        self.assertEqual(app.data_dir, self.root / 'novo')
        self.assertFalse(app.security.configured)
        app.security.setup('681942')
        app.close()
        app = self.build(self.root / 'novo')
        self.addCleanup(app.close)
        self.assertTrue(app.security.configured)
        self.assertEqual((legacy / 'original.txt').read_text(), 'preservado')
        self.assertEqual(len(list(legacy.iterdir())), 1)

    def test_cancel_initial_setup_closes_connection(self):
        app = self.build(self.root / 'novo')
        with patch.object(app.admin, 'setup', return_value=False):
            app.run()
        self.assertIsNone(app.db.conn)

    def test_window_fits_and_close_is_idempotent(self):
        app = self.build(self.root / 'novo')
        app.window.update()
        self.assertLessEqual(app.window.winfo_height(), 720)
        app.close()
        app.close()
