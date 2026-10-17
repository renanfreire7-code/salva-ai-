import tkinter as tk
from tkinter import ttk,messagebox
from .forms import FormDialog,FieldSpec
from .shared import command
from .payment import METHODS
from ..common.errors import BusinessError
from ..common.money import money,parse_money


class DeliveryReceiptDialog(FormDialog):
    def __init__(self,parent,services,order_id):
        self.s=services;self.order_id=order_id;self.command_id=command()
        self.detail=self.s.delivery_queries.detail(order_id)
        self.order=self.detail['order'];self.plan=self.detail['payment_plan']
        self.total=self.order['total_cents']
        labels={value:key for key,value in METHODS.items()}
        method=labels[self.order['method']]
        choices=('Débito','Crédito à vista') if self.plan['payment_channel']=='LINK' else (method,)
        cash=self.order['method']=='MONEY'
        fields=[FieldSpec('method','Modalidade real conforme comprovante',method,kind='choice',choices=choices),
            FieldSpec('custodian','Quem recebeu?','Entregador' if cash else 'Bar',kind='choice',choices=('Bar','Entregador') if cash else ('Bar',)),
            FieldSpec('received','Valor entregue pelo cliente em dinheiro (R$)',money(self.plan['change_for_cents'] or self.total).replace('R$ ',''))]
        super().__init__(parent,f'Confirmar recebimento · Pedido #{order_id}',fields,on_submit=self.finish)
        self.save_button.configure(text='Confirmar recebimento')
        if not cash:self.inputs['received'].configure(state='disabled')
        self.summary=tk.StringVar(value=f'Total do pedido: {money(self.total)}\nTroco combinado: '+('Não registrado' if self.plan['expected_change_cents'] is None else money(self.plan['expected_change_cents'])))
        ttk.Label(self,textvariable=self.summary,padding=(20,10),wraplength=500).pack(before=self.winfo_children()[0],anchor='w')

    def finish(self,values):
        method=METHODS[values['method']];cash=method=='MONEY'
        tendered=parse_money(values['received']) if cash else None
        if cash and tendered<self.total:raise BusinessError('Valor recebido menor que o total.')
        difference=cash and self.plan['payment_timing']!='UNSPECIFIED' and tendered!=(self.plan['change_for_cents'] or self.total)
        summary=f'Pedido #{self.order_id}\nTotal: {money(self.total)}\nForma: {values["method"]}\nRecebedor: {values["custodian"]}'
        if cash:summary+=f'\nRecebido: {money(tendered)}\nTroco real: {money(tendered-self.total)}'
        if difference:summary+='\n\nO valor difere do combinado. Confira o novo troco.'
        if not messagebox.askyesno('Conferir recebimento',summary+'\n\nPagamento efetivamente recebido?',parent=self):
            raise BusinessError('Recebimento não confirmado. Revise os dados.')
        return self.s.delivery.record_payment(self.order_id,method,self.total,'COURIER' if values['custodian']=='Entregador' else 'BAR',tendered,self.command_id,confirm_change_difference=difference)
