import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from datetime import date,datetime
from .shared import View,table,fill,ask_fields,command
from ..common.money import money,parse_money
from ..finance.models import ExpenseDraft,ExpenseFilter
from ..finance.queries import month_range
from ..finance.service import DuplicateExpenseError


from .period import PeriodFilter,PeriodSelection,parse_date as date_input
from .forms import FieldSpec
from ..common.errors import BusinessError


class FinanceView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Contas e despesas',style='Title.TLabel').pack(anchor='w')
        self.month=tk.StringVar(value=self.s.clock.today().strftime('%Y-%m'))
        self.basis=tk.StringVar(value='Data do gasto');self.category=tk.StringVar();self.text=tk.StringVar();self.status=tk.StringVar(value='Todas')
        self.include_deleted=tk.BooleanVar(value=False)
        self.period=PeriodFilter(self,self.s.clock,'THIS_MONTH',self.apply_filters,self.clear_extra)
        self.period.pack(fill='x',pady=4);self.start=self.period.start;self.end=self.period.end
        row=ttk.Frame(self);row.pack(fill='x',pady=4)
        ttk.Label(row,text='Consultar por').pack(side='left',padx=(0,6))
        ttk.Combobox(row,textvariable=self.basis,values=('Data do gasto','Vencimento','Pagamento'),width=17,state='readonly').pack(side='left')
        ttk.Label(row,text='Gasto: quando ocorreu · Vencimento: prazo · Pagamento: quando foi pago.',wraplength=650).pack(side='left',padx=12)
        row=ttk.Frame(self);row.pack(fill='x',pady=4)
        for label,var,width in (('Categoria',self.category,16),('Descrição',self.text,22)):
            ttk.Label(row,text=label).pack(side='left');ttk.Entry(row,textvariable=var,width=width).pack(side='left',padx=6)
        ttk.Combobox(row,textvariable=self.status,values=('Todas','Paga','Pendente','Vencida'),state='readonly',width=12).pack(side='left')
        ttk.Checkbutton(row,text='Mostrar excluídas',variable=self.include_deleted).pack(side='left',padx=8)
        self.summary=ttk.Label(self,text='',wraplength=950);self.summary.pack(anchor='w',pady=5)
        row=ttk.Frame(self);row.pack(side='bottom',fill='x',pady=8)
        for label,callback in (('Nova despesa',self.create),('Editar',self.edit),('Quitar',self.pay),('Pagamentos',self.payments),('Excluir',self.delete),('Contas mensais',self.recurring)):
            ttk.Button(row,text=label,style='Primary.TButton' if callback==self.create else 'Danger.TButton' if callback==self.delete else 'TButton',command=lambda f=callback:self.act(f)).pack(side='left',padx=(0,8))
        self.tree=table(self,['ID','Descrição','Categoria','Valor','Data gasto','Vencimento','Pago em','Situação'])
        for tag,color in (('PAID','#176a37'),('PENDING','#565f68'),('OVERDUE','#ad2727')):self.tree.tag_configure(tag,foreground=color)
        self.rows={};self._applied_filters=self.candidate(self.period.applied);self.refresh()

    def clear_extra(self):
        self.basis.set('Data do gasto');self.category.set('');self.text.set('');self.status.set('Todas');self.include_deleted.set(False)

    def candidate(self,period):
        return ExpenseFilter(period.start,period.end,{'Data do gasto':'incurred','Gasto':'incurred','Vencimento':'due','Pagamento':'payment'}[self.basis.get()],
            self.category.get().strip() or None,self.text.get(),{'Todas':None,'Paga':'PAID','Pendente':'PENDING','Vencida':'OVERDUE'}[self.status.get()],self.include_deleted.get())

    def apply_filters(self,period):
        candidate=self.candidate(period)
        rows=self.s.finance.list_expenses(candidate);totals=self.s.finance.expense_totals(candidate)
        self._applied_filters=candidate;self.render(rows,totals)

    def apply_month(self):
        start,end=month_range(self.month.get())
        self.start.set(start.strftime('%d/%m/%Y'));self.end.set(end.strftime('%d/%m/%Y'));return self.period.apply()

    def filters(self):return self._applied_filters

    def refresh(self):
        filters=self.filters();self.render(self.s.finance.list_expenses(filters),self.s.finance.expense_totals(filters))

    def render(self,rows,totals):
        self.rows={r.id:r for r in rows};labels={'PAID':'Paga','PENDING':'Pendente','OVERDUE':'Vencida'}
        fill(self.tree,[(r.id,(r.id,r.draft.description,r.draft.category,money(r.draft.amount_cents),r.draft.incurred_on.strftime('%d/%m/%Y'),r.due_on.strftime('%d/%m/%Y'),r.paid_on.strftime('%d/%m/%Y') if r.paid_on else '—','Excluída' if r.deleted_at else labels[r.status])) for r in rows])
        for r in rows:self.tree.item(str(r.id),tags=(r.status,))
        paid_label='Pago/abatido no período' if self.filters().date_basis=='payment' else 'Pago/abatido acumulado das contas'
        self.summary.configure(text=f'{paid_label}: {money(totals.paid_cents)}    Saldo pendente atual: {money(totals.pending_cents)}    Vencido (incluído no pendente): {money(totals.overdue_cents)}    Compromissos: {money(totals.commitments_cents)}')

    def form(self,initial=None,on_submit=None):
        today=self.s.clock.today();initial=initial or ExpenseDraft('','Outras despesas',0,today,today)
        def submit(values):
            draft=ExpenseDraft(values['description'],values['category'],parse_money(values['amount']),date_input(values['incurred']),date_input(values['due']))
            return on_submit(draft) if on_submit else draft
        return ask_fields(self,'Despesa',[
            FieldSpec('description','Descrição',initial.description,required=True),FieldSpec('category','Categoria',initial.category,required=True),
            FieldSpec('amount','Valor (R$)',money(initial.amount_cents).replace('R$ ',''),required=True,validator=parse_money),
            FieldSpec('incurred','Data do gasto (DD/MM/AAAA)',initial.incurred_on.strftime('%d/%m/%Y'),validator=date_input),
            FieldSpec('due','Vencimento (DD/MM/AAAA)',initial.due_on.strftime('%d/%m/%Y'),validator=date_input)],on_submit=submit)

    def create(self):
        cmd=command()
        def submit(draft):
            try:result=self.s.finance.add_expense(draft,False,cmd)
            except DuplicateExpenseError as error:
                if not messagebox.askyesno('Possível duplicidade',f'Lançamentos semelhantes: {error.candidate_ids}. Registrar mesmo assim?',parent=self):raise BusinessError('Cadastro não confirmado. Revise a despesa.')
                result=self.s.finance.add_expense(draft,True,cmd)
            self.s.application.notify('Despesa registrada.');return result
        return self.form(on_submit=submit)

    def edit(self):
        id=self.selected(self.tree);cmd=command()
        def submit(draft):
            grant=self.grant('expense.edit');reason=self.reason()
            try:return self.s.finance.edit_expense(id,draft,False,grant,reason,cmd)
            except DuplicateExpenseError as error:
                if not messagebox.askyesno('Possível duplicidade',f'Semelhantes: {error.candidate_ids}. Confirmar?',parent=self):raise BusinessError('Edição não confirmada. Revise os dados.')
                return self.s.finance.edit_expense(id,draft,True,grant,reason,cmd)
        return self.form(self.rows[id].draft,on_submit=submit)

    def delete(self):
        id=self.selected(self.tree)
        if messagebox.askyesno("Excluir lançamento","Retirar dos cálculos ativos, preservando histórico?\nIsso não devolve dinheiro à gaveta.",parent=self):
            self.s.finance.delete_expense(id,self.grant("expense.delete"),self.reason(),command())

    def pay(self):
        id=self.selected(self.tree);row=self.rows[id];pending=row.draft.amount_cents-row.paid_cents;cmd=command()
        def submit(values):
            method={'Dinheiro':'MONEY','Pix':'PIX','Débito':'DEBIT','Crédito à vista':'CREDIT'}[values['method']]
            drawer=values['drawer']=='Sim'
            return self.s.finance.pay_obligation(id,pending,date_input(values['date']),method,drawer,self.grant('cash.withdraw') if drawer else None,cmd)
        return ask_fields(self,'Quitar obrigação · '+money(pending),[
            FieldSpec('date','Pago em (DD/MM/AAAA)',self.s.clock.today().strftime('%d/%m/%Y'),validator=date_input),
            FieldSpec('method','Forma de pagamento','Pix',kind='choice',choices=('Dinheiro','Pix','Débito','Crédito à vista')),
            FieldSpec('drawer','Dinheiro saiu da gaveta?','Não',kind='choice',choices=('Não','Sim'))],on_submit=submit)

    def recurring(self):
        from .recurrence import RecurrenceView
        window=tk.Toplevel(self);window.title('Contas mensais');window.geometry('900x500')
        view=RecurrenceView(window,self.s);view.pack(fill='both',expand=True)
        return view

    def payments(self):
        id=self.selected(self.tree)
        window=tk.Toplevel(self);window.title('Pagamentos da obrigação');window.geometry('820x400')
        root=View(window,self.s);root.pack(fill='both',expand=True)
        tree=table(root,['ID','Data','Modalidade','Valor','Origem','Situação'],height=7)
        methods={'MONEY':'Dinheiro','PIX':'Pix','DEBIT':'Débito','CREDIT':'Crédito','SUPPLIER_CREDIT':'Crédito do fornecedor'}
        def refresh():
            fill(tree,[(p['id'],(p['id'],date.fromisoformat(p['paid_on']).strftime('%d/%m/%Y'),methods[p['method']],money(p['amount_cents']),'Gaveta' if p['from_drawer'] else 'Fora da gaveta','Anulado' if p['corrected'] else 'Confirmado')) for p in self.s.finance.payment_history(id)])
        def edit():
            pid=root.selected(tree);p=next(p for p in self.s.finance.payment_history(id) if p['id']==pid);cmd=command()
            if p['method']=='SUPPLIER_CREDIT':raise BusinessError('Abatimento vinculado ao crédito do fornecedor; consulte Compras e devoluções.')
            def submit(values):
                method=next((key for key,value in methods.items() if value==values['method']),None)
                result=self.s.finance.edit_payment_details(pid,date_input(values['date']),method,self.grant('payment.edit'),self.reason(),cmd);refresh();return result
            return ask_fields(window,'Corrigir dados sem movimentar dinheiro',[
                FieldSpec('date','Pago em (DD/MM/AAAA)',date.fromisoformat(p['paid_on']).strftime('%d/%m/%Y'),validator=date_input),
                FieldSpec('method','Modalidade',methods[p['method']],kind='choice',choices=('Dinheiro','Pix','Débito','Crédito'))],on_submit=submit)
        def void():
            pid=root.selected(tree);cmd=command()
            def submit(values):
                result=self.s.finance.correct_payment(pid,'VOID',parse_money(values['return']),self.grant('payment.correct'),self.reason(),cmd);refresh();return result
            return ask_fields(window,'Anular registro do pagamento',[FieldSpec('return','Dinheiro realmente devolvido à gaveta (R$)','0,00',validator=parse_money)],on_submit=submit)
        row=ttk.Frame(root);row.pack(fill='x')
        for label,callback in (('Corrigir data/modalidade',edit),('Anular pagamento',void)):
            ttk.Button(row,text=label,command=lambda f=callback:root.act(f)).pack(side='left',padx=6)
        root.payments_tree=tree
        refresh()
        return root
