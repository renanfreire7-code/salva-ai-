import tkinter as tk
from tkinter import ttk
from .shared import View,table,fill,ask_fields,FieldSpec,command
from .order_details import OrderDetails,read_text,set_text,delivery_text
from ..common.money import money,parse_money
from ..common.errors import BusinessError


class SettlementView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        self.selected_collections=set();self.selected_trips=set();self.orders={}
        ttk.Label(self,text='Acerto com entregador',style='Title.TLabel').pack(anchor='w')
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True,pady=8)
        current=ttk.Frame(tabs);records=ttk.Frame(tabs)
        tabs.add(current,text='Conferir pendências');tabs.add(records,text='Acertos anteriores')
        ttk.Label(current,text='Selecione o pedido e marque recebimento e/ou corrida. Duplo clique inclui ou retira ambos. Não é necessário usar Ctrl.',wraplength=1050).pack(anchor='w')
        row=ttk.Frame(current);row.pack(fill='x',pady=6)
        self.collection_checked=tk.BooleanVar();self.trip_checked=tk.BooleanVar()
        self.collection_check=ttk.Checkbutton(row,text='Incluir recebimento',variable=self.collection_checked,command=self.toggle_selected)
        self.collection_check.pack(side='left',padx=4)
        self.trip_check=ttk.Checkbutton(row,text='Incluir corrida',variable=self.trip_checked,command=self.toggle_selected)
        self.trip_check.pack(side='left',padx=4)
        ttk.Button(row,text='Selecionar todos',command=self.select_all).pack(side='left',padx=12)
        ttk.Button(row,text='Limpar seleção',command=self.clear_selection).pack(side='left')
        self.summary=tk.StringVar()
        footer=ttk.Frame(current);footer.pack(side='bottom',fill='x',pady=4)
        ttk.Label(footer,textvariable=self.summary,wraplength=760).pack(side='left')
        ttk.Button(footer,text='Conferir acerto',style='Primary.TButton',command=lambda:self.act(self.settle)).pack(side='right')
        panels=ttk.Panedwindow(current,orient='horizontal');panels.pack(fill='both',expand=True)
        listing=ttk.Frame(panels);self.details=OrderDetails(panels,self.s)
        panels.add(listing,weight=5);panels.add(self.details,weight=5)
        self.tree=table(listing,['Pedido','Cliente','Total','A entregar','Corridas','Incluído'],height=6)
        for column in self.tree['columns']:self.tree.column(column,width=85,anchor='w' if column in ('Cliente','Incluído') else 'e')
        self.tree.bind('<<TreeviewSelect>>',lambda event:self.show_selected())
        self.tree.bind('<Double-1>',lambda event:self.toggle_current())
        fund=ttk.Frame(listing);fund.pack(fill='x',pady=4)
        ttk.Button(fund,text='Enviar troco',command=lambda:self.act(self.fund)).pack(side='left',padx=(0,8))
        ttk.Button(fund,text='Receber troco devolvido',command=lambda:self.act(self.return_float)).pack(side='left')
        self.floats_tree=table(listing,['Fundo','Enviado','Pendente'],height=2)
        self.records_tree=table(records,['Acerto','Data','Entregue à gaveta','Pago da gaveta','Compensado'],height=4)
        self.records_tree.bind('<<TreeviewSelect>>',lambda event:self.show_record())
        self.record_text=read_text(records,height=10)
        self.refresh()

    def refresh(self):
        self.orders={r['order_id']:r for r in self.s.delivery_queries.settlement_orders()}
        collection_ids={id for row in self.orders.values() for id in row['collection_ids']}
        trip_ids={id for row in self.orders.values() for id in row['trip_ids']}
        self.selected_collections.intersection_update(collection_ids);self.selected_trips.intersection_update(trip_ids)
        self.render()
        fill(self.floats_tree,[(r['id'],(r['id'],money(r['amount_cents']),money(r['amount_cents']-r['returned_cents']))) for r in self.s.settlements.floats_pending()])
        fill(self.records_tree,[(r['id'],(r['id'],r['occurred_at'],money(r['handed_in_cents']),money(r['paid_out_cents']),money(r['offset_cents']))) for r in self.s.delivery_queries.settlements()])

    def render(self):
        def included(row):
            labels=[]
            if set(row['collection_ids'])&self.selected_collections:labels.append('Recebimento')
            if set(row['trip_ids'])&self.selected_trips:labels.append('Corrida')
            return ' + '.join(labels) or 'Não'
        fill(self.tree,[(id,(id,r['customer'],money(r['total_cents']),money(r['custody_pending_cents']),money(r['trip_pending_cents']),included(r))) for id,r in self.orders.items()])
        amount,due=self.selection_totals()
        self.summary.set(f'Selecionado: recebimentos {money(amount)} · corridas {money(due)}\nFundo de troco ainda a devolver: '+money(sum(r['amount_cents']-r['returned_cents'] for r in self.s.settlements.floats_pending())))
        self.show_selected()

    def toggle_order(self,order_id,selected):
        row=self.orders[order_id]
        operation='update' if selected else 'difference_update'
        getattr(self.selected_collections,operation)(row['collection_ids'])
        getattr(self.selected_trips,operation)(row['trip_ids'])
        self.render()

    def toggle_current(self):
        selection=self.tree.selection()
        if selection:
            id=int(selection[0]);row=self.orders[id]
            included=bool(set(row['collection_ids'])&self.selected_collections or set(row['trip_ids'])&self.selected_trips)
            self.toggle_order(id,not included)

    def toggle_selected(self):
        selection=self.tree.selection()
        if selection:
            row=self.orders[int(selection[0])]
            for variable,selected,ids in ((self.collection_checked,self.selected_collections,row['collection_ids']),(self.trip_checked,self.selected_trips,row['trip_ids'])):
                if variable.get():selected.update(ids)
                else:selected.difference_update(ids)
            self.render()

    def show_selected(self):
        selection=self.tree.selection()
        if selection and int(selection[0]) in self.orders:
            row=self.orders[int(selection[0])];self.details.show(f"delivery:{row['order_id']}")
            self.collection_checked.set(bool(set(row['collection_ids'])&self.selected_collections));self.trip_checked.set(bool(set(row['trip_ids'])&self.selected_trips))
            self.collection_check.configure(state='normal' if row['collection_ids'] else 'disabled')
            self.trip_check.configure(state='normal' if row['trip_ids'] else 'disabled')
        else:
            self.details.show(None);self.collection_checked.set(False);self.trip_checked.set(False)
            self.collection_check.configure(state='disabled');self.trip_check.configure(state='disabled')

    def select_all(self):
        self.selected_collections={id for row in self.orders.values() for id in row['collection_ids']}
        self.selected_trips={id for row in self.orders.values() for id in row['trip_ids']};self.render()

    def clear_selection(self):
        self.selected_collections.clear();self.selected_trips.clear();self.render()

    def selection_totals(self):
        amount=sum(r['amount_cents']-r['settled_cents']-r['courier_refunded_cents'] for r in self.s.settlements.collections_pending() if r['id'] in self.selected_collections)
        due=sum(r['pending_cents'] for r in self.s.settlements.trips_pending() if r['id'] in self.selected_trips)
        return amount,due

    def settle(self):
        amount,due=self.selection_totals();cmd=command()
        if not (amount or due):raise BusinessError('Selecione os recebimentos ou corridas a conferir.')
        def submit(values):
            result=self.s.settlements.settle(sorted(self.selected_collections),sorted(self.selected_trips),parse_money(values['handed']),parse_money(values['paid']),parse_money(values['offset']),self.grant('delivery.settle'),cmd)
            self.clear_selection();self.refresh();self.s.application.notify(f'Acerto #{result.id} registrado. Consulte Acertos anteriores para conferir.');return result
        return ask_fields(self,'Confirmar os valores físicos e a compensação',[
            FieldSpec('handed','Dinheiro entregue à gaveta (R$)',money(max(0,amount-due)).replace('R$ ',''),validator=parse_money),
            FieldSpec('paid','Dinheiro pago da gaveta (R$)',money(max(0,due-amount)).replace('R$ ',''),validator=parse_money),
            FieldSpec('offset','Compensação combinada (R$)',money(min(amount,due)).replace('R$ ',''),validator=parse_money)],on_submit=submit)

    def fund(self):
        cmd=command()
        def submit(values):
            result=self.s.settlements.fund_courier(parse_money(values['amount']),self.grant('delivery.float'),values['reason'],cmd);self.refresh();return result
        return ask_fields(self,'Enviar fundo de troco',[FieldSpec('amount','Valor (R$)',required=True,validator=parse_money),FieldSpec('reason','Motivo','Troco para entregas',required=True)],on_submit=submit)

    def return_float(self):
        id=self.selected(self.floats_tree);cmd=command()
        def submit(values):
            result=self.s.settlements.return_float(id,parse_money(values['amount']),cmd);self.refresh();return result
        return ask_fields(self,'Receber fundo de troco devolvido',[FieldSpec('amount','Valor devolvido à gaveta (R$)',required=True,validator=parse_money)],on_submit=submit)

    def show_record(self):
        selection=self.records_tree.selection()
        if not selection:set_text(self.record_text,'Selecione um acerto para conferir.');return
        record=self.s.delivery_queries.settlement_detail(int(selection[0]))
        text=f"Acerto #{record['id']} · {record['occurred_at']}\nEntregue à gaveta: {money(record['handed_in_cents'])}\nPago da gaveta: {money(record['paid_out_cents'])}\nCompensação: {money(record['offset_cents'])}\n"
        order_ids=set()
        for item in record['items']:
            text+=f"\n{'Recebimento' if item['source_type']=='COLLECTION' else 'Corrida'} #{item['source_id']} · Pedido #{item['order_id']} · parcela {money(item['amount_cents'])}"
            if item['order_id'] is not None:order_ids.add(item['order_id'])
        for id in sorted(order_ids):text+='\n\n'+delivery_text(self.s.delivery_queries.detail(id))
        set_text(self.record_text,text)
