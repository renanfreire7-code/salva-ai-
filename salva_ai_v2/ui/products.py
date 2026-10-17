from tkinter import ttk
from .shared import View, table, fill, ask_fields, command,FieldSpec
from ..common.service import integer
from ..common.money import parse_money, money, round_half_up
from ..inventory.models import PurchaseLine


class ProductsView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Produtos e estoque",style="Title.TLabel").pack(anchor="w")
        actions=ttk.Frame(self);actions.pack(fill="x",pady=8)
        for label,callback in (("Novo produto",self.create),("Editar produto",self.edit),("Promoção",self.promotion),("Atalho F1–F12",self.shortcut),("Desativar",self.deactivate)):
            ttk.Button(actions,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,6))
        actions=ttk.Frame(self);actions.pack(fill='x',pady=(0,4))
        for label,callback in (("Entrada / compra",self.purchase),("Compras / devoluções",self.purchase_history),("Ajustar estoque",self.adjust)):
            ttk.Button(actions,text=label,command=lambda f=callback:self.act(f)).pack(side='left',padx=(0,6))
        self.tree=table(self,["Código","Produto","Preço","Físico","Reservado","Disponível","Mínimo","Custo médio"])

    def refresh(self):
        rows=[]
        for p in self.s.inventory.products():
            pos=self.s.inventory.position(p["id"])
            cost=money(round_half_up(pos.value_cents,pos.physical)) if pos.physical else "Sem estoque"
            rows.append((p["id"],(f'{p["id"]:03d}',p["name"],money(p["price_cents"]),pos.physical,pos.reserved,pos.available,p["min_stock"],cost)))
        fill(self.tree,rows)

    def purchase_history(self):
        view=self.s.application.purchases_view
        self.s.application.show_view(view)
        return view

    def create(self):
        cmd=command()
        def submit(values):
            result=self.s.inventory.create_product(values['name'],parse_money(values['price']),int(values['pack']),int(values['minimum']),cmd)
            self.s.application.notify('Produto cadastrado.');return result
        ask_fields(self,'Novo produto',[
            FieldSpec('name','Nome',required=True),FieldSpec('price','Preço normal (R$)',required=True,validator=parse_money),
            FieldSpec('pack','Unidades por caixa/fardo',1,validator=lambda value:integer(int(value),'Unidades',1)),
            FieldSpec('minimum','Estoque mínimo',0,validator=lambda value:integer(int(value),'Mínimo'))],on_submit=submit)

    def purchase(self):
        pid=self.selected(self.tree)
        today=self.s.clock.today().isoformat()
        cmd=command()
        def submit(values):
            from ..sales.models import Payment
            from ..common.errors import BusinessError
            unit=values['unit'].casefold()
            if unit not in ('unidade','caixa','fardo','caixa/fardo'):
                raise BusinessError('Escolha unidade ou caixa/fardo.')
            product=next(p for p in self.s.inventory.products() if p['id']==pid)
            qty=int(values['qty'])*(product['pack_size'] if unit!='unidade' else 1)
            modes={'pendente':None,'pix':'PIX','dinheiro da gaveta':'MONEY','débito':'DEBIT','crédito':'CREDIT'}
            if values['payment'].casefold() not in modes:
                raise BusinessError('Escolha uma das formas de pagamento indicadas.')
            method=modes[values['payment'].casefold()]
            payment=Payment(method) if method else None
            purchase=self.s.inventory.receive_and_pay_purchase([PurchaseLine(pid,qty,parse_money(values['cost']))],parse_money(values['freight']),values['date'],values['due'],payment,self.grant('cash.withdraw') if method=='MONEY' else None,cmd)
            self.s.application.notify(f'Compra #{purchase} registrada no estoque e no financeiro.')
            return purchase
        ask_fields(self,'Entrada de mercadoria',[
            FieldSpec('qty','Quantidade',1,validator=lambda value:integer(int(value),'Quantidade',1)),
            FieldSpec('unit','Unidade de entrada','unidade',kind='choice',choices=('unidade','caixa/fardo')),
            FieldSpec('cost','Custo total dos produtos (R$)',required=True,validator=parse_money),
            FieldSpec('freight','Frete (R$)','0,00',validator=parse_money),
            FieldSpec('date','Data do gasto (AAAA-MM-DD)',today),FieldSpec('due','Vencimento (AAAA-MM-DD)',today),
            FieldSpec('payment','Pagamento','Pendente',kind='choice',choices=('Pendente','Pix','Dinheiro da gaveta','Débito','Crédito'))],on_submit=submit)

    def edit(self):
        pid=self.selected(self.tree)
        product=next(p for p in self.s.inventory.products() if p['id']==pid)
        cmd=command()
        def submit(values):
            before=self.s.pricing.snapshot(pid)
            result=self.s.inventory.update_product(pid,values['name'],parse_money(values['price']),int(values['pack']),int(values['minimum']),self.grant('product.edit'),self.reason(),cmd)
            disabled=before.group_qty is not None and self.s.pricing.snapshot(pid).group_qty is None
            self.s.application.notify('Produto atualizado.'+(' A promoção foi desativada porque deixou de oferecer economia.' if disabled else ''))
            return result
        ask_fields(self,'Editar produto',[
            FieldSpec('name','Nome',product['name'],required=True),
            FieldSpec('price','Preço normal (R$)',money(product['price_cents']).replace('R$ ',''),validator=parse_money),
            FieldSpec('pack','Unidades por caixa/fardo',product['pack_size'],validator=lambda value:integer(int(value),'Unidades',1)),
            FieldSpec('minimum','Estoque mínimo',product['min_stock'],validator=lambda value:integer(int(value),'Mínimo'))],on_submit=submit)

    def promotion(self):
        pid=self.selected(self.tree)
        cmd=command()
        return ask_fields(self,'Promoção por quantidade',[
            FieldSpec('qty','Quantidade do grupo',3,validator=lambda value:integer(int(value),'Quantidade',2)),
            FieldSpec('price','Preço do grupo (R$)','12,00',validator=parse_money),
            FieldSpec('active','Promoção ativa?','Sim',kind='choice',choices=('Sim','Não'))],
            on_submit=lambda values:self.s.pricing.set_promotion(pid,int(values['qty']),parse_money(values['price']),values['active']=='Sim',cmd))

    def adjust(self):
        pid=self.selected(self.tree);cmd=command()
        return ask_fields(self,'Ajuste de estoque',[FieldSpec('delta','Variação em unidades (+ ou -)',validator=int,required=True),FieldSpec('reason','Motivo',required=True)],
            on_submit=lambda values:self.s.inventory.adjust(pid,int(values['delta']),values['reason'],self.grant('stock.adjust'),cmd))

    def shortcut(self):
        pid=self.selected(self.tree);cmd=command()
        return ask_fields(self,'Selecionar por atalho',[FieldSpec('key','Número da tecla F1 a F12','1',kind='choice',choices=tuple(str(i) for i in range(1,13)))],
            on_submit=lambda values:self.s.inventory.assign_shortcut(int(values['key']),pid,cmd))

    def deactivate(self):
        self.s.inventory.deactivate(self.selected(self.tree),self.grant("product.deactivate"),self.reason(),command())
