import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .shared import View, ProductPicker, table, fill, command
from ..sales.models import Payment
from ..common.money import parse_money, money


from .payment import ask_payment,PaymentDialog


class SalesView(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        self.cart_id=None
        self.payment_command=None
        ttk.Label(self,text="Venda de balcão",style="Title.TLabel").pack(anchor="w",pady=(0,8))
        panels=ttk.Panedwindow(self,orient='horizontal');panels.pack(fill='both',expand=True)
        catalog=ttk.Frame(panels,padding=(0,0,12,0));order=ttk.Frame(panels,padding=(12,0,0,0))
        panels.add(catalog,weight=4);panels.add(order,weight=6)
        self.build_picker(catalog,self.add_selected)
        self.product_tree=table(catalog,['Produto','Preço','Disponível'],height=8)
        self.product_tree.column('Produto',width=230,anchor='w');self.product_tree.column('Preço',width=80);self.product_tree.column('Disponível',width=85)
        self.product_tree.bind('<Double-1>',lambda event:self.choose_catalog())
        ttk.Label(order,text='Pedido atual',style='Title.TLabel').pack(anchor='w')
        buttons=ttk.Frame(order);buttons.pack(side="bottom",fill="x",pady=8)
        self.total_label=ttk.Label(buttons,text="Total: R$ 0,00",style="Title.TLabel")
        self.total_label.pack(side="left")
        ttk.Button(buttons,text="Receber",style='Primary.TButton',command=lambda:self.act(self.checkout)).pack(side="right")
        actions=ttk.Frame(order);actions.pack(side='bottom',fill='x',pady=4)
        ttk.Button(actions,text="Alterar quantidade",command=lambda:self.act(self.change_qty)).pack(side="left",padx=(0,8))
        ttk.Button(actions,text="Novo pedido",command=self.reset).pack(side="left")
        self.tree=table(order,["Produto","Quantidade","Total","Economia"])
        self.tree.column('Produto',width=230,anchor='w')
        for column in ('Quantidade','Total','Economia'):self.tree.column(column,width=85)

    def render_product_candidates(self,products):
        fill(self.product_tree,[(p['id'],(p['name'],money(p['price_cents']),self.s.inventory.position(p['id']).available)) for p in products])

    def choose_catalog(self):
        from ..inventory.queries import product_label
        selected=self.product_tree.selection()
        if selected:
            pid=int(selected[0]);product=next(p for p in self.s.inventory.products() if p['id']==pid)
            self.search.set(product_label(product));self.products_map[self.search.get()]=pid;self.qty.focus_set()

    @property
    def total_cents(self):
        return self.s.sales.total(self.cart_id) if self.cart_id else 0

    def add_product(self,pid,qty):
        if self.cart_id is None:
            self.cart_id=self.s.sales.create_cart(command())
        existing=next((row["qty"] for row in self.s.sales.lines(self.cart_id) if row["product_id"]==pid),0)
        self.s.sales.set_cart_qty(self.cart_id,pid,existing+qty,command())
        self.payment_command=None
        self.refresh()

    def add_selected(self):
        self.add_product(self.selected_product(),int(self.qty.get()))

    def change_qty(self):
        pid=self.selected(self.tree)
        qty=simpledialog.askinteger("Quantidade","Nova quantidade (zero remove):",parent=self,minvalue=0)
        if qty is not None:
            self.s.sales.set_cart_qty(self.cart_id,pid,qty,command())
            self.payment_command=None

    def submit(self,payment):
        if self.cart_id is None:
            from ..common.errors import BusinessError
            raise BusinessError("Adicione produtos antes de receber.")
        self.payment_command=self.payment_command or command()
        sale=self.s.sales.sell(self.cart_id,payment,self.payment_command)
        self.cart_id=None
        self.payment_command=None
        self.s.application.notify(f"Venda #{sale.id} registrada. Troco: {money(sale.change_cents)}")
        self.refresh()
        return sale

    def checkout(self):
        if not self.total_cents:
            from ..common.errors import BusinessError
            raise BusinessError('Adicione produtos antes de receber.')
        PaymentDialog(self,self.total_cents,on_submit=self.submit).show()

    def reset(self):
        if self.total_cents and not messagebox.askyesno("Novo carrinho","Descartar o carrinho atual?",parent=self):
            return
        self.cart_id=None;self.payment_command=None;self.refresh()

    def refresh(self):
        from ..pricing.models import PriceCondition
        self.filter_products()
        rows=[]
        if self.cart_id:
            for line in self.s.sales.lines(self.cart_id):
                if line["qty"]:
                    quote=self.s.pricing.quote(PriceCondition(line["unit_cents"],line["group_qty"],line["group_cents"]),line["qty"])
                    rows.append((line["product_id"],(line["name"],line["qty"],money(quote.total_cents),money(quote.savings_cents))))
        fill(self.tree,rows)
        self.total_label.configure(text="Total: "+money(self.total_cents))
