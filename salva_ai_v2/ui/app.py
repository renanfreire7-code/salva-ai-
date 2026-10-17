import tkinter as tk
from tkinter import ttk
from .theme import configure_theme
from .branding import APP_NAME,STORE_NAME,load_icon,load_store_logo


class MainWindow(tk.Tk):
    def __init__(self, close_callback):
        super().__init__()
        self.title(APP_NAME+" | Gestão do bar")
        self.geometry("1260x700")
        self.minsize(1040,620)
        self.protocol("WM_DELETE_WINDOW", close_callback)
        self.configure(background='#faf6eb')
        self.style=configure_theme(self)
        header = ttk.Frame(self, padding=(20,8))
        header.pack(fill="x")
        self.brand_label=ttk.Label(header,text=APP_NAME,style='Brand.TLabel')
        self.brand_label.pack(side='left')
        ttk.Label(header,text='Gestão do bar · Offline',style='Muted.TLabel').pack(side='left',padx=16)
        self.brand_logo=load_icon(self,56)
        self.iconphoto(True,self.brand_logo)
        self.logo_label=ttk.Label(header,image=self.brand_logo);self.logo_label.pack(side='right')
        self.cash_state=tk.StringVar(value='Caixa fechado')
        ttk.Label(header,textvariable=self.cash_state).pack(side='right',padx=18)
        self.status = tk.StringVar(value="Ambiente novo. Configure seu acesso para começar.")
        ttk.Label(self, textvariable=self.status, padding=(18, 8), wraplength=1100).pack(side="bottom", fill="x")
        self.body = ttk.Frame(self, padding=(8,4))
        self.body.pack(fill="both", expand=True)

    def show_identity(self,establishment=False):
        name=STORE_NAME if establishment else APP_NAME
        self.title(name+" | Gestão do bar")
        self.brand_label.configure(text=name)
        self.brand_logo=load_store_logo(self,64) if establishment else load_icon(self,56)
        self.logo_label.configure(image=self.brand_logo)
        self.iconphoto(True,self.brand_logo)
