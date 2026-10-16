from tkinter import ttk,simpledialog,messagebox
from .shared import View, ProductPicker, table,fill,command
from .sales import ask_payment
from ..common.money import money


class TabsView(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Comandas por cliente",style="Title.TLabel").pack(anchor="w")
        row=ttk.Frame(self);row.pack(fill="x",pady=6)
        self.customer=ttk.Entry(row,width=32);self.customer.pack(side="left")
        ttk.Button(row,text="Abrir comanda",command=lambda:self.act(self.create)).pack(side="left",padx=8)
        self.customer.bind("<Return>",lambda e:self.act(self.create))
        self.tabs_tree=table(self,["Comanda","Cliente","Total"],height=4)
        self.tabs_tree.bind("<<TreeviewSelect>>",lambda e:self.refresh_items())
        self.build_picker(self,self.add_selected)
        row=ttk.Frame(self);row.pack(side="bottom",fill="x",pady=6)
        for label,callback in (("Receber comanda",self.checkout),("Alterar quantidade",self.change_qty),("Cancelar comanda",self.cancel)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,8))
        self.items_tree=table(self,["Produto","Quantidade","Total"],height=5)

    def create(self):
        name=self.customer.get().strip()
        if any(t["name"].casefold()==name.casefold() for t in self.s.sales.open_tabs()):
            if not messagebox.askyesno("Nome já utilizado","Há uma comanda aberta com esse nome. Abrir outra?",parent=self):
                return
        id=self.s.sales.create_tab(name,command())
        self.customer.delete(0,"end")
        self.refresh()
        self.tabs_tree.selection_set(str(id))
        self.refresh_items()

    def add_selected(self):
        tab=self.selected(self.tabs_tree);pid=self.selected_product()
        old=next((r["qty"] for r in self.s.sales.lines(tab) if r["product_id"]==pid),0)
        self.s.sales.set_tab_qty(tab,pid,old+int(self.qty.get()),None,None,command())

    def change_qty(self):
        tab=self.selected(self.tabs_tree);pid=self.selected(self.items_tree)
        row=next(r for r in self.s.sales.lines(tab) if r["product_id"]==pid)
        qty=simpledialog.askinteger("Alterar quantidade","Nova quantidade (zero remove):",initialvalue=row["qty"],minvalue=0,parent=self)
        if qty is not None:
            grant=self.grant("tab.reduce") if qty<row["qty"] else None
            reason=self.reason() if grant else None
            self.s.sales.set_tab_qty(tab,pid,qty,grant,reason,command())

    def checkout(self):
        tab=self.selected(self.tabs_tree)
        payment=ask_payment(self,self.s.sales.total(tab))
        if payment:
            sale=self.s.sales.pay_tab(tab,payment,command())
            self.s.application.notify(f"Comanda recebida. Venda #{sale.id}.")

    def cancel(self):
        self.s.sales.cancel_tab(self.selected(self.tabs_tree),self.grant("tab.cancel"),self.reason(),command())

    def refresh(self):
        self.filter_products()
        fill(self.tabs_tree,[(t["id"],(t["id"],t["name"],money(self.s.sales.total(t["id"])))) for t in self.s.sales.open_tabs()])
        self.refresh_items()

    def refresh_items(self):
        from ..pricing.models import PriceCondition
        selection=self.tabs_tree.selection()
        rows=[]
        if selection:
            for line in self.s.sales.lines(int(selection[0])):
                if line["qty"]:
                    total=self.s.pricing.quote(PriceCondition(line["unit_cents"],line["group_qty"],line["group_cents"]),line["qty"]).total_cents
                    rows.append((line["product_id"],(line["name"],line["qty"],money(total))))
        fill(self.items_tree,rows)

