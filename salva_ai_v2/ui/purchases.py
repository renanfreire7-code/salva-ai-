from tkinter import ttk,messagebox
from .shared import View,table,fill,ask_fields,command,FieldSpec
from ..common.money import money,parse_money
from ..common.errors import BusinessError
from ..inventory.models import CartLine


class PurchasesView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True)
        purchases=ttk.Frame(tabs);credits=ttk.Frame(tabs)
        tabs.add(purchases,text='Compras e devoluções');tabs.add(credits,text='Créditos do fornecedor')
        ttk.Label(purchases,text='Selecione a compra e um item para devolução. Reverter cancela toda a entrada; registre depois a compra correta.',wraplength=950).pack(anchor='w')
        row=ttk.Frame(purchases);row.pack(fill='x',pady=6)
        for label,callback in (('Reverter compra',self.reverse_purchase),('Devolver item selecionado',self.return_item)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side='left',padx=4)
        self.tree=table(purchases,['Compra','Data','Valor','Pago / abatido','Situação'],height=6)
        self.items_tree=table(purchases,['Produto','Quantidade','Devolvido','Custo da linha'],height=5)
        self.tree.bind('<<TreeviewSelect>>',lambda event:self.select_purchase())
        ttk.Label(credits,text='Crédito não é dinheiro recebido. Confirme a devolução efetiva ou o abatimento na própria compra.',wraplength=950).pack(anchor='w')
        ttk.Button(credits,text='Confirmar recebimento / abatimento',command=lambda:self.act(self.settle_credit)).pack(anchor='w',pady=6)
        self.credits_tree=table(credits,['Crédito','Compra','Valor','Liquidado','Pendente','Motivo'])
        self.refresh()

    def refresh(self):
        inventory=self.s.inventory
        fill(self.tree,[(r['id'],(r['id'],r['incurred_on'],money(r['total_cents']),money(r['paid_cents']),'Revertida' if r['reversed'] else 'Registrada')) for r in inventory.purchases()])
        fill(self.credits_tree,[(r['id'],(r['id'],r['purchase_id'],money(r['amount_cents']),money(r['received_cents']),money(r['pending_cents']),r['reason'])) for r in inventory.supplier_credits()])
        if self.tree.selection():
            self.select_purchase()

    def select_purchase(self):
        if not self.tree.selection():
            fill(self.items_tree,[])
            return
        rows=self.s.inventory.purchase_lines(self.selected(self.tree))
        fill(self.items_tree,[(r['product_id'],(r['name'],r['qty'],r['returned_qty'],money(r['total_cents']))) for r in rows])

    def reverse_purchase(self):
        purchase=self.selected(self.tree)
        if not messagebox.askyesno('Reverter compra',f'Reverter toda a compra #{purchase}? O estoque e a obrigação serão corrigidos. Valores já pagos gerarão crédito a conferir com o fornecedor.',parent=self):
            return
        self.s.inventory.reverse_purchase(purchase,self.grant('purchase.reverse'),self.reason(),command())
        self.refresh()
        self.s.application.notify('Compra revertida. Consulte créditos se já havia pagamento; registre a entrada correta.')

    def return_item(self):
        purchase=self.selected(self.tree);product=self.selected(self.items_tree);cmd=command()
        def submit(values):
            result=self.s.inventory.return_to_supplier(purchase,[CartLine(product,int(values['qty']))],self.grant('purchase.return'),self.reason(),cmd)
            self.refresh();self.s.application.notify('Devolução registrada. Confira o crédito na aba Créditos do fornecedor.');return result
        return ask_fields(self,'Devolver ao fornecedor',[FieldSpec('qty','Quantidade em unidades',1,validator=int)],on_submit=submit)

    def settle_credit(self):
        credit=self.selected(self.credits_tree);cmd=command()
        def submit(values):
            mode={'recebimento':'RECEIPT','abatimento':'OFFSET'}.get(values['mode'].casefold())
            modes={'pix':'PIX','dinheiro na gaveta':'MONEY','dinheiro fora':'MONEY','débito':'DEBIT','crédito':'CREDIT'}
            method=modes.get(values['method'].casefold())
            if not mode or (mode=='RECEIPT' and not method):raise BusinessError('Escolha uma das opções indicadas.')
            result=self.s.inventory.settle_supplier_credit(credit,parse_money(values['amount']),mode,method if mode=='RECEIPT' else None,mode=='RECEIPT' and values['method'].casefold()=='dinheiro na gaveta',values['date'],self.grant('purchase.credit.settle'),self.reason(),cmd)
            self.refresh();self.s.application.notify('Crédito liquidado com registro no histórico.');return result
        return ask_fields(self,'Confirmar crédito do fornecedor',[
            FieldSpec('amount','Valor confirmado (R$)',required=True,validator=parse_money),
            FieldSpec('mode','Forma de confirmação','Recebimento',kind='choice',choices=('Recebimento','Abatimento')),
            FieldSpec('method','Forma do recebimento','Pix',kind='choice',choices=('Pix','Dinheiro na gaveta','Dinheiro fora','Débito','Crédito')),
            FieldSpec('date','Data da confirmação (AAAA-MM-DD)',self.s.clock.today().isoformat())],on_submit=submit)
