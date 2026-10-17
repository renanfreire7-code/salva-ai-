import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .shared import View, ProductPicker, table, fill, command
from ..sales.models import Payment
from ..common.money import parse_money, money


def ask_payment(parent,total):
    from .shared import ask_fields
    values=ask_fields(parent,"Receber pagamento",[("method","Dinheiro / Pix / Débito / Crédito","Dinheiro"),("received","Recebido em dinheiro (R$)",money(total).replace("R$ ", ""))])
    if not values:
        return None
    methods={"dinheiro":"MONEY","pix":"PIX","débito":"DEBIT","debito":"DEBIT","crédito":"CREDIT","credito":"CREDIT"}
    method=methods.get(values["method"].casefold())
    payment=Payment(method,parse_money(values["received"]) if method=="MONEY" else None)
    change=(payment.tendered_cents or 0)-total if method=="MONEY" else 0
    if messagebox.askyesno("Conferir recebimento",f"Total: {money(total)}\nTroco: {money(change)}\n\nConfirmar pagamento?",parent=parent):
        return payment
    return None


class SalesView(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        self.cart_id=None
        self.payment_command=None
        ttk.Label(self,text="Venda direta",style="Title.TLabel").pack(anchor="w")
        self.build_picker(self,self.add_selected)
        buttons=ttk.Frame(self);buttons.pack(side="bottom",fill="x",pady=8)
        self.total_label=ttk.Label(buttons,text="Total: R$ 0,00",style="Title.TLabel")
        self.total_label.pack(side="left")
        ttk.Button(buttons,text="Receber pagamento",command=lambda:self.act(self.checkout)).pack(side="right")
        ttk.Button(buttons,text="Alterar quantidade",command=lambda:self.act(self.change_qty)).pack(side="right",padx=8)
        ttk.Button(buttons,text="Novo carrinho",command=self.reset).pack(side="right",padx=8)
        self.tree=table(self,["Produto","Quantidade","Total","Economia"])

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
        payment=ask_payment(self,self.total_cents)
        if payment:
            self.submit(payment)

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
