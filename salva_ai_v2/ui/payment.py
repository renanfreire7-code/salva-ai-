import tkinter as tk
from tkinter import ttk,messagebox
from .forms import FormDialog,FieldSpec
from ..common.errors import BusinessError
from ..common.money import money,parse_money
from ..sales.models import Payment

METHODS={'Dinheiro':'MONEY','Pix':'PIX','Débito':'DEBIT','Crédito à vista':'CREDIT'}


class PaymentDialog(FormDialog):
    def __init__(self,parent,total,on_submit=None):
        self.total=total;self.payment_submit=on_submit
        super().__init__(parent,'Receber pagamento',[
            FieldSpec('method','Forma de pagamento','Dinheiro',kind='choice',choices=tuple(METHODS),required=True),
            FieldSpec('received','Valor recebido em dinheiro (R$)',money(total).replace('R$ ',''))],on_submit=self.finish)
        self.save_button.configure(text='Confirmar recebimento')
        self.change=tk.StringVar(value=f'Total: {money(total)} · Troco: {money(0)}')
        ttk.Label(self,textvariable=self.change,style='Title.TLabel',padding=(20,8)).pack(before=self.winfo_children()[0],anchor='w')
        self.inputs['method'].bind('<<ComboboxSelected>>',lambda event:self.update_method())
        self.inputs['received'].bind('<KeyRelease>',lambda event:self.update_change())

    def update_method(self):
        cash=self.inputs['method'].get()=='Dinheiro'
        self.inputs['received'].configure(state='normal' if cash else 'disabled')
        self.update_change()

    def update_change(self):
        if self.inputs['method'].get()!='Dinheiro':
            self.change.set(f'Total: {money(self.total)} · Confirme o recebimento na conta ou maquininha.');return
        try:
            received=parse_money(self.inputs['received'].get())
            self.change.set(f'Total: {money(self.total)} · '+(f'Troco: {money(received-self.total)}' if received>=self.total else f'Faltam: {money(self.total-received)}'))
        except BusinessError:
            self.change.set(f'Total: {money(self.total)} · Informe o valor recebido.')

    def finish(self,values):
        method=METHODS[values['method']]
        received=parse_money(values['received']) if method=='MONEY' else None
        if received is not None and received<self.total:
            raise BusinessError('O valor recebido é menor que o total. Confira antes de confirmar.')
        payment=Payment(method,received)
        detail=f'Total: {money(self.total)}\nForma: {values["method"]}'
        if received is not None:detail+=f'\nRecebido: {money(received)}\nTroco: {money(received-self.total)}'
        if not messagebox.askyesno('Conferir recebimento',detail+'\n\nPagamento efetivamente recebido?',parent=self):
            raise BusinessError('Recebimento não confirmado. Revise os dados ou cancele.')
        return self.payment_submit(payment) if self.payment_submit else payment


def ask_payment(parent,total):
    return PaymentDialog(parent,total).show()
