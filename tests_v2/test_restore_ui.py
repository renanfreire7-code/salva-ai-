"""Restauração pelo botão real, com reconstrução de interface e dados isolados."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

from salva_ai_v2.bootstrap import build_application


class RestoreUITest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = build_application(self.root)
        self.addCleanup(self.app.close)
        self.app.security.setup('681')
        self.app.services.inventory.create_product('Antes do backup', 500, 1, 0, 'before')
        self.backup = self.app.services.backups.create('manual', 'snapshot').path
        self.app.services.inventory.create_product('Depois do backup', 900, 1, 0, 'after')
        self.audit = self.app.history_view.open_audit()
        self.audit.backup_center()
        self.window = next(widget for widget in self.audit.winfo_children()
                           if isinstance(widget, tk.Toplevel))
        self.errors = []
        self.app.window.report_callback_exception = lambda *error: self.errors.append(error)

    def restore_button(self):
        def search(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button) and child.cget('text') == 'Restaurar arquivo':
                    return child
                found = search(child)
                if found is not None:
                    return found
        return search(self.window)

    def restore(self, confirmed, showinfo):
        with patch('tkinter.filedialog.askopenfilename', return_value=str(self.backup)), \
             patch.object(self.app.admin, 'request', side_effect=lambda action: self.app.security.authorize('681', action)), \
             patch('salva_ai_v2.ui.audit.messagebox.askyesno', return_value=confirmed), \
             patch('salva_ai_v2.ui.audit.messagebox.showinfo', side_effect=showinfo):
            self.restore_button().invoke()

    def test_restore_shows_confirmation_with_live_parent_then_closes_and_releases_data(self):
        messages = []
        def showinfo(title, message, *, parent):
            self.assertTrue(parent.winfo_exists(), 'A confirmação usa uma janela destruída')
            messages.append((title, message))
        self.restore(True, showinfo)
        self.assertEqual(self.errors, [], self.errors)
        self.assertEqual(len(messages), 1)
        self.assertTrue(self.app._closed)
        self.assertIsNone(self.app.db.conn)
        reopened = build_application(self.root)
        self.addCleanup(reopened.close)
        self.assertFalse(hasattr(reopened, 'access_view'))
        self.assertEqual([row['name'] for row in reopened.services.inventory.products()], ['Antes do backup'])
        self.assertTrue(list((self.root/'backups').glob('antes_restauracao_*.sqlite3')))
        reopened.security.authorize('681', 'backup.restore')

    def test_cancel_keeps_current_data_and_backup_window_open(self):
        self.restore(False, lambda *args, **kwargs: self.fail('Cancelamento não deve confirmar restauração'))
        self.assertEqual(self.errors, [])
        self.assertFalse(self.app._closed)
        self.assertTrue(self.window.winfo_exists())
        self.assertEqual(len(self.app.services.inventory.products()), 2)
        self.assertFalse(list((self.root/'backups').glob('antes_restauracao_*.sqlite3')))

    def test_failed_replacement_reports_error_on_live_window_and_keeps_original_data(self):
        messages = []
        def showerror(title, message, *, parent):
            self.assertTrue(parent.winfo_exists(), 'O erro usa uma janela destruída')
            messages.append(message)
        with patch('salva_ai_v2.maintenance.restore.promote', side_effect=OSError('disco bloqueado')), \
             patch('salva_ai_v2.ui.shared.messagebox.showerror', side_effect=showerror):
            self.restore(True, lambda *args, **kwargs: self.fail('Falha não deve informar sucesso'))
        self.assertEqual(self.errors, [], self.errors)
        self.assertEqual(messages, ['disco bloqueado'])
        self.assertFalse(self.app._closed)
        self.assertEqual(len(self.app.services.inventory.products()), 2)
        self.app.close()
        reopened = build_application(self.root)
        self.addCleanup(reopened.close)
        self.assertEqual(len(reopened.services.inventory.products()), 2)

    def test_confirmation_failure_still_closes_after_successful_replacement(self):
        def unavailable_dialog(*args, **kwargs):
            raise tk.TclError('Janela indisponível')
        self.restore(True, unavailable_dialog)
        self.assertEqual(len(self.errors), 1)
        self.assertIs(self.errors[0][0], tk.TclError)
        self.assertTrue(self.app._closed)
        self.assertIsNone(self.app.db.conn)
        reopened = build_application(self.root)
        self.addCleanup(reopened.close)
        self.assertEqual(len(reopened.services.inventory.products()), 1)
