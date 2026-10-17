import hashlib
import json
from .errors import BusinessError, ConflictError


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class CommandBus:
    def __init__(self, db):
        self.db = db

    def execute(self, command_id, kind, payload, handler):
        if not isinstance(command_id, str) or not command_id.strip():
            raise BusinessError("Identificação da operação ausente.")
        fingerprint = hashlib.sha256(canonical(payload).encode()).hexdigest()
        with self.db.transaction():
            previous = self.db.conn.execute("SELECT * FROM command_results WHERE id=?", (command_id,)).fetchone()
            if previous:
                if previous["kind"] != kind or previous["fingerprint"] != fingerprint:
                    raise ConflictError("Esta identificação já pertence a outra operação.")
                return json.loads(previous["result"])
            result = handler()
            encoded = canonical(result)
            self.db.conn.execute("INSERT INTO command_results VALUES(?,?,?,?)",
                                 (command_id, kind, fingerprint, encoded))
            return json.loads(encoded)
