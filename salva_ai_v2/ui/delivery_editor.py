import tkinter as tk
from tkinter import ttk
from .shared import View,ProductPicker,table,fill,command
from .payment import METHODS
from ..common.errors import BusinessError
from ..common.money import money,parse_money
from ..inventory.models import CartLine
from ..delivery.models import DeliveryDraft


class DeliveryEditor(View,ProductPicker):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        self.lines={};self.fields={};self.command_id=command()
        self.error=tk.StringVar();self.change_summary=tk.StringVar()
        ttk.Label(self,text='Novo pedido de delivery',style='Title.TLabel').pack(anchor='w',pady=(0,8))
        panels=ttk.Panedwindow(self,orient='horizontal');panels.pack(fill='both',expand=True)
        customer=ttk.Frame(panels,padding=(0,0,16,0));items=ttk.Frame(panels,padding=(12,0,0,0))
        panels.add(customer,weight=4);panels.add(items,weight=6);customer.columnconfigure(0,weight=1)
        for i,(key,label) in enumerate((('customer','Cliente *'),('phone','Telefone *'),('address','Endereço *'),('complement','Complemento (opcional)'),('reference','Ponto de referência'))):
            ttk.Label(customer,text=label).grid(row=i*2,column=0,sticky='w',pady=(3,2))
            entry=ttk.Entry(customer,width=34);entry.grid(row=i*2+1,column=0,sticky='ew',pady=(0,3));self.fields[key]=entry
        entries=list(self.fields.values())
        for index,entry in enumerate(entries):
            entry.bind('<Return>',lambda event,i=index:self.advance_customer(i))
        self.timing=tk.StringVar(value='Na entrega');self.channel=tk.StringVar(value='Dinheiro')
        self.method=tk.StringVar(value='Crédito à vista');self.change_needed=tk.StringVar(value='Não')
        self.timing_input=self.choice(customer,10,'Quando o cliente vai pagar?',self.timing,('Antecipado','Na entrega'))
        self.channel_input=self.choice(customer,12,'Forma combinada',self.channel,tuple(METHODS))
        self.method_label=ttk.Label(customer,text='Modalidade do link (conforme comprovante)')
        self.method_label.grid(row=14,column=0,sticky='w',pady=(5,2))
        self.method_input=ttk.Combobox(customer,textvariable=self.method,state='readonly',values=('Débito','Crédito à vista'))
        self.method_input.grid(row=15,column=0,sticky='ew')
        self.link_label=ttk.Label(customer,text='Link / referência (opcional)');self.link_label.grid(row=16,column=0,sticky='w')
        self.link_reference=ttk.Entry(customer);self.link_reference.grid(row=17,column=0,sticky='ew')
        self.change_input=self.choice(customer,18,'Precisa de troco?',self.change_needed,('Não','Sim'))
        self.change_label=customer.grid_slaves(row=18)[0]
        self.change_for_label=ttk.Label(customer,text='Troco para quanto? (R$)')
        self.change_for_label.grid(row=20,column=0,sticky='w',pady=(4,2))
        self.change_for=ttk.Entry(customer);self.change_for.grid(row=21,column=0,sticky='ew')
        ttk.Label(customer,textvariable=self.change_summary,wraplength=340).grid(row=22,column=0,sticky='w',pady=8)
        self.change_for.bind('<KeyRelease>',lambda event:self.refresh())
        self.change_for.bind('<Return>',lambda event:self.to_picker())
        self.build_picker(items,self.add)
        actions=ttk.Frame(items);actions.pack(side='bottom',fill='x',pady=8)
        ttk.Button(actions,text='Confirmar pedido',style='Primary.TButton',command=self.submit).pack(side='right')
        ttk.Button(actions,text='Remover item',command=lambda:self.act(self.remove)).pack(side='left')
        self.summary=ttk.Label(items,text='',wraplength=570,style='Title.TLabel');self.summary.pack(side='bottom',anchor='w',pady=8)
        ttk.Label(items,textvariable=self.error,foreground='#a52525',wraplength=550).pack(side='bottom',anchor='w')
        self.tree=table(items,['Produto','Quantidade','Total'],height=8)
        self.tree.column('Produto',width=290,anchor='w');self.tree.column('Quantidade',width=90);self.tree.column('Total',width=100)
        self.timing_input.bind('<<ComboboxSelected>>',lambda event:self.update_payment())
        self.channel_input.bind('<<ComboboxSelected>>',lambda event:self.update_payment())
        self.change_input.bind('<<ComboboxSelected>>',lambda event:self.update_payment())
        self.timing_input.bind('<Return>',lambda event:self.focus_and_break(self.channel_input))
        self.channel_input.bind('<Return>',lambda event:self.focus_and_break(self.method_input if self.channel.get()=='Link de pagamento' else self.change_input if self.channel.get()=='Dinheiro' else self.picker))
        self.method_input.bind('<Return>',lambda event:self.focus_and_break(self.link_reference))
        self.link_reference.bind('<Return>',lambda event:self.to_picker())
        self.change_input.bind('<Return>',lambda event:self.focus_and_break(self.change_for if self.change_needed.get()=='Sim' else self.picker))
        self.update_payment();self.refresh()
        self.s.application.shortcuts.register(parent,self)

    def choice(self,parent,row,label,variable,choices):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=(5,2))
        widget=ttk.Combobox(parent,textvariable=variable,values=choices,state='readonly')
        widget.grid(row=row+1,column=0,sticky='ew')
        return widget

    def focus_and_break(self,widget):
        widget.focus_set();return 'break'

    def advance_customer(self,index):
        entry=list(self.fields.values())[index]
        if index<3 and not entry.get().strip():
            self.error.set('Preencha cliente, telefone e endereço.');return 'break'
        next_widget=list(self.fields.values())[index+1] if index+1<len(self.fields) else self.timing_input
        return self.focus_and_break(next_widget)

    def to_picker(self):
        try:
            if self.channel.get()=='Dinheiro' and self.change_needed.get()=='Sim':parse_money(self.change_for.get())
        except BusinessError as error:
            self.error.set(str(error));return 'break'
        return self.focus_and_break(self.picker)

    def update_payment(self):
        choices=('Pix','Link de pagamento') if self.timing.get()=='Antecipado' else tuple(METHODS)
        self.channel_input.configure(values=choices)
        if self.channel.get() not in choices:self.channel.set(choices[0])
        cash=self.channel.get()=='Dinheiro';link=self.channel.get()=='Link de pagamento'
        self.change_input.configure(state='readonly' if cash else 'disabled')
        if not cash:self.change_needed.set('Não')
        for widget in (self.change_label,self.change_input,self.change_for_label,self.change_for):
            if cash:widget.grid()
            else:widget.grid_remove()
        enabled=cash and self.change_needed.get()=='Sim'
        self.change_for.configure(state='normal')
        if not enabled:self.change_for.delete(0,'end');self.change_for.configure(state='disabled')
        for widget in (self.method_label,self.method_input,self.link_label,self.link_reference):
            if link:widget.grid()
            else:widget.grid_remove()
        if not link:self.link_reference.delete(0,'end')
        self.refresh()

    def act(self,func):
        try:
            result=func();self.error.set('');return result
        except (BusinessError,ValueError) as error:
            self.error.set(str(error));return False

    def add(self):
        pid=self.selected_product();qty=int(self.qty.get())
        if qty<1:raise BusinessError('Quantidade deve ser positiva.')
        self.lines[pid]=self.lines.get(pid,0)+qty;self.refresh()

    def remove(self):
        self.lines.pop(self.selected(self.tree),None);self.refresh()

    def refresh(self):
        self.filter_products();products={p['id']:p for p in self.s.inventory.products()}
        rows=[];subtotal=0
        for pid,qty in self.lines.items():
            amount=self.s.pricing.quote(self.s.pricing.snapshot(pid),qty).total_cents
            rows.append((pid,(products[pid]['name'],qty,money(amount))));subtotal+=amount
        fill(self.tree,rows)
        fee=self.s.delivery.settings()['customer_fee_cents'];self.total_cents=subtotal+fee
        self.summary.configure(text=f'Total: {money(self.total_cents)}\nProdutos: {money(subtotal)} · Entrega: {money(fee)}')
        if self.channel.get()=='Dinheiro' and self.change_needed.get()=='Sim':
            try:
                value=parse_money(self.change_for.get())
                self.change_summary.set('Troco previsto: '+money(value-self.total_cents) if value>self.total_cents else 'Troco para deve ser maior que o total.')
            except BusinessError:self.change_summary.set('Informe o valor combinado com o cliente.')
        else:self.change_summary.set('Sem troco previsto.' if self.channel.get()=='Dinheiro' else 'Recebimento digital deve ser confirmado pelo bar.')

    def draft(self):
        values={key:entry.get().strip() for key,entry in self.fields.items()}
        link=self.channel.get()=='Link de pagamento'
        method=METHODS.get(self.method.get() if link else self.channel.get())
        if not method:raise BusinessError('Escolha a forma de pagamento.')
        forecast=parse_money(self.change_for.get()) if method=='MONEY' and self.change_needed.get()=='Sim' else None
        return DeliveryDraft(values['customer'],values['phone'],values['address'],values['reference'],
            [CartLine(pid,qty) for pid,qty in self.lines.items()],method,'COURIER' if method=='MONEY' else 'BAR',
            'ADVANCE' if self.timing.get()=='Antecipado' else 'ON_DELIVERY','LINK' if link else method,forecast,self.link_reference.get().strip() if link else '',values['complement'])

    def submit(self):
        def perform():
            order=self.s.delivery.confirm(self.draft(),self.command_id)
            self.s.application.notify(f'Pedido #{order.id} confirmado. Total: {money(order.total_cents)}')
            self.s.application.refresh();self.master.destroy();return order
        return self.act(perform)
