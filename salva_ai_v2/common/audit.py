from uuid import uuid4
from .commands import canonical


class Audit:
    def __init__(self, db):
        self.db = db

    def record(self, kind, object_id, before, after, reason):
        if not self.db.conn.in_transaction:
            raise RuntimeError("Auditoria exige a transação da operação")
        event_id = str(uuid4())
        self.db.conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)",
            (event_id, self.db.clock.now().isoformat(), kind, str(object_id),
             canonical(before), canonical(after), reason))
        return event_id

