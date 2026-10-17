from tkinter import ttk,messagebox
from .shared import View,table,fill,ask_fields,FieldSpec,command
from .period import MonthSelector
from ..common.money import money,parse_money
from ..common.errors import BusinessError
from ..finance.models import ExpenseDraft


def valid_day(value):
    day=int(value)
    if not 1<=day<=31:raise BusinessError('Escolha um dia de 1 a 31. Meses curtos usam seu último dia.')
    return day


class RecurrenceView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Contas mensais',style='Title.TLabel').pack(anchor='w')
        self.selector=MonthSelector(self,self.s.clock,lambda month:None);self.selector.pack(fill='x')
        ttk.Label(self,text='Gerar cria uma conta pendente no mês consultado. Não registra pagamento. Edições afetam apenas ocorrências futuras ainda não geradas.',wraplength=820).pack(anchor='w',pady=6)
        row=ttk.Frame(self);row.pack(fill='x')
        for label,callback in (('Nova regra',self.create),('Editar futuras',self.edit),('Gerar mês consultado',self.generate)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side='left',padx=(0,8))
        self.tree=table(self,['ID','Descrição','Categoria','Valor','Dia','Ativa'])
        self.refresh()

    def refresh(self):
        fill(self.tree,[(r['id'],(r['id'],r['description'],r['category'],money(r['amount_cents']),r['due_day'],'Sim' if r['active'] else 'Não')) for r in self.s.recurrence.list_rules()])

    def form(self,rule=None):
        cmd=command();rule=rule or {}
        def submit(values):
            today=self.s.clock.today()
            draft=ExpenseDraft(values['description'],values['category'],parse_money(values['amount']),today,today)
            day=valid_day(values['day'])
            if rule:
                result=self.s.recurrence.update_rule(rule['id'],draft,day,values['active']=='Sim',self.grant('recurrence.edit'),self.reason(),cmd)
            else:result=self.s.recurrence.create_rule(draft,day,self.selector.applied,cmd)
            self.refresh();return result
        fields=[FieldSpec('description','Descrição',rule.get('description',''),required=True),FieldSpec('category','Categoria',rule.get('category','Outras despesas'),required=True),
            FieldSpec('amount','Valor previsto (R$)',money(rule.get('amount_cents',0)).replace('R$ ',''),validator=parse_money),
            FieldSpec('day','Dia do vencimento (1 a 31)',rule.get('due_day',1),validator=valid_day)]
        if rule:fields.append(FieldSpec('active','Regra ativa?','Sim' if rule['active'] else 'Não',kind='choice',choices=('Sim','Não')))
        return ask_fields(self,'Editar regra futura' if rule else 'Nova conta mensal',fields,on_submit=submit)

    def create(self):return self.form()

    def edit(self):
        id=self.selected(self.tree);return self.form(next(r for r in self.s.recurrence.list_rules() if r['id']==id))

    def generate(self):
        id=self.selected(self.tree);month=self.selector.applied
        if not messagebox.askyesno('Gerar previsão',f'Gerar conta pendente para {month}? Confira o valor antes de pagar.',parent=self):return
        result=self.s.recurrence.generate(id,month,command());self.s.application.refresh();self.s.application.notify(f'Conta #{result} gerada, ainda pendente.');return result
