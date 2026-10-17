import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from .shared import View,ProductPicker,table,fill,ask_fields,command,FieldSpec
from ..inventory.models import CartLine
from ..delivery.models import DeliveryDraft
from ..common.money import money,parse_money

METHODS={"Dinheiro":"MONEY","Pix":"PIX","Débito":"DEBIT","Crédito":"CREDIT"}
STATES={"PREPARING":"Em preparação","OUT":"Saiu para entrega","DELIVERED":"Entregue","CANCELED":"Cancelado"}


from .delivery_editor import DeliveryEditor


class DeliveryView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        from .assets import load_asset
        self.moto=load_asset(self,'motorcycle.png',24)
        self.motorcycle_label=ttk.Label(self,text='Delivery',image=self.moto,compound='left',style='Title.TLabel')
        self.motorcycle_label.pack(anchor='w')
        self.action_buttons={};self.action_hint=tk.StringVar(value='Selecione um pedido para conferir as próximas ações.')
        row=ttk.Frame(self);row.pack(fill="x",pady=6)
        for label,callback in (("Novo pedido",self.create),("Detalhes",self.details),("Receber",self.receive),("Saiu para entrega",self.dispatch),("Marcar entregue",self.delivered),("Cancelar",self.cancel)):
            button=ttk.Button(row,text=label,style='Primary.TButton' if callback==self.create else 'Danger.TButton' if callback==self.cancel else 'TButton',command=lambda f=callback:self.act(f))
            button.pack(side="left",padx=(0,6));self.action_buttons[callback.__name__]=button
        row=ttk.Frame(self);row.pack(fill="x",pady=(0,6))
        for label,callback in (("Conferir devolução",self.returned),("Reembolsar",self.refund),("Nova tentativa",self.redeliver),("Acertar entregas",self.settlement),("Taxas fixas",self.fees)):
            button=ttk.Button(row,text=label,command=lambda f=callback:self.act(f))
            button.pack(side="left",padx=(0,6));self.action_buttons[callback.__name__]=button
        ttk.Label(self,textvariable=self.action_hint,wraplength=950).pack(anchor='w',pady=4)
        self.summary=ttk.Label(self,text="");self.summary.pack(anchor="w",pady=5)
        self.tree=table(self,["Pedido","Cliente","Situação","Pagamento","Total","Entrega","Entregador"])
        self.tree.bind('<<TreeviewSelect>>',lambda event:self.update_actions())

    def refresh(self):
        rows=[]
        for r in self.s.delivery.list_orders():
            order=self.s.delivery.order(r["id"])
            paid="Pago" if order.paid_cents>=order.total_cents else "Pendente"
            rows.append((r["id"],(r["id"],r["name"],STATES.get(order.state,order.state),paid,money(order.total_cents),money(order.delivery_fee_cents),money(order.courier_fee_cents))))
        fill(self.tree,rows)
        pending=sum(r["pending_cents"] for r in self.s.settlements.trips_pending())
        self.summary.configure(text=f"Dinheiro com entregador: {money(self.s.settlements.pending_custody_cents())} • Corridas a pagar: {money(pending)}")
        self.update_actions()

    def update_actions(self):
        selection=self.tree.selection()
        enabled={name:False for name in ('details','receive','dispatch','delivered','cancel','returned','refund','redeliver')}
        hint='Selecione um pedido para conferir as próximas ações.'
        if selection:
            id=int(selection[0]);order=self.s.delivery.order(id);detail=self.s.delivery_queries.detail(id)
            plan=detail['payment_plan'];paid=order.paid_cents>=order.total_cents
            enabled.update(details=True,receive=order.state!='CANCELED' and not paid,
                dispatch=order.state=='PREPARING',delivered=order.state=='OUT',cancel=order.state!='CANCELED',
                returned=order.state=='CANCELED' and bool(detail['trips']),
                refund=any(r['pending_cents']>0 for r in detail['refunds']),redeliver=order.state=='CANCELED' and order.paid_cents==0)
            hint='Entrega e recebimento são confirmados separadamente.'
            if order.state=='PREPARING' and plan['payment_timing']=='ADVANCE' and not paid:
                enabled['dispatch']=False;hint='Confirme o pagamento antecipado antes de registrar a saída.'
            elif order.state=='PREPARING' and not paid and plan['payment_timing']=='ON_DELIVERY' and (plan['expected_change_cents'] or 0)>self.s.settlements.pending_custody_cents():
                enabled['dispatch']=False;hint='Envie e registre o fundo de troco em Acertar entregas antes da saída.'
        for name,value in enabled.items():
            self.action_buttons[name].configure(state='normal' if value else 'disabled')
        self.action_hint.set(hint)

    def create(self):
        window=tk.Toplevel(self);window.title("Novo pedido de delivery");window.geometry("1100x650")
        editor=DeliveryEditor(window,self.s);editor.pack(fill="both",expand=True)
        return editor

    def details(self):
        id=self.selected(self.tree)
        row=next(r for r in self.s.delivery.list_orders() if r["id"]==id)
        lines=self.s.sales.lines(id)
        messagebox.showinfo(f"Pedido #{id}",f'{row["name"]}\n{row["phone"]}\n{row["address"]}\nReferência: {row["reference"]}\n\n'+
            "\n".join(f'{line["qty"]} × {line["name"]}' for line in lines),parent=self)

    def receive(self):
        from .delivery_receipt import DeliveryReceiptDialog
        return DeliveryReceiptDialog(self,self.s,self.selected(self.tree)).show()

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
        detail=self.s.delivery_queries.detail(id);plan=detail['payment_plan'];cmd=command()
        explicit=plan['payment_timing']!='UNSPECIFIED'
        text='Criar novo pedido vinculado, com preços e taxas atuais?\n'+('A nova tentativa ficará em preparação para conferir pagamento e troco.' if explicit else 'Será registrada uma nova saída.')+'\nA corrida anterior permanece devida.'
        if not messagebox.askyesno('Nova tentativa',text,parent=self):return
        def submit(values=None):
            kwargs={}
            if values is not None:kwargs['new_change_for_cents']=parse_money(values['change']) if values['needed']=='Sim' else 0
            result=self.s.delivery.redeliver(id,self.grant('delivery.redeliver'),self.reason(),cmd,**kwargs)
            self.s.application.notify(f'Nova tentativa #{result} registrada.'+(' Confira o pagamento e registre a saída quando estiver pronta.' if explicit else ''))
            return result
        if explicit and plan['method']=='MONEY':
            return ask_fields(self,'Troco da nova tentativa',[
                FieldSpec('needed','Precisa de troco?','Sim' if plan['change_for_cents'] else 'Não',kind='choice',choices=('Não','Sim')),
                FieldSpec('change','Troco para quanto? (R$)',money(plan['change_for_cents'] or 0).replace('R$ ',''))],on_submit=submit)
        return submit()

    def fees(self):
        settings=self.s.delivery.settings()
        values=ask_fields(self,"Valores fixos por entrega",[("customer","Taxa cobrada do cliente (R$)",money(settings["customer_fee_cents"]).replace("R$ ","")),("courier","Valor pago ao entregador (R$)",money(settings["courier_fee_cents"]).replace("R$ ",""))])
        if values:
            self.s.delivery.configure_fees(parse_money(values["customer"]),parse_money(values["courier"]),command())

    def settlement(self):
        from .settlement import SettlementView
        window=tk.Toplevel(self);window.title('Acerto com entregador');window.geometry('1180x650')
        view=SettlementView(window,self.s);view.pack(fill='both',expand=True)
        return view
