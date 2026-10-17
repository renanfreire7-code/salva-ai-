import tkinter as tk
import sqlite3
from decimal import InvalidOperation
from tkinter import ttk, simpledialog, messagebox
from uuid import uuid4
from ..common.errors import BusinessError
from ..common.money import parse_money, money
from .forms import FormDialog,FieldSpec,ask_fields


def command():
    return str(uuid4())


FieldsDialog=FormDialog


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
        except (BusinessError,ValueError,OSError,sqlite3.Error,InvalidOperation) as error:
            messagebox.showerror("Não foi possível concluir",str(error),parent=self)
            self.s.application.refresh()

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
        self._add_callback=add_callback
        row=ttk.Frame(parent)
        row.pack(fill="x",pady=6)
        ttk.Label(row,text="Produto").pack(side="left")
        self.search=tk.StringVar()
        self.picker=ttk.Combobox(row,textvariable=self.search,width=43)
        self.picker.pack(side="left",padx=8)
        self.picker.bind("<KeyRelease>",lambda event:self.filter_products() if event.keysym not in ('Up','Down','Return','KP_Enter') and not event.keysym.startswith('F') else None)
        self.picker.bind('<Return>',lambda event:self.choose_product())
        self.picker.bind('<Down>',lambda event:self.move_product(1))
        self.picker.bind('<Up>',lambda event:self.move_product(-1))
        ttk.Label(row,text="Quantidade").pack(side="left")
        self.qty=ttk.Entry(row,width=6)
        self.qty.insert(0,"1")
        self.qty.pack(side="left",padx=8)
        ttk.Button(row,text="Adicionar",command=lambda:self.act(self.add_and_focus)).pack(side="left")
        self.qty.bind("<Return>",lambda event:self.add_key())
        self.products_map={}
        self.picker_notice=tk.StringVar()
        ttk.Label(parent,textvariable=self.picker_notice,foreground='#a52525').pack(anchor='w')

    def choose_product(self):
        from ..inventory.queries import product_label
        try:
            pid=self.selected_product()
        except BusinessError as error:
            self.picker_notice.set(str(error));return 'break'
        product=next(p for p in self.s.inventory.products() if p['id']==pid)
        label=product_label(product);self.products_map[label]=pid;self.search.set(label)
        self.picker_notice.set('');self.qty.focus_set()
        return 'break'

    def move_product(self,delta):
        values=list(self.picker['values'])
        if values:
            index=self.picker.current()
            self.picker.current(max(0,min(len(values)-1,index+delta)))
        return 'break'

    def add_and_focus(self):
        self._add_callback()
        self.search.set('');self.qty.delete(0,'end');self.qty.insert(0,'1')
        self.filter_products();self.picker_notice.set('');self.picker.focus_set()

    def add_key(self):
        self.act(self.add_and_focus);return 'break'

    def filter_products(self):
        from ..inventory.queries import search_products,product_label
        products=search_products(self.s.inventory.products(),self.search.get())
        self.products_map={product_label(p):p["id"] for p in products}
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
        from ..inventory.queries import product_label
        row=self.s.inventory.shortcut(key)
        if row:
            self.search.set(product_label(row))
            self.products_map[self.search.get()]=row["id"]
            self.qty.focus_set()
            self.picker_notice.set('')
        else:
            self.picker_notice.set(f'F{key} não tem produto associado. Configure em Produtos e estoque.')
