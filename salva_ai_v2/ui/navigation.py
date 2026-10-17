from tkinter import ttk
from .assets import load_asset


class NavigationShell(ttk.Frame):
    def __init__(self,parent,groups=(),on_select=None):
        super().__init__(parent)
        self.pack(fill='both',expand=True)
        self.on_select=on_select;self.selected_view=None;self.buttons={}
        self.sidebar=ttk.Frame(self,style='Sidebar.TFrame',width=200,padding=(8,10))
        self.sidebar.pack(side='left',fill='y',padx=(0,8));self.sidebar.pack_propagate(False)
        self.content=ttk.Frame(self);self.content.pack(side='left',fill='both',expand=True)
        self.moto=load_asset(self,'motorcycle.png',18)
        self.set_groups(groups)

    def set_groups(self,groups):
        for widget in self.sidebar.winfo_children():widget.destroy()
        self.buttons={}
        for label,views in groups:
            ttk.Label(self.sidebar,text=label,style='Sidebar.TLabel').pack(anchor='w',padx=12,pady=(12,5))
            for title,view in views:
                options=dict(text=title,style='Nav.TButton',command=lambda v=view:self.show(v))
                if title=='Delivery':options.update(image=self.moto,compound='left')
                button=ttk.Button(self.sidebar,**options);button.pack(fill='x',pady=1)
                self.buttons[view]=button

    def show(self,view):
        if self.selected_view is not None:
            self.selected_view.pack_forget()
            self.buttons[self.selected_view].configure(style='Nav.TButton')
        view.pack(fill='both',expand=True)
        self.selected_view=view;self.buttons[view].configure(style='Selected.Nav.TButton')
        if self.on_select:self.on_select(view)
