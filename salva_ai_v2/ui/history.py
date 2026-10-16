import tkinter as tk
from tkinter import ttk,messagebox
from .shared import View,table,fill,ask_fields,command
from .finance import date_input
from ..finance.queries import month_range
from ..reporting.models import HistoryFilter
from ..sales.models import Payment


class HistoryView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Histórico e correções',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(self);row.pack(fill='x',pady=8)
        start,end=month_range(self.s.clock.today().strftime('%Y-%m'))
        self.start=tk.StringVar(value=start.strftime('%d/%m/%Y'));self.end=tk.StringVar(value=end.strftime('%d/%m/%Y'))
        self.object_id=tk.StringVar()
        for label,var in (('De',self.start),('Até',self.end),('ID do registro',self.object_id)):
            ttk.Label(row,text=label).pack(side='left');ttk.Entry(row,textvariable=var,width=12).pack(side='left',padx=6)
        ttk.Button(row,text='Consultar',command=lambda:self.act(self.refresh)).pack(side='left',padx=6)
        ttk.Button(row,text='Corrigir venda / reabrir comanda',command=lambda:self.act(self.reverse)).pack(side='left',padx=6)
        self.actions=row
        self.tree=table(self,['Data','Operação','Registro','Motivo'])

    def refresh(self):
        filters=HistoryFilter(date_input(self.start.get()),date_input(self.end.get()),self.object_id.get().strip() or None)
        fill(self.tree,[(r.id,(r.occurred_at.strftime('%d/%m/%Y %H:%M'),r.kind,r.object_id,r.description)) for r in self.s.reports.history(filters)])

    def reverse(self):
        from ..common.money import parse_money
        values=ask_fields(self,'Corrigir venda',[('sale','Número da venda',''),('returned','Mercadoria retornou? sim/não','não'),('refund','Reembolso confirmado? sim/não','não'),('method','Dinheiro / Pix / Débito / Crédito','Dinheiro'),('amount','Valor devolvido em dinheiro (R$)','0,00'),('reopen','Reabrir comanda? sim/não','não')])
        if values:
            methods={'dinheiro':'MONEY','pix':'PIX','débito':'DEBIT','debito':'DEBIT','crédito':'CREDIT','credito':'CREDIT'}
            method=methods.get(values['method'].casefold())
            refund=Payment(method,parse_money(values['amount']) if method=='MONEY' else None) if values['refund'].casefold()=='sim' else None
            self.s.sales.reverse_sale(int(values['sale']),values['returned'].casefold()=='sim',refund,values['reopen'].casefold()=='sim',self.grant('sale.reverse'),self.reason(),command())
