import calendar
from dataclasses import asdict
from datetime import date
from .models import ExpenseDraft
from .queries import month_range
from ..common.service import Service,integer
from ..common.errors import BusinessError


class RecurrenceService(Service):
    def __init__(self,db,finance,clock=None):
        super().__init__(db,finance.security)
        self.finance,self.clock=finance,clock or db.clock

    def list_rules(self):
        return [dict(r) for r in self.db.conn.execute("SELECT * FROM recurring_rules ORDER BY id")]

    def create_rule(self,template,due_day,start_month,command_id):
        self.finance._validate(template)
        integer(due_day,"Dia do vencimento",1)
        if due_day>31:
            raise BusinessError("Dia deve estar entre 1 e 31.")
        month_range(start_month)
        def perform():
            return self.db.conn.execute("INSERT INTO recurring_rules(description,category,amount_cents,due_day,start_month) VALUES(?,?,?,?,?)",
                (template.description,template.category,template.amount_cents,due_day,start_month)).lastrowid
        return self.run(command_id,"recurrence.created",dict(template=asdict(template),due_day=due_day,start_month=start_month),perform)

    def generate(self,rule_id,month,command_id):
        start,end=month_range(month)
        def perform():
            existing=self.db.conn.execute("SELECT obligation_id FROM recurring_occurrences WHERE rule_id=? AND competence_month=?", (rule_id,month)).fetchone()
            if existing:
                return existing[0]
            rule=self.one("recurring_rules",rule_id)
            if not rule["active"] or month<rule["start_month"]:
                raise BusinessError("Regra inativa ou período anterior ao início.")
            due=date(start.year,start.month,min(rule["due_day"],end.day))
            draft=ExpenseDraft(rule["description"],rule["category"],rule["amount_cents"],start,due)
            id=self.finance.add_expense(draft,True,f"recurring:{rule_id}:{month}")
            self.db.conn.execute("INSERT INTO recurring_occurrences VALUES(?,?,?)",(rule_id,month,id))
            return id
        return self.run(command_id,"recurrence.generated",dict(rule_id=rule_id,month=month),perform)

    def update_rule(self,rule_id,template,due_day,active,grant,reason,command_id):
        self.finance._validate(template)
        integer(due_day,"Dia do vencimento",1)
        if due_day>31:
            raise BusinessError("Dia deve estar entre 1 e 31.")
        def perform():
            self.protect(grant,"recurrence.edit",reason)
            old=self.one("recurring_rules",rule_id)
            self.db.conn.execute("UPDATE recurring_rules SET description=?,category=?,amount_cents=?,due_day=?,active=?,revision=revision+1 WHERE id=?",
                (template.description,template.category,template.amount_cents,due_day,bool(active),rule_id))
            self.audit.record("recurrence.changed",rule_id,dict(old),dict(self.one("recurring_rules",rule_id)),reason)
            return rule_id
        return self.run(command_id,"recurrence.updated",dict(rule_id=rule_id,template=asdict(template),due_day=due_day,active=bool(active),reason=reason),perform)
