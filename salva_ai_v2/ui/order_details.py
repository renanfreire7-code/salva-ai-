import tkinter as tk
from tkinter import ttk
from .shared import table,fill
from ..common.money import money

KINDS={'CART':'Balcão','TAB':'Comanda','DELIVERY':'Delivery'}
STATES={'PAID':'Recebida','REVERSED':'Estornada','PREPARING':'Em preparação','OUT':'Saiu para entrega','DELIVERED':'Entregue','CANCELED':'Cancelado','OPEN':'Aberta'}
METHODS={'MONEY':'Dinheiro','PIX':'Pix','DEBIT':'Débito','CREDIT':'Crédito à vista','LINK':'Link de pagamento'}
PAYMENT_STATES={'PAID':'Pago','PENDING':'Pendente','REFUND_PENDING':'Reembolso pendente','REFUNDED':'Reembolsado','NO_RECEIPT':'Sem recebimento'}
TIMING={'ADVANCE':'Antecipado','ON_DELIVERY':'Na entrega','UNSPECIFIED':'Não informado'}


def delivery_text(detail):
    order=detail['order'];plan=detail['payment_plan']
    lines=[f"Pedido #{order['id']} · {STATES.get(order['state'],order['state'])}",
        f"Cliente: {order['name']}",f"Telefone: {order['phone']}",f"Endereço: {order['address']}",f"Referência: {order['reference'] or '—'}",
        f"Criado: {order['created_at']}",f"Pagamento: {TIMING[plan['payment_timing']]} · {METHODS.get(plan['payment_channel'],'Não informado')}",
        f"Modalidade combinada: {METHODS[plan['method']]}",f"Produtos: {money(order['subtotal_cents'])}",
        f"Taxa cobrada: {money(order['delivery_fee_cents'])}",f"Total: {money(order['total_cents'])}",f"Valor por corrida: {money(order['courier_fee_cents'])}"]
    if order.get('complement'):lines.insert(4,'Complemento: '+order['complement'])
    if plan['link_reference']:lines.append('Link / referência: '+plan['link_reference'])
    if plan['expected_change_cents'] is None:lines.append('Troco combinado: não registrado nesta versão anterior.')
    else:
        lines.append('Troco previsto: '+money(plan['expected_change_cents']))
        if plan['change_for_cents']:lines.append('Troco para: '+money(plan['change_for_cents']))
    for item in detail['items']:lines.append(f"{item['qty']} × {item['name']} = {money(item['total_cents'])}")
    for collection in detail['collections']:
        lines.append(f"Recebimento #{collection['id']}: {money(collection['amount_cents'])} · {METHODS[collection['method']]} · {'Entregador' if collection['custodian']=='COURIER' else 'Bar'} · {collection['collected_at']}")
        if collection['method']=='MONEY':lines.append(f"Cliente entregou: {money(collection['tendered_cents'])} · troco real: {money(collection['change_cents'])}")
        lines.append(f"Reembolsado: {money(collection['refunded_cents'])}")
    if not detail['collections']:lines.append('Recebimento ainda não confirmado.')
    for trip in detail['trips']:lines.append(f"Corrida #{trip['id']} · {trip['dispatched_at']} · {money(trip['fee_cents'])} · pago {money(trip['paid_cents'])} · pendente {money(trip['pending_cents'])}")
    for refund in detail['refunds']:lines.append(f"Reembolso #{refund['id']}: devolvido {money(refund['refunded_cents'])} · pendente {money(refund['pending_cents'])}")
    for returned in detail['returns']:lines.append(f"Retorno: produto #{returned['product_id']} · {returned['qty']} unidades · {returned['returned_at'] or 'Data não registrada'}")
    lines.append('Dinheiro deste pedido ainda com entregador: '+money(detail['custody_pending_cents']))
    if order['previous_order_id']:lines.append(f"Nova tentativa do pedido #{order['previous_order_id']}")
    for record in detail['settlements']:lines.append(f"Acerto #{record['id']} · {record['occurred_at']}")
    return '\n'.join(lines)


def read_text(parent,height=8):
    frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,pady=4)
    widget=tk.Text(frame,height=height,width=35,wrap='word',font='TkDefaultFont',background='#ffffff',foreground='#233c3e',relief='flat',padx=8,pady=8)
    scroll=ttk.Scrollbar(frame,command=widget.yview);widget.configure(yscrollcommand=scroll.set)
    widget.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
    widget.configure(state='disabled')
    return widget


def set_text(widget,value):
    widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',value);widget.configure(state='disabled')


class OrderDetails(ttk.Frame):
    def __init__(self,parent,services):
        super().__init__(parent,padding=(12,0,0,0));self.s=services
        self.summary=tk.StringVar(value='Selecione uma venda ou pedido para conferir os itens.')
        ttk.Label(self,textvariable=self.summary,wraplength=480,justify='left').pack(anchor='w',pady=6)
        self.items_tree=table(self,['Produto','Quantidade','Preço normal','Promoção','Total'],height=4)
        self.items_tree.column('Produto',width=190,anchor='w')
        for column in ('Quantidade','Preço normal','Promoção','Total'):self.items_tree.column(column,width=85)
        self.facts=read_text(self,height=8)

    def show(self,key):
        if key is None:
            fill(self.items_tree,[]);self.summary.set('Selecione uma venda ou pedido para conferir os itens.');set_text(self.facts,'');return
        detail=self.s.commerce.detail(key);row=detail['row']
        number=f"Pedido #{row.order_id}" if row.kind=='DELIVERY' else f"Venda #{row.sale_id}"+(f" · Comanda #{row.order_id}" if row.kind=='TAB' else '')
        self.summary.set(f"{KINDS[row.kind]} · {number}\n{row.customer} · {row.occurred_at.strftime('%d/%m/%Y %H:%M')}\nTotal: {money(row.total_cents)} · {STATES.get(row.state,row.state)}\nPagamento: {PAYMENT_STATES[row.payment_state]} · Modalidade real: {METHODS.get(row.payment_method,'Ainda não recebida')}")
        fill(self.items_tree,[(r.product_id,(r.name,r.qty,money(r.unit_cents),f'{r.group_qty} por {money(r.group_cents)}' if r.group_qty else '—',money(r.total_cents))) for r in detail['items']])
        if detail['delivery']:text=delivery_text(detail['delivery'])
        else:
            payment=detail['payment']
            text=f"Modalidade real: {METHODS[payment['method']]}\nPagamento: {PAYMENT_STATES[row.payment_state]}\nValor da venda: {money(payment['total_cents'])}\nRecebido líquido: {money(row.paid_cents)}\n"
            if payment['method']=='MONEY':
                text+=f"Cliente entregou: {money(payment['tendered_cents'])}\nTroco: {money(payment['change_cents'])}\n"
            for refund in detail['refunds']:text+=f"Reembolso: {money(refund['refunded_cents'])} devolvido · {money(refund['pending_cents'])} pendente\n"
        set_text(self.facts,text)
