import tkinter as tk
from tkinter import ttk
from .shared import View,table,fill
from .finance import date_input
from .order_details import OrderDetails,KINDS,STATES
from ..reporting.commerce_models import CommerceFilter
from ..common.money import money


class HistoryView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Histórico de vendas',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(self);row.pack(fill='x',pady=8)
        today=self.s.clock.today().strftime('%d/%m/%Y')
        self.start=tk.StringVar(value=today);self.end=tk.StringVar(value=today)
        self.kind=tk.StringVar(value='Todos');self.state=tk.StringVar(value='Todas');self.text=tk.StringVar()
        for label,var in (('De',self.start),('Até',self.end)):
            ttk.Label(row,text=label).pack(side='left');ttk.Entry(row,textvariable=var,width=11).pack(side='left',padx=6)
        ttk.Combobox(row,textvariable=self.kind,values=('Todos','Balcão','Comanda','Delivery'),width=12,state='readonly').pack(side='left',padx=6)
        ttk.Button(row,text='Consultar',command=lambda:self.act(self.refresh)).pack(side='left',padx=6)
        ttk.Button(row,text='Auditoria e manutenção',command=lambda:self.act(self.open_audit)).pack(side='right')
        row=ttk.Frame(self);row.pack(fill='x')
        ttk.Label(row,text='Número, cliente ou produto').pack(side='left')
        ttk.Entry(row,textvariable=self.text,width=28).pack(side='left',padx=8)
        ttk.Combobox(row,textvariable=self.state,values=('Todas',*STATES.values()),width=20,state='readonly').pack(side='left')
        ttk.Label(self,text='Balcão/comanda: data do recebimento da venda. Delivery: data de criação do pedido.',wraplength=950).pack(anchor='w',pady=5)
        panels=ttk.Panedwindow(self,orient='horizontal');panels.pack(fill='both',expand=True)
        listing=ttk.Frame(panels);self.details=OrderDetails(panels,self.s)
        panels.add(listing,weight=5);panels.add(self.details,weight=5)
        self.tree=table(listing,['Tipo','Número','Cliente','Valor','Situação'])
        for column,width in (('Tipo',80),('Número',100),('Cliente',120),('Valor',90),('Situação',120)):
            self.tree.column(column,width=width,anchor='e' if column=='Valor' else 'w')
        self.tree.bind('<<TreeviewSelect>>',lambda event:self.show_selected())
        self.rows={}

    def filters(self):
        return CommerceFilter(date_input(self.start.get()),date_input(self.end.get()),
            next((key for key,value in KINDS.items() if value==self.kind.get()),None),
            next((key for key,value in STATES.items() if value==self.state.get()),None),self.text.get())

    def refresh(self):
        rows=self.s.commerce.list(self.filters());self.rows={r.key:r for r in rows}
        def number(row):
            return f'{row.order_id} (venda {row.sale_id})' if row.kind=='TAB' else row.order_id if row.kind=='DELIVERY' else row.sale_id
        fill(self.tree,[(r.key,(KINDS[r.kind],number(r),r.customer,money(r.total_cents),STATES.get(r.state,r.state))) for r in rows])
        self.show_selected()

    def show_selected(self):
        selected=self.tree.selection();self.details.show(selected[0] if selected else None)

    def open_audit(self):
        from .audit import AuditView
        window=tk.Toplevel(self);window.title('Histórico de alterações e manutenção');window.geometry('1120x620')
        view=AuditView(window,self.s);view.pack(fill='both',expand=True);view.refresh()
        return view

    def backup_center(self):
        return self.open_audit().backup_center()
