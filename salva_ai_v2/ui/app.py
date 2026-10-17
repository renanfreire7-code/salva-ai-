import tkinter as tk
import sys
from tkinter import font
from tkinter import ttk


class MainWindow(tk.Tk):
    def __init__(self, close_callback):
        super().__init__()
        self.title("Salva AI • Gestão do bar")
        self.geometry("1180x700")
        self.minsize(960, 620)
        self.protocol("WM_DELETE_WINDOW", close_callback)
        self.configure(background="#f4f5f7")
        family='Segoe UI' if sys.platform=='win32' else font.nametofont('TkDefaultFont').actual('family')
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", font=(family, 10), foreground="#172b3a", background="#f4f5f7")
        style.configure("TButton", padding=(10, 7))
        style.configure("Treeview", rowheight=28, background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=(family, 10, "bold"))
        style.configure("Title.TLabel", font=(family, 19, "bold"))
        header = ttk.Frame(self, padding=(18, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Salva AI", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Gestão do bar | offline").pack(side="left", padx=18)
        self.status = tk.StringVar(value="Ambiente novo. Configure seu acesso para começar.")
        ttk.Label(self, textvariable=self.status, padding=(18, 8), wraplength=1100).pack(side="bottom", fill="x")
        self.body = ttk.Frame(self, padding=(16, 4))
        self.body.pack(fill="both", expand=True)
        self.placeholder = ttk.Label(self.body, text="Seu novo espaço de trabalho", style="Title.TLabel")
        self.placeholder.pack(anchor="w", pady=18)
        ttk.Label(self.body, text="Os módulos serão disponibilizados conforme forem implementados e verificados.").pack(anchor="w")
