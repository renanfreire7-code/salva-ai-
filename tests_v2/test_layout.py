import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest


class LayoutTest(unittest.TestCase):
    def test_primary_actions_fit_1366_by_768(self):
        from salva_ai_v2.bootstrap import build_application
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
