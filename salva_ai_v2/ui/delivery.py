import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from .shared import View,ProductPicker,table,fill,ask_fields,command
from ..inventory.models import CartLine
from ..delivery.models import DeliveryDraft
from ..common.money import money,parse_money

METHODS={"Dinheiro":"MONEY","Pix":"PIX","Débito":"DEBIT","Crédito":"CREDIT"}
STATES={"PREPARING":"Em preparação","OUT":"Saiu para entrega","DELIVERED":"Entregue","CANCELED":"Cancelado"}


class DeliveryEditor(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        self.lines={}
        self.fields={}
        grid=ttk.Frame(self);grid.pack(fill="x")
        for i,(key,label) in enumerate((("customer","Cliente"),("phone","Telefone"),("address","Endereço"),("reference","Referência"))):
            ttk.Label(grid,text=label).grid(row=i//2,column=(i%2)*2,sticky="w",padx=6,pady=6)
            entry=ttk.Entry(grid,width=35);entry.grid(row=i//2,column=(i%2)*2+1,sticky="ew",padx=6,pady=6)
            self.fields[key]=entry
        row=ttk.Frame(self);row.pack(fill="x",pady=6)
        ttk.Label(row,text="Pagamento combinado").pack(side="left")
        self.method=tk.StringVar(value="Dinheiro")
        ttk.Combobox(row,textvariable=self.method,values=list(METHODS),state="readonly",width=14).pack(side="left",padx=8)
        self.build_picker(self,self.add)
        self.tree=table(self,["Produto","Quantidade"],height=8)
        row=ttk.Frame(self);row.pack(fill="x",pady=8)
        self.summary=ttk.Label(row,text="");self.summary.pack(side="left")
        ttk.Button(row,text="Remover item",command=lambda:self.act(self.remove)).pack(side="right",padx=8)
        ttk.Button(row,text="Confirmar pedido",command=lambda:self.act(self.submit)).pack(side="right")
        self.refresh()

    def add(self):
        pid=self.selected_product();qty=int(self.qty.get())
        if qty<1:
            from ..common.errors import BusinessError
            raise BusinessError("Quantidade deve ser positiva.")
        self.lines[pid]=self.lines.get(pid,0)+qty
        self.refresh()

    def remove(self):
        self.lines.pop(self.selected(self.tree),None);self.refresh()

    def refresh(self):
        self.filter_products()
        products={r["id"]:r for r in self.s.inventory.products()}
        fill(self.tree,[(id,(products[id]["name"],qty)) for id,qty in self.lines.items()])
        fees=self.s.delivery.settings()
        total=sum(self.s.pricing.quote(self.s.pricing.snapshot(id),qty).total_cents for id,qty in self.lines.items())+fees["customer_fee_cents"]
        self.summary.configure(text=f"Total previsto: {money(total)} • Entrega: {money(fees['customer_fee_cents'])}")

    def submit(self):
        values={key:entry.get().strip() for key,entry in self.fields.items()}
        draft=DeliveryDraft(values["customer"],values["phone"],values["address"],values["reference"],
            [CartLine(pid,qty) for pid,qty in self.lines.items()],METHODS[self.method.get()],"COURIER")
        order=self.s.delivery.confirm(draft,command())
        self.s.application.notify(f"Pedido #{order.id} confirmado. Total: {money(order.total_cents)}")
        self.master.destroy()


class DeliveryView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        from .assets import load_asset
        self.moto=load_asset(self,'motorcycle.png',24)
        self.motorcycle_label=ttk.Label(self,text='Delivery',image=self.moto,compound='left',style='Title.TLabel')
        self.motorcycle_label.pack(anchor='w')
        row=ttk.Frame(self);row.pack(fill="x",pady=6)
        for label,callback in (("Novo pedido",self.create),("Detalhes",self.details),("Receber",self.receive),("Saiu para entrega",self.dispatch),("Marcar entregue",self.delivered),("Cancelar",self.cancel)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,6))
        row=ttk.Frame(self);row.pack(fill="x",pady=(0,6))
        for label,callback in (("Conferir devolução",self.returned),("Reembolsar",self.refund),("Nova tentativa",self.redeliver),("Acertar entregas",self.settlement),("Taxas fixas",self.fees)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,6))
        self.summary=ttk.Label(self,text="");self.summary.pack(anchor="w",pady=5)
        self.tree=table(self,["Pedido","Cliente","Situação","Pagamento","Total","Entrega","Entregador"])

    def refresh(self):
        rows=[]
        for r in self.s.delivery.list_orders():
            order=self.s.delivery.order(r["id"])
            paid="Pago" if order.paid_cents>=order.total_cents else "Pendente"
            rows.append((r["id"],(r["id"],r["name"],STATES.get(order.state,order.state),paid,money(order.total_cents),money(order.delivery_fee_cents),money(order.courier_fee_cents))))
        fill(self.tree,rows)
        pending=sum(r["pending_cents"] for r in self.s.settlements.trips_pending())
        self.summary.configure(text=f"Dinheiro com entregador: {money(self.s.settlements.pending_custody_cents())} • Corridas a pagar: {money(pending)}")

    def create(self):
        window=tk.Toplevel(self);window.title("Novo pedido de delivery");window.geometry("1000x620")
        editor=DeliveryEditor(window,self.s);editor.pack(fill="both",expand=True)

    def details(self):
        id=self.selected(self.tree)
        row=next(r for r in self.s.delivery.list_orders() if r["id"]==id)
        lines=self.s.sales.lines(id)
        messagebox.showinfo(f"Pedido #{id}",f'{row["name"]}\n{row["phone"]}\n{row["address"]}\nReferência: {row["reference"]}\n\n'+
            "\n".join(f'{line["qty"]} × {line["name"]}' for line in lines),parent=self)

    def receive(self):
        id=self.selected(self.tree);order=self.s.delivery.order(id)
        details=next(r for r in self.s.delivery.list_orders() if r["id"]==id)
        method=details["method"]
        values=ask_fields(self,"Confirmar recebimento",[("custodian","Quem recebeu? bar / entregador","entregador" if method=="MONEY" else "bar"),("received","Recebido em dinheiro (R$)",money(order.total_cents).replace("R$ ",""))])
        if values:
            self.s.delivery.record_payment(id,method,order.total_cents,"COURIER" if values["custodian"].casefold()=="entregador" else "BAR",
                parse_money(values["received"]) if method=="MONEY" else None,command())

    def dispatch(self):
        id=self.selected(self.tree);order=self.s.delivery.order(id)
        if messagebox.askyesno("Registrar saída",f"Esta saída gera uma corrida de {money(order.courier_fee_cents)}, mesmo sem entrega concluída. Confirmar?",parent=self):
            self.s.delivery.dispatch(id,command())

    def delivered(self):
        self.s.delivery.mark_delivered(self.selected(self.tree),command())

    def cancel(self):
        self.s.delivery.cancel(self.selected(self.tree),self.grant("delivery.cancel"),self.reason(),command())

    def returned(self):
        id=self.selected(self.tree)
        window=tk.Toplevel(self);window.title("Conferir retorno");window.geometry("660x350")
        root=View(window,self.s);root.pack(fill="both",expand=True)
        ttk.Label(root,text="Selecione o produto e informe apenas a quantidade conferida.").pack(anchor="w")
        tree=table(root,["Produto","Quantidade enviada"],height=5)
        fill(tree,[(r["product_id"],(r["name"],r["qty"])) for r in self.s.sales.lines(id)])
        def confirm():
            pid=root.selected(tree)
            qty=simpledialog.askinteger("Retorno","Unidades recebidas em condição de revenda:",minvalue=1,parent=window)
            if qty:
                self.s.delivery.confirm_return(id,[CartLine(pid,qty)],self.grant("delivery.return"),self.reason(),command())
                window.destroy()
        ttk.Button(root,text="Confirmar unidades",command=lambda:root.act(confirm)).pack(anchor="e")

    def refund(self):
        id=self.selected(self.tree)
        details=next(r for r in self.s.delivery.list_orders() if r["id"]==id)
        values=ask_fields(self,"Confirmar reembolso realizado",[("amount","Valor devolvido (R$)",""),("drawer","Se dinheiro, saiu da gaveta? sim/não","não")])
        if values:
            self.s.delivery.refund(id,details["method"],parse_money(values["amount"]),values["drawer"].casefold()=="sim",
                self.grant("delivery.refund"),self.reason(),command())

    def redeliver(self):
        id=self.selected(self.tree)
        if messagebox.askyesno("Nova tentativa","Criar novo pedido vinculado, com taxas atuais, e registrar nova saída?\nA corrida anterior permanece devida.",parent=self):
            self.s.delivery.redeliver(id,self.grant("delivery.redeliver"),self.reason(),command())

    def fees(self):
        settings=self.s.delivery.settings()
        values=ask_fields(self,"Valores fixos por entrega",[("customer","Taxa cobrada do cliente (R$)",money(settings["customer_fee_cents"]).replace("R$ ","")),("courier","Valor pago ao entregador (R$)",money(settings["courier_fee_cents"]).replace("R$ ",""))])
        if values:
            self.s.delivery.configure_fees(parse_money(values["customer"]),parse_money(values["courier"]),command())

    def settlement(self):
        window=tk.Toplevel(self);window.title("Acerto com entregador");window.geometry("960x600")
        root=View(window,self.s);root.pack(fill="both",expand=True)
        ttk.Label(root,text="Selecione recebimentos e corridas (Ctrl para selecionar vários). Valores são conferidos antes de concluir.").pack(anchor="w")
        panels=ttk.Frame(root);panels.pack(fill="both",expand=True)
        left=ttk.Frame(panels);left.pack(side="left",fill="both",expand=True,padx=(0,8))
        right=ttk.Frame(panels);right.pack(side="left",fill="both",expand=True)
        collections=table(left,["Recebimento","Pedido","Pendente"],height=6);collections.configure(selectmode="extended")
        trips=table(right,["Corrida","Pedido","A pagar"],height=6);trips.configure(selectmode="extended")
        floats=table(root,["Troco transferido","Pendente"],height=3)
        def refresh():
            fill(collections,[(r["id"],(r["id"],r["order_id"],money(r["amount_cents"]-r["settled_cents"]-r["courier_refunded_cents"]))) for r in self.s.settlements.collections_pending()])
            fill(trips,[(r["id"],(r["id"],r["order_id"],money(r["pending_cents"]))) for r in self.s.settlements.trips_pending()])
            fill(floats,[(r["id"],(r["id"],money(r["amount_cents"]-r["returned_cents"]))) for r in self.s.settlements.floats_pending()])
        def settle():
            ids=[int(x) for x in collections.selection()];trip_ids=[int(x) for x in trips.selection()]
            available=sum(r["amount_cents"]-r["settled_cents"]-r["courier_refunded_cents"] for r in self.s.settlements.collections_pending() if r["id"] in ids)
            due=sum(r["pending_cents"] for r in self.s.settlements.trips_pending() if r["id"] in trip_ids)
            values=ask_fields(window,f"Conferir acerto • recebido {money(available)} / corridas {money(due)}",
                [("handed","Dinheiro entregue à gaveta (R$)",money(max(0,available-due)).replace("R$ ","")),
                 ("paid","Dinheiro pago da gaveta (R$)",money(max(0,due-available)).replace("R$ ","")),
                 ("offset","Compensação combinada (R$)",money(min(available,due)).replace("R$ ",""))])
            if values:
                self.s.settlements.settle(ids,trip_ids,parse_money(values["handed"]),parse_money(values["paid"]),parse_money(values["offset"]),self.grant("delivery.settle"),command());refresh()
        def fund():
            values=ask_fields(window,"Enviar troco",[("amount","Valor (R$)",""),("reason","Motivo","Troco para entregas")])
            if values:
                self.s.settlements.fund_courier(parse_money(values["amount"]),self.grant("delivery.float"),values["reason"],command());refresh()
        def return_float():
            id=root.selected(floats);values=ask_fields(window,"Devolver troco",[("amount","Valor devolvido à gaveta (R$)","")])
            if values:
                self.s.settlements.return_float(id,parse_money(values["amount"]),command());refresh()
        actions=ttk.Frame(root);actions.pack(fill="x",pady=6)
        for label,callback in (("Conferir acerto",settle),("Enviar troco",fund),("Receber troco de volta",return_float)):
            ttk.Button(actions,text=label,command=lambda f=callback:root.act(f)).pack(side="left",padx=6)
        refresh()
