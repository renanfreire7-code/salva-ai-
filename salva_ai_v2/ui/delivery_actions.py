"""Confirmações comerciais: leitura de fatos, sem movimentar dinheiro/estoque."""
from tkinter import messagebox
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
    lines=[EXPLANATIONS[action],'',f"Pedido #{order['id']} | {STATES.get(order['state'],order['state'])}",
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


def confirm_action(parent,detail,action):
    return messagebox.askyesno(TITLES[action],action_summary(detail,action)+'\n\nConfirmar esta operação?',parent=parent)
