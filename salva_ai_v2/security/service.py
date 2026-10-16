import hashlib
import hmac
import re
import secrets
from .models import AdminGrant
from ..common.audit import Audit
from ..common.errors import AuthorizationError, BusinessError

ITERATIONS = 600_000


class SecurityService:
    def __init__(self, db, clock=None):
        self.db = db
        self.clock = clock or db.clock
        self._grants = {}

    @property
    def configured(self):
        return self.db.conn.execute("SELECT 1 FROM admin_credentials").fetchone() is not None

    def _pin(self, pin):
        if not isinstance(pin, str) or not re.fullmatch(r"[0-9]{6}", pin):
            raise BusinessError("O PIN deve ter seis dígitos.")

    @staticmethod
    def _hash(value, salt, iterations=ITERATIONS):
        return hashlib.pbkdf2_hmac("sha256", value.encode(), salt, iterations)

    def setup(self, pin):
        self._pin(pin)
        key = secrets.token_urlsafe(32)
        salt, recovery_salt = secrets.token_bytes(16), secrets.token_bytes(16)
        with self.db.transaction():
            if self.configured:
                raise BusinessError("O PIN já foi configurado.")
            self.db.conn.execute("INSERT INTO admin_credentials(id,salt,pin_hash,recovery_salt,recovery_hash,iterations) VALUES(1,?,?,?,?,?)",
                (salt, self._hash(pin, salt), recovery_salt, self._hash(key, recovery_salt), ITERATIONS))
            Audit(self.db).record("security.setup", "admin", {}, {"configured": True}, None)
        return key

    def authorize(self, pin, action):
        self._pin(pin)
        if not isinstance(action, str) or not action.strip():
            raise AuthorizationError("Ação administrativa inválida.")
        error = None
        with self.db.transaction():
            row = self.db.conn.execute("SELECT * FROM admin_credentials WHERE id=1").fetchone()
            if not row:
                raise AuthorizationError("Configure o PIN administrativo.")
            now = max(self.clock.now().timestamp(), row["last_time"])
            self.db.conn.execute("UPDATE admin_credentials SET last_time=? WHERE id=1", (now,))
            if now < row["blocked_until"]:
                error = "Aguarde antes de tentar o PIN novamente."
            elif not hmac.compare_digest(self._hash(pin, row["salt"], row["iterations"]), row["pin_hash"]):
                failures = row["failures"] + 1
                wait = min(900, 30 * 2 ** min(max(0, failures - 5), 5)) if failures >= 5 else 0
                self.db.conn.execute("UPDATE admin_credentials SET failures=?, blocked_until=? WHERE id=1", (failures, now + wait))
                error = "PIN incorreto."
            else:
                self.db.conn.execute("UPDATE admin_credentials SET failures=0, blocked_until=0 WHERE id=1")
        if error:
            raise AuthorizationError(error)
        grant = AdminGrant(secrets.token_urlsafe(32), action, now + 60)
        self._grants[grant.id] = grant
        return grant

    def validate(self, grant, action):
        if not isinstance(grant, AdminGrant) or self._grants.get(grant.id) != grant or grant.action != action:
            raise AuthorizationError("Confirme o PIN para esta operação.")
        row = self.db.conn.execute("SELECT last_time FROM admin_credentials WHERE id=1").fetchone()
        now = max(self.clock.now().timestamp(), row[0])
        fingerprint = hashlib.sha256(grant.id.encode()).hexdigest()
        if now >= grant.expires_at or self.db.conn.execute("SELECT 1 FROM consumed_grants WHERE id=?", (fingerprint,)).fetchone():
            raise AuthorizationError("Autorização expirada ou já utilizada.")

    def consume(self, grant, action):
        if not self.db.conn.in_transaction:
            raise RuntimeError("Autorização exige a transação da operação")
        self.validate(grant, action)
        fingerprint = hashlib.sha256(grant.id.encode()).hexdigest()
        self.db.conn.execute("INSERT INTO consumed_grants VALUES(?)", (fingerprint,))

    def recover(self, recovery_key, new_pin):
        self._pin(new_pin)
        if not isinstance(recovery_key, str) or not recovery_key:
            raise AuthorizationError("Chave de recuperação inválida.")
        new_key = secrets.token_urlsafe(32)
        with self.db.transaction():
            row = self.db.conn.execute("SELECT * FROM admin_credentials WHERE id=1").fetchone()
            if not row or not hmac.compare_digest(self._hash(recovery_key, row["recovery_salt"], row["iterations"]), row["recovery_hash"]):
                raise AuthorizationError("Chave de recuperação inválida.")
            salt, recovery_salt = secrets.token_bytes(16), secrets.token_bytes(16)
            self.db.conn.execute("UPDATE admin_credentials SET salt=?,pin_hash=?,recovery_salt=?,recovery_hash=?,iterations=?,failures=0,blocked_until=0,last_time=? WHERE id=1",
                (salt, self._hash(new_pin, salt), recovery_salt, self._hash(new_key, recovery_salt), ITERATIONS, self.clock.now().timestamp()))
            Audit(self.db).record("security.recovered", "admin", {}, {"recovery_key_rotated": True}, None)
        self._grants.clear()
        return new_key

