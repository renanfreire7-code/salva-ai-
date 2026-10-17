"""Confirmações comerciais: leitura de fatos, sem movimentar dinheiro/estoque."""
import tkinter as tk
from tkinter import ttk
from .order_details import METHODS,STATES
from ..common.money import money

TITLES={'CANCEL':'Cancelar pedido','REFUND':'Registrar reembolso','RETURN':'Conferir produtos devolvidos','REDELIVER':'Criar nova tentativa de entrega'}
EXPLANATIONS={
 'CANCEL':'Cancela o atendimento. Se já saiu, a corrida continua devida. Produtos devolvidos e dinheiro reembolsado precisam de conferência separada.',
 'REFUND':'Registre apenas o valor efetivamente devolvido ao cliente. O programa não devolve Pix/cartão automaticamente e não altera o estoque.',
 'RETURN':'Confirme apenas as unidades recebidas em condição de revenda. Esta ação devolve produtos ao estoque e não devolve dinheiro ao cliente.',
 'REDELIVER':'Cria outro pedido vinculado, com preços e taxas atuais. A nova tentativa fica em preparação; outra corrida será gerada somente ao sair.'}


def action_summary(detail,action):
    order=detail['order']
    explanation=EXPLANATIONS[action]
    if action=='REDELIVER' and order.get('payment_timing','UNSPECIFIED')=='UNSPECIFIED':
        explanation='Cria outro pedido vinculado, com preços e taxas atuais. Este pedido antigo sai imediatamente e gera outra corrida devida ao entregador.'
    lines=[explanation,'',f"Pedido #{order['id']} | {STATES.get(order['state'],order['state'])}",
        'Cliente: '+order['name'],'Endereço: '+order['address']]
    if order.get('complement'):lines.append('Complemento: '+order['complement'])
    for item in detail['items']:lines.append(f"{item['qty']} × {item['name']} = {money(item['total_cents'])}")
    lines.extend([f"Total original: {money(order['total_cents'])}",f"Taxa de entrega: {money(order['delivery_fee_cents'])}"])
    for receipt in detail['collections']:lines.append('Recebimento real: '+METHODS[receipt['method']]+' | '+money(receipt['amount_cents']))
    if not detail['collections']:lines.append('Sem recebimento confirmado.')
    refunded=sum(r['refunded_cents'] for r in detail['refunds']);pending=sum(r['pending_cents'] for r in detail['refunds'])
    lines.append(f'Reembolsado: {money(refunded)} | Reembolso pendente: {money(pending)}')
    lines.append('Corridas geradas: '+money(sum(r['fee_cents'] for r in detail['trips']))+' | A pagar: '+money(sum(r['pending_cents'] for r in detail['trips'])))
    if detail.get('confirmation'):lines.extend(['',detail['confirmation']])
    return '\n'.join(lines)


class ActionConfirmation(tk.Toplevel):
    """Scrollable facts with fixed actions; closing or Escape always declines."""
    def __init__(self,parent,title,text):
        super().__init__(parent)
        self.result=False
        self.title(title)
        self.transient(parent.winfo_toplevel())
        width=min(760,self.winfo_screenwidth()-60)
        height=min(600,self.winfo_screenheight()-100)
        self.geometry(f'{width}x{height}+30+30')
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        ttk.Label(self,text='Confira os dados antes de confirmar.',padding=12).grid(row=0,column=0,columnspan=2,sticky='w')
        self.content=tk.Text(self,wrap='word',width=60,height=15,padx=12,pady=8)
        self.scrollbar=ttk.Scrollbar(self,orient='vertical',command=self.content.yview)
        self.content.configure(yscrollcommand=self.scrollbar.set)
        self.content.grid(row=1,column=0,sticky='nsew',padx=(12,0))
        self.scrollbar.grid(row=1,column=1,sticky='ns',padx=(0,12))
        self.content.insert('1.0',text);self.content.configure(state='disabled')
        actions=ttk.Frame(self,padding=12);actions.grid(row=2,column=0,columnspan=2,sticky='e')
        cancel=ttk.Button(actions,text='Voltar',command=self.cancel);cancel.pack(side='left',padx=6)
        self.confirm_button=ttk.Button(actions,text='Confirmar operação',command=self.confirm)
        self.confirm_button.pack(side='left')
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.bind('<Escape>',lambda event:self.cancel())
        self.update_idletasks();self.grab_set();cancel.focus_set()

    def cancel(self):
        self.result=False;self.destroy()

    def confirm(self):
        self.result=True;self.destroy()

    def show(self):
        self.wait_window();return self.result


def confirm_action(parent,detail,action):
    return ActionConfirmation(parent,TITLES[action],action_summary(detail,action)).show()
