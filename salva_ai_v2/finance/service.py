from dataclasses import asdict
from datetime import date
from uuid import uuid4
from .models import ExpenseDraft,ExpenseFilter,ExpenseRow,ExpenseTotals
from ..common.service import Service,integer,valid_date
from ..common.errors import BusinessError
from ..inventory.queries import normalize
from .payments import PaymentsMixin


class DuplicateExpenseError(BusinessError):
    def __init__(self, candidate_ids):
        self.candidate_ids=candidate_ids
        super().__init__("Possível despesa duplicada. Confira os lançamentos antes de confirmar.")


class FinanceService(PaymentsMixin, Service):
    def __init__(self,db,cash,security,clock=None):
        super().__init__(db,security)
        self.cash,self.clock=cash,clock or db.clock

    def _validate(self,draft):
        integer(draft.amount_cents,"Valor",1)
        if not draft.description.strip() or not draft.category.strip():
            raise BusinessError("Informe descrição e categoria.")
        valid_date(draft.incurred_on);valid_date(draft.due_on)

    def _duplicates(self,draft,exclude=None):
        rows=self.db.conn.execute("SELECT * FROM obligations WHERE source_type='EXPENSE' AND deleted_at IS NULL AND amount_cents=? AND substr(incurred_on,1,7)=?",
            (draft.amount_cents,valid_date(draft.incurred_on)[:7])).fetchall()
        return [r["id"] for r in rows if r["id"]!=exclude and normalize(r["description"])==normalize(draft.description) and normalize(r["category"])==normalize(draft.category)]

    def paid_cents(self,obligation_id):
        return self.db.conn.execute("SELECT COALESCE(SUM(amount_cents),0) FROM obligation_payments WHERE obligation_id=? AND corrected=0",(obligation_id,)).fetchone()[0]

    def add_expense(self,draft,accept_duplicate,command_id):
        self._validate(draft)
        def perform():
            candidates=self._duplicates(draft)
            if candidates and not accept_duplicate:
                raise DuplicateExpenseError(candidates)
            return self.db.conn.execute("INSERT INTO obligations(source_type,source_id,description,category,amount_cents,incurred_on,due_on,created_at) VALUES('EXPENSE',?,?,?,?,?,?,?)",
                (command_id,draft.description.strip(),draft.category.strip(),draft.amount_cents,valid_date(draft.incurred_on),valid_date(draft.due_on),self.clock.now().isoformat())).lastrowid
        return self.run(command_id,"expense.created",dict(draft=asdict(draft),accept_duplicate=bool(accept_duplicate)),perform)

    def edit_expense(self,expense_id,draft,accept_duplicate,grant,reason,command_id):
        self._validate(draft)
        def perform():
            self.protect(grant,"expense.edit",reason)
            old=self.one("obligations",expense_id)
            if old["source_type"]!="EXPENSE" or old["deleted_at"]:
                raise BusinessError("Edite esta obrigação pelo processo que a originou.")
            if draft.amount_cents<self.paid_cents(expense_id):
                raise BusinessError("Corrija o pagamento antes de reduzir o valor abaixo do que foi pago.")
            duplicates=self._duplicates(draft,expense_id)
            if duplicates and not accept_duplicate:
                raise DuplicateExpenseError(duplicates)
            self.db.conn.execute("UPDATE obligations SET description=?,category=?,amount_cents=?,incurred_on=?,due_on=? WHERE id=?",
                (draft.description.strip(),draft.category.strip(),draft.amount_cents,valid_date(draft.incurred_on),valid_date(draft.due_on),expense_id))
            self.audit.record("expense.changed",expense_id,dict(old),asdict(draft)|{"incurred_on":valid_date(draft.incurred_on),"due_on":valid_date(draft.due_on)},reason)
            return expense_id
        return self.run(command_id,"expense.edit",dict(expense_id=expense_id,draft=asdict(draft),accept_duplicate=bool(accept_duplicate),reason=reason),perform)

    def delete_expense(self,expense_id,grant,reason,command_id):
        def perform():
            self.protect(grant,"expense.delete",reason)
            old=self.one("obligations",expense_id)
            if old["source_type"]!="EXPENSE" or old["deleted_at"]:
                raise BusinessError("Despesa excluída ou gerenciada por outro processo.")
            self.db.conn.execute("UPDATE obligations SET deleted_at=? WHERE id=?", (self.clock.now().isoformat(),expense_id))
            self.audit.record("expense.deleted",expense_id,dict(old),dict(self.one("obligations",expense_id)),reason)
            return expense_id
        return self.run(command_id,"expense.delete",dict(expense_id=expense_id,reason=reason),perform)

    def list_expenses(self,filters):
        start,end=valid_date(filters.start),valid_date(filters.end)
        if start>end:
            raise BusinessError("O início deve ser anterior ao fim do período.")
        basis={"incurred":"incurred_on","due":"due_on","payment":"paid_on"}.get(filters.date_basis)
        if not basis:
            raise BusinessError("Escolha data do gasto, vencimento ou pagamento.")
        args=[start,end]
        predicate=f"o.{basis} BETWEEN ? AND ?" if basis!="paid_on" else "EXISTS(SELECT 1 FROM obligation_payments p WHERE p.obligation_id=o.id AND p.corrected=0 AND p.paid_on BETWEEN ? AND ?)"
        rows=self.db.conn.execute("SELECT o.* FROM obligations o WHERE "+predicate+" ORDER BY o.incurred_on DESC,o.id DESC",args).fetchall()
        result=[]
        for r in rows:
            if r["deleted_at"] and not filters.include_deleted:
                continue
            if filters.category and r["category"]!=filters.category:
                continue
            if normalize(filters.text) not in normalize(r["description"]):
                continue
            paid=self.paid_cents(r["id"])
            paid_on=self.db.conn.execute("SELECT MAX(paid_on) FROM obligation_payments WHERE obligation_id=? AND corrected=0",(r["id"],)).fetchone()[0]
            status="PAID" if paid>=r["amount_cents"] else "OVERDUE" if r["due_on"]<self.clock.today().isoformat() else "PENDING"
            if filters.status and status!=filters.status:
                continue
            draft=ExpenseDraft(r["description"],r["category"],r["amount_cents"],date.fromisoformat(r["incurred_on"]),date.fromisoformat(r["due_on"]))
            result.append(ExpenseRow(r["id"],draft,paid,date.fromisoformat(paid_on) if paid_on else None,status,r["deleted_at"],r["source_type"]))
        return result

    def expense_totals(self,filters):
        rows=[r for r in self.list_expenses(filters) if not r.deleted_at]
        categories={}
        for row in rows:
            categories[row.draft.category]=categories.get(row.draft.category,0)+row.draft.amount_cents
        return ExpenseTotals(sum(r.paid_cents for r in rows),sum(r.draft.amount_cents-r.paid_cents for r in rows),
            sum(r.draft.amount_cents-r.paid_cents for r in rows if r.status=="OVERDUE"),
            sum(r.draft.amount_cents for r in rows),categories)
