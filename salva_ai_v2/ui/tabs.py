from tkinter import ttk,simpledialog,messagebox
from .shared import View, ProductPicker, table,fill,command
from .sales import ask_payment
from .payment import PaymentDialog
from ..common.money import money


class TabsView(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Comandas por cliente",style="Title.TLabel").pack(anchor="w")
        row=ttk.Frame(self);row.pack(fill="x",pady=6)
        self.customer=ttk.Entry(row,width=32);self.customer.pack(side="left")
        self.create_button=ttk.Button(row,text="Abrir comanda",command=lambda:self.act(self.create));self.create_button.pack(side="left",padx=8)
        self.create_button.bind("<Return>",lambda event:self.create_key())
        self.customer.bind("<Return>",lambda event:self.focus_create())
        panels=ttk.Panedwindow(self,orient='horizontal');panels.pack(fill='both',expand=True)
        listing=ttk.Frame(panels,padding=(0,0,12,0));detail=ttk.Frame(panels,padding=(12,0,0,0))
        panels.add(listing,weight=3);panels.add(detail,weight=7)
        self.tabs_tree=table(listing,["Comanda","Cliente","Total"],height=10)
        self.tabs_tree.column('Comanda',width=65);self.tabs_tree.column('Cliente',width=140,anchor='w');self.tabs_tree.column('Total',width=85)
        self.tabs_tree.bind("<<TreeviewSelect>>",lambda e:self.refresh_items())
        self.build_picker(detail,self.add_selected)
        row=ttk.Frame(detail);row.pack(side="bottom",fill="x",pady=6)
        for label,callback in (("Receber comanda",self.checkout),("Alterar quantidade",self.change_qty),("Cancelar comanda",self.cancel)):
            ttk.Button(row,text=label,style='Primary.TButton' if callback==self.checkout else 'Danger.TButton' if callback==self.cancel else 'TButton',command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,8))
        self.items_tree=table(detail,["Produto","Quantidade","Total"],height=5)
        self.items_tree.column('Produto',width=250,anchor='w')

    def focus_create(self):
        self.create_button.focus_set();return "break"

    def create_key(self):
        self.act(self.create);return "break"

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
        cmd=command()
        def submit(payment):
            sale=self.s.sales.pay_tab(tab,payment,cmd)
            self.s.application.notify(f"Comanda recebida. Venda #{sale.id}.")
            return sale
        PaymentDialog(self,self.s.sales.total(tab),on_submit=submit).show()

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
