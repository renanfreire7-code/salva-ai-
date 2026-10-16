import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .clock import Clock
from .errors import BusinessError

APPLICATION_ID = 0x53414932


class Database:
    def __init__(self, path: Path, clock=None):
        self.path = Path(path)
        self.clock = clock or Clock()
        self.conn = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.path), isolation_level=None)
            self.conn.row_factory = sqlite3.Row
            appid = self.conn.execute("PRAGMA application_id").fetchone()[0]
            tables = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if appid != APPLICATION_ID and (appid or tables):
                self.close()
                raise BusinessError("Este banco pertence a outro aplicativo. O banco antigo foi preservado.")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.execute("PRAGMA busy_timeout=5000")
        except (OSError, sqlite3.Error) as exc:
            self.close()
            raise BusinessError("Não foi possível abrir o banco de dados no diretório escolhido.") from exc

    @contextmanager
    def transaction(self):
        if self.conn.in_transaction:
            yield self.conn
            return
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def migrate(self):
        folder = Path(__file__).resolve().parents[1] / "migrations"
        with self.transaction():
            self.conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
            exists = self.conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
            applied = dict(self.conn.execute("SELECT version, checksum FROM schema_migrations")) if exists else {}
            for path in sorted(folder.glob("*.sql")):
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode()).hexdigest()
                if path.name in applied:
                    if applied[path.name] != checksum:
                        raise BusinessError("Migração instalada foi alterada; atualização interrompida.")
                    continue
                for statement in sql.split(";"):
                    if statement.strip():
                        self.conn.execute(statement)
                self.conn.execute("INSERT INTO schema_migrations VALUES(?,?)", (path.name, checksum))

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

