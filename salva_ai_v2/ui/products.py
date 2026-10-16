from tkinter import ttk
from .shared import View, table, fill, ask_fields, command
from ..common.money import parse_money, money, round_half_up
from ..inventory.models import PurchaseLine


class ProductsView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Produtos e estoque",style="Title.TLabel").pack(anchor="w")
        actions=ttk.Frame(self);actions.pack(fill="x",pady=8)
        for label,callback in (("Novo produto",self.create),("Entrada / compra",self.purchase),("Promoção",self.promotion),("Ajustar estoque",self.adjust),("Atalho F1–F12",self.shortcut),("Desativar",self.deactivate)):
            ttk.Button(actions,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,6))
        self.tree=table(self,["Código","Produto","Preço","Físico","Reservado","Disponível","Mínimo","Custo médio"])

    def refresh(self):
        rows=[]
        for p in self.s.inventory.products():
            pos=self.s.inventory.position(p["id"])
            cost=money(round_half_up(pos.value_cents,pos.physical)) if pos.physical else "Sem estoque"
            rows.append((p["id"],(f'{p["id"]:03d}',p["name"],money(p["price_cents"]),pos.physical,pos.reserved,pos.available,p["min_stock"],cost)))
        fill(self.tree,rows)

    def create(self):
        values=ask_fields(self,"Novo produto",[("name","Nome",""),("price","Preço normal (R$)",""),("pack","Unidades por caixa/fardo",1),("minimum","Estoque mínimo",0)])
        if values:
            self.s.inventory.create_product(values["name"],parse_money(values["price"]),int(values["pack"]),int(values["minimum"]),command())
            self.s.application.notify("Produto cadastrado.")

    def purchase(self):
        pid=self.selected(self.tree)
        today=self.s.clock.today().isoformat()
        values=ask_fields(self,"Entrada de mercadoria",[("qty","Quantidade de unidades",1),("cost","Custo total dos produtos (R$)",""),("freight","Frete (R$)","0,00"),("date","Data do gasto (AAAA-MM-DD)",today),("due","Vencimento (AAAA-MM-DD)",today)])
        if values:
            self.s.inventory.receive_purchase([PurchaseLine(pid,int(values["qty"]),parse_money(values["cost"]))],parse_money(values["freight"]),values["date"],values["due"],command())
            self.s.application.notify("Compra registrada no estoque e nas contas a pagar.")

    def promotion(self):
        pid=self.selected(self.tree)
        values=ask_fields(self,"Promoção por quantidade",[("qty","Quantidade do grupo",3),("price","Preço do grupo (R$)","12,00"),("active","Ativa? (sim/não)","sim")])
        if values:
            self.s.pricing.set_promotion(pid,int(values["qty"]),parse_money(values["price"]),values["active"].casefold()=="sim",command())

    def adjust(self):
        pid=self.selected(self.tree)
        values=ask_fields(self,"Ajuste de estoque",[("delta","Variação em unidades (+ ou -)",""),("reason","Motivo","")])
        if values:
            self.s.inventory.adjust(pid,int(values["delta"]),values["reason"],self.grant("stock.adjust"),command())

    def shortcut(self):
        pid=self.selected(self.tree)
        values=ask_fields(self,"Selecionar por atalho",[("key","Número da tecla F1 a F12",1)])
        if values:
            self.s.inventory.assign_shortcut(int(values["key"]),pid,command())

    def deactivate(self):
        self.s.inventory.deactivate(self.selected(self.tree),self.grant("product.deactivate"),self.reason(),command())

