import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from uuid import uuid4
from ..common.errors import BusinessError
from ..common.money import parse_money, money


def command():
    return str(uuid4())


class FieldsDialog(simpledialog.Dialog):
    def __init__(self, parent, title, fields):
        self.fields, self.inputs = fields, {}
        super().__init__(parent,title)

    def body(self, master):
        for row,(key,label,value) in enumerate(self.fields):
            ttk.Label(master,text=label).grid(row=row,column=0,sticky="w",padx=8,pady=5)
            entry = ttk.Entry(master,width=38)
            entry.insert(0,str(value))
            entry.grid(row=row,column=1,sticky="ew",padx=8,pady=5)
            self.inputs[key]=entry
        return next(iter(self.inputs.values()),None)

    def apply(self):
        self.result={key:entry.get().strip() for key,entry in self.inputs.items()}


def ask_fields(parent,title,fields):
    return FieldsDialog(parent,title,fields).result


def table(parent, columns, height=12):
    container=ttk.Frame(parent)
    container.pack(fill="both",expand=True,pady=(8,4))
    tree=ttk.Treeview(container,columns=columns,show="headings",height=height,selectmode="browse")
    y=ttk.Scrollbar(container,orient="vertical",command=tree.yview)
    x=ttk.Scrollbar(container,orient="horizontal",command=tree.xview)
    tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
    tree.grid(row=0,column=0,sticky="nsew")
    y.grid(row=0,column=1,sticky="ns")
    x.grid(row=1,column=0,sticky="ew")
    container.rowconfigure(0,weight=1);container.columnconfigure(0,weight=1)
    for name in columns:
        tree.heading(name,text=name)
        tree.column(name,width=110,minwidth=70,anchor="w" if name in ("Produto","Cliente","Descrição","Situação") else "e")
    return tree


def fill(tree, rows):
    selected=tree.selection()
    tree.delete(*tree.get_children())
    for id,values in rows:
        tree.insert("", "end", iid=str(id), values=values)
    if selected and tree.exists(selected[0]):
        tree.selection_set(selected[0])


class View(ttk.Frame):
    def __init__(self,parent,services):
        super().__init__(parent,padding=12)
        self.s=services

    def act(self,func):
        try:
            value=func()
            self.s.application.refresh()
            return value
        except (BusinessError,ValueError) as error:
            messagebox.showerror("Não foi possível concluir",str(error),parent=self)

    def selected(self,tree):
        rows=tree.selection()
        if not rows:
            raise BusinessError("Selecione um registro na lista.")
        return int(rows[0])

    def grant(self,action):
        grant=self.s.application.admin.request(action)
        if grant is None:
            raise BusinessError("Operação cancelada.")
        return grant

    def reason(self):
        reason=simpledialog.askstring("Motivo","Descreva o motivo (mínimo cinco caracteres):",parent=self)
        if reason is None:
            raise BusinessError("Operação cancelada.")
        return reason

    def refresh(self):
        pass


class ProductPicker:
    def build_picker(self,parent,add_callback):
        row=ttk.Frame(parent)
        row.pack(fill="x",pady=6)
        ttk.Label(row,text="Produto").pack(side="left")
        self.search=tk.StringVar()
        self.picker=ttk.Combobox(row,textvariable=self.search,width=43)
        self.picker.pack(side="left",padx=8)
        self.picker.bind("<KeyRelease>",lambda event:self.filter_products())
        ttk.Label(row,text="Quantidade").pack(side="left")
        self.qty=ttk.Entry(row,width=6)
        self.qty.insert(0,"1")
        self.qty.pack(side="left",padx=8)
        ttk.Button(row,text="Adicionar",command=lambda:self.act(add_callback)).pack(side="left")
        self.qty.bind("<Return>",lambda event:self.act(add_callback))
        self.products_map={}

    def filter_products(self):
        from ..inventory.queries import search_products
        products=search_products(self.s.inventory.products(),self.search.get())
        self.products_map={f'{p["id"]:03d} — {p["name"]}':p["id"] for p in products}
        self.picker.configure(values=list(self.products_map))

    def selected_product(self):
        value=self.search.get()
        if value in self.products_map:
            return self.products_map[value]
        from ..inventory.queries import search_products
        matches=search_products(self.s.inventory.products(),value)
        if len(matches)!=1:
            raise BusinessError("Escolha um produto na lista.")
        return matches[0]["id"]

    def select_shortcut(self,key):
        row=self.s.inventory.shortcut(key)
        if row:
            self.search.set(f'{row["id"]:03d} — {row["name"]}')
            self.products_map[self.search.get()]=row["id"]
            self.qty.focus_set()

