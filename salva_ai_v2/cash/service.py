from .models import CashPosition
from ..common.service import Service, integer
from ..common.errors import BusinessError


class CashService(Service):
    def __init__(self, db, security, clock=None):
        super().__init__(db, security)
        self.clock = clock or db.clock

    def active(self):
        return self.db.conn.execute("SELECT * FROM cash_sessions WHERE state IN ('OPEN','CLOSING')").fetchone()

    def require_open(self):
        pending = self.db.conn.execute("SELECT name FROM sqlite_master WHERE name='closing_jobs'").fetchone()
        if pending and self.db.conn.execute("SELECT 1 FROM closing_jobs WHERE complete=0").fetchone():
            raise BusinessError("Conclua a recuperação do fechamento pendente.")
        session = self.active()
        if session is None or session["state"] != "OPEN":
            raise BusinessError("Abra o caixa antes desta operação.")
        return session

    def open(self, opening_cents, command_id):
        integer(opening_cents,"Troco inicial")
        def perform():
            if self.active():
                raise BusinessError("Já existe um caixa aberto ou em fechamento.")
            if self.db.conn.execute("SELECT name FROM sqlite_master WHERE name='closing_jobs'").fetchone():
                if self.db.conn.execute("SELECT 1 FROM closing_jobs WHERE complete=0").fetchone():
                    raise BusinessError("Há um fechamento pendente de recuperação.")
            return self.db.conn.execute("INSERT INTO cash_sessions(opened_at,opening_cents) VALUES(?,?)",
                (self.clock.now().isoformat(),opening_cents)).lastrowid
        return self.run(command_id,"cash.opened",dict(opening=opening_cents),perform)

    def position(self, session_id):
        row = self.one("cash_sessions",session_id)
        delta = self.db.conn.execute("SELECT COALESCE(SUM(delta_cents),0) FROM cash_entries WHERE session_id=?", (session_id,)).fetchone()[0]
        return CashPosition(row["opening_cents"] + delta)

    def entry(self, delta_cents, kind, source, reason=None):
        if not self.db.conn.in_transaction:
            raise RuntimeError("Lançamento exige transação")
        session = self.require_open()
        if self.position(session["id"]).expected_cents + delta_cents < 0:
            raise BusinessError("Não há dinheiro suficiente na gaveta.")
        return self.db.conn.execute("INSERT INTO cash_entries(session_id,occurred_at,delta_cents,kind,source,reason) VALUES(?,?,?,?,?,?)",
            (session["id"],self.clock.now().isoformat(),delta_cents,kind,source,reason)).lastrowid

    def move(self, kind, amount_cents, reason, grant, command_id):
        integer(amount_cents,"Valor",1)
        if kind not in ("WITHDRAWAL","REINFORCEMENT"):
            raise BusinessError("Movimento de caixa inválido.")
        def perform():
            self.protect(grant,"cash.withdraw" if kind=="WITHDRAWAL" else "cash.reinforce",reason)
            return self.entry(-amount_cents if kind=="WITHDRAWAL" else amount_cents,kind,"movement:"+command_id,reason)
        return self.run(command_id,"cash.moved",dict(kind=kind,amount=amount_cents,reason=reason),perform)

    def blockers(self, session_id):
        self.one("cash_sessions",session_id)
        tables = {r[0] for r in self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = []
        if "orders" in tables:
            if self.db.conn.execute("SELECT 1 FROM orders WHERE kind='TAB' AND state='OPEN'").fetchone():
                result.append("Comandas abertas")
            if self.db.conn.execute("SELECT 1 FROM orders WHERE kind='DELIVERY' AND state NOT IN ('DELIVERED','CANCELED')").fetchone():
                result.append("Pedidos em andamento")
            if 'collections' in tables and self.db.conn.execute("SELECT 1 FROM orders o JOIN delivery_orders d ON d.order_id=o.id WHERE o.state='DELIVERED' AND NOT EXISTS(SELECT 1 FROM collections c WHERE c.order_id=o.id)").fetchone():
                result.append('Pedidos sem pagamento confirmado')
        if "custody_entries" in tables:
            if self.db.conn.execute("SELECT COALESCE(SUM(delta_cents),0) FROM custody_entries").fetchone()[0]:
                result.append("Dinheiro do entregador sem conferir")
        if "refunds" in tables and self.db.conn.execute("SELECT 1 FROM refunds WHERE pending_cents>0").fetchone():
            result.append("Reembolso pendente")
        if "closing_jobs" in tables and self.db.conn.execute("SELECT 1 FROM closing_jobs WHERE complete=0").fetchone():
            result.append("Fechamento pendente")
        return result
