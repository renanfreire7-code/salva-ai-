import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest


class LayoutTest(unittest.TestCase):
    def test_primary_actions_fit_1366_by_768(self):
        from tests_v2.application_support import build_test_application as build_application
        with tempfile.TemporaryDirectory() as directory:
            app=build_application(Path(directory))
            try:
                app.window.geometry('1260x680')
                app.window.update()
                for view in app.views:
                    app.show_view(view)
                    app.window.update()
                    for widget in view.winfo_children():
                        if isinstance(widget,ttk.Frame):
                            for button in widget.winfo_children():
                                if isinstance(button,ttk.Button):
                                    self.assertTrue(button.winfo_ismapped(),button.cget('text'))
                                    self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),app.window.winfo_rootx()+app.window.winfo_width(),button.cget('text'))
                                    self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),app.window.winfo_rooty()+app.window.winfo_height(),button.cget('text'))
            finally:
                app.close()

    def test_nested_visible_buttons_and_inputs_fit_available_window(self):
        from tests_v2.application_support import build_test_application as build_application
        from salva_ai_v2.ui.forms import FormDialog
        from unittest.mock import patch
        def check(widget,root):
            for child in widget.winfo_children():
                if child.winfo_ismapped() and isinstance(child,(ttk.Button,ttk.Entry,ttk.Combobox)):
                    label=str(child.cget('text')) if isinstance(child,ttk.Button) else str(child)
                    self.assertLessEqual(child.winfo_rootx()+child.winfo_width(),root.winfo_rootx()+root.winfo_width(),label)
                    self.assertLessEqual(child.winfo_rooty()+child.winfo_height(),root.winfo_rooty()+root.winfo_height(),label)
                    self.assertGreaterEqual(child.winfo_rooty(),root.winfo_rooty(),label)
                check(child,root)
        with tempfile.TemporaryDirectory() as directory:
            app=build_application(Path(directory))
            try:
                app.window.geometry('1260x680');app.window.update()
                for view in app.views:
                    app.show_view(view);app.window.update();check(view,app.window)
                editor=app.delivery_view.create();app.window.update();check(editor,editor.winfo_toplevel());editor.winfo_toplevel().destroy()
                dialogs=[]
                with patch('salva_ai_v2.ui.products.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):app.products_view.create()
                dialog=dialogs[0];app.window.update();check(dialog,dialog)
                self.assertLessEqual(dialog.winfo_height(),680);dialog.destroy()
            finally:app.close()
