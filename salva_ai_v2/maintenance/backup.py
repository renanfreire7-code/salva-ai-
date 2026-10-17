import hashlib
import json
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from ..common.db import APPLICATION_ID
from ..common.clock import Clock
from ..common.commands import CommandBus
from ..common.audit import Audit
from ..common.errors import BusinessError,ConflictError


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    schema_version: str
    created_at: str
    integrity_ok: bool
    external_copy_ok: bool | None = None


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def sync_file(path):
    with Path(path).open("rb") as handle:
        os.fsync(handle.fileno())


def promote(source,destination):
    os.replace(source,destination)
    if hasattr(os,"O_DIRECTORY"):
        fd=os.open(str(Path(destination).parent),os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class BackupService:
    def __init__(self,db,backup_dir):
        self.db,self.backup_dir=db,Path(backup_dir)
        self._external_dir=None

    @property
    def external_dir(self):
        if self._external_dir is not None:
            return self._external_dir
        exists=self.db.conn.execute("SELECT 1 FROM sqlite_master WHERE name='maintenance_settings'").fetchone()
        row=self.db.conn.execute("SELECT value FROM maintenance_settings WHERE key='external_backup'").fetchone() if exists else None
        return Path(row[0]) if row and row[0] else None

    @external_dir.setter
    def external_dir(self,path):
        self._external_dir=Path(path) if path else None

    def list_backups(self):
        return sorted(self.backup_dir.glob("*.sqlite3"),key=lambda p:p.stat().st_mtime,reverse=True) if self.backup_dir.exists() else []

    def set_external_dir(self,path,grant,command_id):
        path=Path(path).resolve()
        if not path.is_dir():
            raise BusinessError('Escolha uma pasta existente para a cópia adicional.')
        if path==self.backup_dir.resolve():
            raise BusinessError('Escolha uma pasta diferente da cópia local.')
        def perform():
            self.db_security.consume(grant,'backup.configure')
            self.db.conn.execute("INSERT INTO maintenance_settings VALUES('external_backup',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(path),))
            Audit(self.db).record('backup.configured',command_id,{},dict(destination=str(path)),None)
            return str(path)
        result=CommandBus(self.db).execute(command_id,'backup.configure',dict(destination=str(path)),perform)
        self._external_dir=None
        return result

    def verify(self,path):
        return self.verify_path(path,self.db.clock)

    @staticmethod
    def verify_path(path,clock=None):
        clock=clock or Clock()
        path=Path(path).resolve()
        if not path.is_file() or path.suffix!=".sqlite3":
            raise BusinessError("Selecione um arquivo de backup SQLite existente.")
        conn=None
        try:
            conn=sqlite3.connect(path.as_uri()+"?mode=ro&immutable=1",uri=True)
            if conn.execute("PRAGMA application_id").fetchone()[0]!=APPLICATION_ID:
                raise BusinessError("O backup não pertence ao novo Salva AI.")
            if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchone():
                raise BusinessError("O backup não passou na verificação de integridade.")
            migrations=dict(conn.execute("SELECT version,checksum FROM schema_migrations"))
            known={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).resolve().parents[1]/"migrations").glob("*.sql")}
            if not migrations or sorted(migrations)!=sorted(known)[:len(migrations)] or any(known.get(version)!=checksum for version,checksum in migrations.items()):
                raise BusinessError("Versão de backup incompatível ou esquema alterado.")
            version=max(migrations)
            return BackupInfo(path,version,clock.now().isoformat(),True)
        except (sqlite3.Error,OSError) as error:
            raise BusinessError("Não foi possível verificar o backup.") from error
        finally:
            if conn:
                conn.close()

    def create(self,kind,command_id):
        if self.db.conn.in_transaction:
            raise BusinessError("Conclua a operação antes de gerar o backup.")
        if not re.fullmatch("[a-z_]{1,40}",kind):
            raise BusinessError("Tipo de backup inválido.")
        if not isinstance(command_id,str) or not command_id.strip():
            raise BusinessError("Identificação da cópia ausente.")
        previous=self.db.conn.execute("SELECT * FROM command_results WHERE id=?",(command_id,)).fetchone()
        if previous:
            if previous["kind"]!="backup.created":
                raise ConflictError("Identificação já usada em outra operação.")
            saved=json.loads(previous["result"])
            if saved["kind"]!=kind:
                raise ConflictError("Identificação já usada em outra cópia.")
            info=self.verify(saved["path"])
            if file_hash(info.path)!=saved["hash"]:
                raise BusinessError("A cópia foi alterada depois de criada.")
            return BackupInfo(info.path,info.schema_version,info.created_at,True,saved["external_copy_ok"])
        self.backup_dir.mkdir(parents=True,exist_ok=True)
        token=hashlib.sha256(command_id.encode()).hexdigest()[:24]
        path=(self.backup_dir/f"{kind}_{token}.sqlite3").resolve()
        if not path.exists():
            temp=path.with_name(path.stem+".tmp.sqlite3")
            try:
                dest=sqlite3.connect(temp)
                try:
                    self.db.conn.backup(dest)
                finally:
                    dest.close()
                self.verify(temp)
                sync_file(temp)
                promote(temp,path)
            finally:
                if temp.exists():
                    temp.unlink()
        info=self.verify(path)
        external_ok=None
        external=self.external_dir
        if external is not None:
            try:
                if not external.is_dir():
                    raise OSError("Destino externo indisponível")
                target=(external/path.name).resolve()
                if target==path:
                    raise OSError('O destino não é uma cópia adicional')
                temp=target.with_name(target.stem+".tmp.sqlite3")
                shutil.copyfile(path,temp)
                self.verify(temp);sync_file(temp);promote(temp,target)
                external_ok=True
            except (OSError,BusinessError):
                external_ok=False
        payload=dict(kind=kind)
        result=dict(kind=kind,path=str(path),hash=file_hash(path),external_copy_ok=external_ok)
        def record():
            Audit(self.db).record("backup.created",command_id,{},dict(kind=kind),None)
            return result
        CommandBus(self.db).execute(command_id,"backup.created",payload,record)
        return BackupInfo(path,info.schema_version,info.created_at,True,external_ok)
