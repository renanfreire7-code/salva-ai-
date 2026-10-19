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
    if 'Produto' in columns:
        from .product_table import ProductTable
        result=ProductTable(parent,columns,height)
        result.pack(fill='both',expand=True,pady=(8,4))
        return result
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

    def act(self,func,*,error_parent=None):
        try:
            value=func()
            self.s.application.refresh()
            return value
        except (BusinessError,ValueError,OSError,sqlite3.Error,InvalidOperation) as error:
            messagebox.showerror("Não foi possível concluir",str(error),parent=error_parent if error_parent is not None else self)
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
        row=ttk.Frame(parent);row.pack(fill='x',pady=6);row.columnconfigure(1,weight=1)
        ttk.Label(row,text='Buscar produto · nome, código ou iniciais').grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,4))
        self.search=tk.StringVar()
        self.picker=ttk.Combobox(row,textvariable=self.search,width=24)
        self.picker.grid(row=1,column=0,columnspan=3,sticky='ew',pady=(0,6))
        self.picker.bind("<KeyRelease>",lambda event:self.filter_products() if event.keysym not in ('Up','Down','Return','KP_Enter') and not event.keysym.startswith('F') else None)
        self.picker.bind('<Return>',lambda event:self.choose_product())
        self.picker.bind('<Down>',lambda event:self.move_product(1))
        self.picker.bind('<Up>',lambda event:self.move_product(-1))
        ttk.Label(row,text="Quantidade").grid(row=2,column=0,sticky='w')
        self.qty=ttk.Entry(row,width=6)
        self.qty.insert(0,"1")
        self.qty.grid(row=2,column=1,sticky='w',padx=8)
        ttk.Button(row,text="Adicionar",command=lambda:self.act(self.add_and_focus)).grid(row=2,column=2,sticky='e')
        self.qty.bind("<Return>",lambda event:self.add_key())
        self.products_map={}
        self.picker_notice=tk.StringVar()
        ttk.Label(parent,textvariable=self.picker_notice,foreground='#a52525').pack(anchor='w')
        self.selected_name=tk.StringVar()
        selected_label=ttk.Label(parent,textvariable=self.selected_name,wraplength=400)
        self.selected_name_label=selected_label
        selected_label.pack(fill='x',anchor='w')
        selected_label.bind('<Configure>',lambda event:selected_label.configure(wraplength=max(80,event.width)))
        self.candidate_frame=ttk.Frame(parent)
        from .product_table import ProductTable
        self.candidates=ProductTable(self.candidate_frame,['Produto','Preço','Disponível'],height=3)
        self.candidates.pack(fill='both',expand=True)
        self.candidates.bind('<Double-1>',lambda event:self.choose_candidate())
        self.candidates.bind('<Return>',lambda event:self.choose_candidate())
        self.persistent_candidates=False

    def choose_product(self):
        from ..inventory.queries import product_label
        try:
            pid=self.selected_product()
        except BusinessError as error:
            self.picker_notice.set(str(error));return 'break'
        product=next(p for p in self.s.inventory.products() if p['id']==pid)
        label=product_label(product);self.products_map[label]=pid;self.search.set(label)
        self.selected_name.set(product['name'])
        if not self.persistent_candidates:self.candidate_frame.pack_forget()
        self.picker_notice.set('');self.qty.focus_set()
        return 'break'

    def choose_candidate(self):
        from ..inventory.queries import product_label
        selected=self.candidates.selection()
        if selected:
            product=next(p for p in self.s.inventory.products() if p['id']==int(selected[0]))
            self.search.set(product_label(product));self.products_map[self.search.get()]=product['id']
            return self.choose_product()
        return 'break'

    def move_product(self,delta):
        values=list(self.picker['values'])
        if values:
            index=self.picker.current()
            self.picker.current(max(0,min(len(values)-1,index+delta)))
            pid=self.products_map[self.picker.get()]
            self.candidates.selection_set(str(pid));self.candidates.see(str(pid))
        return 'break'

    def add_and_focus(self):
        self._add_callback()
        self.selected_name.set('')
        self.search.set('');self.qty.delete(0,'end');self.qty.insert(0,'1')
        self.filter_products();self.picker_notice.set('');self.picker.focus_set()

    def add_key(self):
        self.act(self.add_and_focus);return 'break'

    def filter_products(self):
        from ..inventory.queries import search_products,product_label
        products=search_products(self.s.inventory.products(),self.search.get())
        self.products_map={product_label(p):p["id"] for p in products}
        self.picker.configure(values=list(self.products_map))
        fill(self.candidates,[(p['id'],(p['name'],money(p['price_cents']),self.s.inventory.position(p['id']).available)) for p in products])
        if self.persistent_candidates or self.search.get().strip():
            self.candidate_frame.pack(after=self.selected_name_label,fill='both' if self.persistent_candidates else 'x',expand=self.persistent_candidates)
        else:self.candidate_frame.pack_forget()
        if hasattr(self,'product_tree') and self.product_tree is not self.candidates and hasattr(self,'render_product_candidates'):
            self.render_product_candidates(products)

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
            self.selected_name.set(row['name'])
            if not self.persistent_candidates:self.candidate_frame.pack_forget()
            self.qty.focus_set()
            self.picker_notice.set('')
        else:
            self.picker_notice.set(f'F{key} não tem produto associado. Configure em Produtos e estoque.')
