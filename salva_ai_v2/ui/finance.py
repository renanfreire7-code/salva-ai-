import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from datetime import date,datetime
from .shared import View,table,fill,ask_fields,command
from ..common.money import money,parse_money
from ..finance.models import ExpenseDraft,ExpenseFilter
from ..finance.queries import month_range
from ..finance.service import DuplicateExpenseError


def date_input(text):
    try:
        return datetime.strptime(text,"%d/%m/%Y").date()
    except ValueError:
        return date.fromisoformat(text)


class FinanceView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Financeiro mensal",style="Title.TLabel").pack(anchor="w")
        row=ttk.Frame(self);row.pack(fill="x",pady=8)
        self.month=tk.StringVar(value=self.s.clock.today().strftime("%Y-%m"))
        self.start=tk.StringVar();self.end=tk.StringVar()
        self.basis=tk.StringVar(value="Gasto");self.category=tk.StringVar();self.text=tk.StringVar();self.status=tk.StringVar(value="Todas")
        for label,var,width in (("Mês",self.month,8),("De",self.start,10),("Até",self.end,10)):
            ttk.Label(row,text=label).pack(side="left",padx=(0,4))
            ttk.Entry(row,textvariable=var,width=width).pack(side="left",padx=(0,8))
        ttk.Combobox(row,textvariable=self.basis,values=["Gasto","Vencimento","Pagamento"],width=12,state="readonly").pack(side="left")
        ttk.Button(row,text="Usar mês",command=lambda:self.act(self.apply_month)).pack(side="left",padx=6)
        ttk.Button(row,text="Filtrar",command=lambda:self.act(self.refresh)).pack(side="left")
        row=ttk.Frame(self);row.pack(fill="x",pady=(0,6))
        for label,var,width in (("Categoria",self.category,18),("Descrição",self.text,25)):
            ttk.Label(row,text=label).pack(side="left",padx=(0,4));ttk.Entry(row,textvariable=var,width=width).pack(side="left",padx=(0,10))
        ttk.Combobox(row,textvariable=self.status,values=["Todas","Paga","Pendente","Vencida"],state="readonly",width=12).pack(side="left")
        self.include_deleted=tk.BooleanVar(value=False)
        ttk.Checkbutton(row,text="Mostrar excluídas",variable=self.include_deleted,command=lambda:self.act(self.refresh)).pack(side="left",padx=8)
        self.summary=ttk.Label(self,text="",wraplength=1050);self.summary.pack(anchor="w",pady=4)
        row=ttk.Frame(self);row.pack(side="bottom",fill="x",pady=8)
        for label,callback in (("Nova despesa",self.create),("Editar",self.edit),("Quitar",self.pay),("Excluir",self.delete),("Contas mensais",self.recurring)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,8))
        self.tree=table(self,["ID","Descrição","Categoria","Valor","Data gasto","Vencimento","Pago em","Situação"])
        for tag,color in (("PAID","#176a37"),("PENDING","#565f68"),("OVERDUE","#ad2727")):
            self.tree.tag_configure(tag,foreground=color)
        self.rows={}
        self.apply_month()

    def apply_month(self):
        start,end=month_range(self.month.get())
        self.start.set(start.strftime("%d/%m/%Y"));self.end.set(end.strftime("%d/%m/%Y"))
        self.refresh()

    def filters(self):
        return ExpenseFilter(date_input(self.start.get()),date_input(self.end.get()),
            {"Gasto":"incurred","Vencimento":"due","Pagamento":"payment"}[self.basis.get()],
            self.category.get().strip() or None,self.text.get(),{"Todas":None,"Paga":"PAID","Pendente":"PENDING","Vencida":"OVERDUE"}[self.status.get()],self.include_deleted.get())

    def refresh(self):
        filters=self.filters()
        rows=self.s.finance.list_expenses(filters)
        self.rows={r.id:r for r in rows}
        label={"PAID":"Paga","PENDING":"Pendente","OVERDUE":"Vencida"}
        fill(self.tree,[(r.id,(r.id,r.draft.description,r.draft.category,money(r.draft.amount_cents),r.draft.incurred_on.strftime("%d/%m/%Y"),r.due_on.strftime("%d/%m/%Y"),r.paid_on.strftime("%d/%m/%Y") if r.paid_on else "—","Excluída" if r.deleted_at else label[r.status])) for r in rows])
        for r in rows:
            self.tree.item(str(r.id),tags=(r.status,))
        totals=self.s.finance.expense_totals(filters)
        self.summary.configure(text=f"Pago: {money(totals.paid_cents)}    Pendente: {money(totals.pending_cents)}    Vencido (incluído no pendente): {money(totals.overdue_cents)}    Compromissos: {money(totals.commitments_cents)}")

    def form(self,initial=None):
        today=self.s.clock.today()
        initial=initial or ExpenseDraft("","Outras despesas",0,today,today)
        values=ask_fields(self,"Despesa",[("description","Descrição",initial.description),("category","Categoria",initial.category),("amount","Valor (R$)",money(initial.amount_cents).replace("R$ ","")),("incurred","Data do gasto (DD/MM/AAAA)",initial.incurred_on.strftime("%d/%m/%Y")),("due","Vencimento (DD/MM/AAAA)",initial.due_on.strftime("%d/%m/%Y"))])
        if values:
            return ExpenseDraft(values["description"],values["category"],parse_money(values["amount"]),date_input(values["incurred"]),date_input(values["due"]))

    def create(self):
        draft=self.form()
        if draft:
            id=command()
            try:
                self.s.finance.add_expense(draft,False,id)
            except DuplicateExpenseError as error:
                if messagebox.askyesno("Possível duplicidade",f"Lançamentos semelhantes: {error.candidate_ids}\nRegistrar mesmo assim?",parent=self):
                    self.s.finance.add_expense(draft,True,id)
            self.s.application.notify("Consulta financeira atualizada.")

    def edit(self):
        id=self.selected(self.tree);draft=self.form(self.rows[id].draft)
        if draft:
            grant=self.grant("expense.edit");reason=self.reason();cmd=command()
            try:
                self.s.finance.edit_expense(id,draft,False,grant,reason,cmd)
            except DuplicateExpenseError as error:
                if messagebox.askyesno("Possível duplicidade",f"Semelhantes: {error.candidate_ids}. Confirmar?",parent=self):
                    self.s.finance.edit_expense(id,draft,True,grant,reason,cmd)

    def delete(self):
        id=self.selected(self.tree)
        if messagebox.askyesno("Excluir lançamento","Retirar dos cálculos ativos, preservando histórico?\nIsso não devolve dinheiro à gaveta.",parent=self):
            self.s.finance.delete_expense(id,self.grant("expense.delete"),self.reason(),command())

    def pay(self):
        id=self.selected(self.tree);row=self.rows[id]
        pending=row.draft.amount_cents-row.paid_cents
        values=ask_fields(self,"Quitar obrigação",[("date","Pago em (DD/MM/AAAA)",self.s.clock.today().strftime("%d/%m/%Y")),("method","Dinheiro / Pix / Débito / Crédito","Pix"),("drawer","Dinheiro saiu da gaveta? (sim/não)","não")])
        if values:
            method={"dinheiro":"MONEY","pix":"PIX","débito":"DEBIT","debito":"DEBIT","crédito":"CREDIT","credito":"CREDIT"}.get(values["method"].casefold())
            drawer=values["drawer"].casefold()=="sim"
            self.s.finance.pay_obligation(id,pending,date_input(values["date"]),method,drawer,self.grant("cash.withdraw") if drawer else None,command())

    def recurring(self):
        window=tk.Toplevel(self);window.title("Contas mensais");window.geometry("780x420")
        root=View(window,self.s);root.pack(fill="both",expand=True)
        tree=table(root,["ID","Descrição","Valor","Dia","Ativa"],height=7)
        def refresh():
            fill(tree,[(r["id"],(r["id"],r["description"],money(r["amount_cents"]),r["due_day"],"Sim" if r["active"] else "Não")) for r in self.s.recurrence.list_rules()])
        def create():
            draft=self.form()
            if draft:
                day=simpledialog.askinteger("Vencimento","Dia de 1 a 31:",minvalue=1,maxvalue=31,parent=window)
                if day:
                    self.s.recurrence.create_rule(draft,day,self.month.get(),command());refresh()
        def generate():
            id=root.selected(tree)
            if messagebox.askyesno("Gerar previsão",f"Gerar lançamento pendente para {self.month.get()}?\nConfirme o valor antes de pagar.",parent=window):
                self.s.recurrence.generate(id,self.month.get(),command());self.s.application.refresh()
        def edit():
            id=root.selected(tree);row=next(r for r in self.s.recurrence.list_rules() if r["id"]==id)
            draft=self.form(ExpenseDraft(row["description"],row["category"],row["amount_cents"],self.s.clock.today(),self.s.clock.today()))
            if draft:
                values=ask_fields(window,"Alterar regra",[("day","Dia do vencimento",row["due_day"]),("active","Ativa? (sim/não)","sim" if row["active"] else "não")])
                if values:
                    self.s.recurrence.update_rule(id,draft,int(values["day"]),values["active"].casefold()=="sim",self.grant("recurrence.edit"),self.reason(),command());refresh()
        row=ttk.Frame(root);row.pack(fill="x")
        for label,callback in (("Nova regra",create),("Editar futuras",edit),("Gerar mês selecionado",generate)):
            ttk.Button(row,text=label,command=lambda f=callback:root.act(f)).pack(side="left",padx=5)
        refresh()

