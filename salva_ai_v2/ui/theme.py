import sys
from tkinter import ttk,font


def configure_theme(root):
    family='Segoe UI' if sys.platform=='win32' else font.nametofont('TkDefaultFont').actual('family')
    style=ttk.Style(root)
    if 'clam' in style.theme_names():style.theme_use('clam')
    style.configure('.',font=(family,10),foreground='#233c3e',background='#faf6eb')
    style.configure('TFrame',background='#faf6eb')
    style.configure('TLabel',background='#faf6eb')
    style.configure('TButton',padding=(10,7),background='#ffffff',borderwidth=1)
    style.map('TButton',background=[('active','#e7eeeb')],foreground=[('disabled','#657370')])
    style.configure('Primary.TButton',background='#225c48',foreground='#ffffff',padding=(14,9))
    style.map('Primary.TButton',background=[('active','#194735'),('disabled','#d4ded8')],foreground=[('disabled','#52665a')])
    style.configure('Danger.TButton',foreground='#a52525')
    style.configure('Title.TLabel',font=(family,18,'bold'))
    style.configure('Brand.TLabel',font=(family,18,'bold'))
    style.configure('Muted.TLabel',foreground='#52635e')
    style.configure('Nav.TButton',anchor='w',padding=(12,7),borderwidth=0,background='#ffffff')
    style.configure('Selected.Nav.TButton',background='#e2eee7',foreground='#194735')
    style.map('Selected.Nav.TButton',background=[('active','#d9e9df')])
    style.configure('Sidebar.TFrame',background='#ffffff')
    style.configure('Sidebar.TLabel',background='#ffffff',foreground='#52635e',font=(family,10,'bold'))
    style.configure('Treeview',font=(family,10),rowheight=30,background='#ffffff',fieldbackground='#ffffff',borderwidth=1)
    style.configure('Treeview.Heading',font=(family,10,'bold'),padding=(8,7),background='#eaf0ed')
    style.map('Treeview',background=[('selected','#d8e9df')],foreground=[('selected','#173f2d')])
    return style
