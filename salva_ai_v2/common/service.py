from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from .commands import CommandBus
from .audit import Audit
from .errors import BusinessError


def serial(value):
    if is_dataclass(value):
        return serial(asdict(value))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise BusinessError(f"{label}: informe um número inteiro a partir de {minimum}.")
    return value


def valid_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (ValueError, TypeError):
        raise BusinessError("Data inválida.") from None


class Service:
    def __init__(self, db, security=None):
        self.db, self.security = db, security
        self.bus, self.audit = CommandBus(db), Audit(db)

    def run(self, command_id, kind, payload, handler):
        def perform():
            result = handler()
            self.audit.record(kind, str(result if isinstance(result, int) else command_id),
                              {}, serial(payload), payload.get("reason"))
            return result
        return self.bus.execute(command_id, kind, serial(payload), perform)

    def protect(self, grant, action, reason):
        if not isinstance(reason, str) or len(reason.strip()) < 5:
            raise BusinessError("Informe um motivo com pelo menos cinco caracteres.")
        self.security.consume(grant, action)

    def one(self, table, id):
        row = self.db.conn.execute(f"SELECT * FROM {table} WHERE id=?", (id,)).fetchone()
        if row is None:
            raise BusinessError("Registro não encontrado.")
        return row
