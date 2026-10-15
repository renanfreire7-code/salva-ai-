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


if __name__ == '__main__':
    unittest.main()
