"""Credenciais fictícias legadas: não usa a política de novos cadastros."""
import secrets
from salva_ai_v2.security.service import SecurityService,ITERATIONS


def seed_legacy_pin(db,pin='681942'):
    key=secrets.token_urlsafe(32);salt=secrets.token_bytes(16);recovery_salt=secrets.token_bytes(16)
    db.conn.execute('INSERT INTO admin_credentials(id,salt,pin_hash,recovery_salt,recovery_hash,iterations) VALUES(1,?,?,?,?,?)',
        (salt,SecurityService._hash(pin,salt),recovery_salt,SecurityService._hash(key,recovery_salt),ITERATIONS))
    return key
