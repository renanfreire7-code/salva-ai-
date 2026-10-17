import json
import os
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .backup import BackupService,file_hash,sync_file,promote
from ..common.db import Database
from ..common.audit import Audit
from ..common.commands import CommandBus
from ..common.errors import BusinessError


@dataclass(frozen=True)
class RestorePreview:
    id: str
    source: Path
    sha256: str
    schema_version: str
    target: Path


def write_journal(path,record):
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
    sync_file(temp)
    os.replace(temp,path)


def recover_restore(data_dir):
    root=Path(data_dir).resolve()
    journal=root/"restauracao_pendente.json"
    if not journal.exists():
        return None
    try:
        record=json.loads(journal.read_text(encoding="utf-8"))
        target,stage,preserved=(Path(record[key]).resolve() for key in ("target","stage","preserved"))
        if any(not p.is_relative_to(root) or p.suffix!=".sqlite3" for p in (target,stage,preserved)):
            raise BusinessError("Registro de recuperação aponta para local inesperado.")
        try:
            BackupService.verify_path(target)
            current_ok=True
        except BusinessError:
            current_ok=False
        installed=record.get("state")=="replaced" or (not stage.exists() and current_ok and file_hash(target)==record["sha256"])
        if not current_ok:
            BackupService.verify_path(preserved)
            temp=target.with_name(target.stem+".recovery.sqlite3")
            shutil.copyfile(preserved,temp);sync_file(temp);promote(temp,target)
            installed=False
        db=Database(target)
        try:
            kind="restore.completed" if installed else "restore.kept_original"
            def log():
                Audit(db).record(kind,record["id"],{},{"recovered_after_interruption":True},None)
                return {"recovered":True}
            CommandBus(db).execute("restore-result:"+record["id"],kind,{"source_hash":record["sha256"]},log)
        finally:
            db.close()
        if stage.exists():
            stage.unlink()
        journal.unlink()
        return "restored" if installed else "kept_original"
    except (OSError,ValueError,KeyError) as error:
        raise BusinessError("Não foi possível concluir a recuperação. O banco e a cópia anterior foram preservados.") from error


class RestoreService:
    def __init__(self,data_dir,backups,security):
        self.on_completed=None
        self.data_dir=Path(data_dir).resolve()
        self.backups,self.security=backups,security
        self.db=backups.db
        self._previews={}

    def prepare(self,source,grant):
        source=Path(source).resolve()
        target=self.db.path.resolve()
        if source==target:
            raise BusinessError("O banco ativo não pode ser usado como origem da restauração.")
        info=self.backups.verify(source)
        self.security.validate(grant,"backup.restore")
        preview=RestorePreview(secrets.token_urlsafe(24),source,file_hash(source),info.schema_version,target)
        self._previews[preview.id]=(preview,grant)
        return preview

    def _reopen(self):
        reopened=Database(self.db.path,self.db.clock)
        self.db.conn=reopened.conn

    def apply(self,preview,confirmed):
        entry=self._previews.get(preview.id)
        if entry is None or entry[0]!=preview:
            raise BusinessError("Consulte novamente o backup antes de restaurar.")
        if not confirmed:
            self._previews.pop(preview.id,None)
            return
        self.backups.verify(preview.source)
        if file_hash(preview.source)!=preview.sha256:
            raise BusinessError("O arquivo mudou após a conferência. Consulte o backup novamente.")
        self.security.validate(entry[1],"backup.restore")
        operation=str(uuid4())
        with self.db.transaction():
            self.security.consume(entry[1],"backup.restore")
            Audit(self.db).record("restore.started",operation,{},{"source_hash":preview.sha256},None)
        preserved=self.backups.create("antes_restauracao","before-restore:"+operation)
        stage=self.data_dir/("restore_"+operation+".sqlite3")
        journal=self.data_dir/"restauracao_pendente.json"
        shutil.copyfile(preview.source,stage)
        if file_hash(stage)!=preview.sha256:
            stage.unlink()
            raise BusinessError("A origem mudou durante a cópia. Restauração interrompida.")
        self.backups.verify(stage);sync_file(stage)
        record=dict(id=operation,target=str(preview.target),stage=str(stage),preserved=str(preserved.path),
                    sha256=preview.sha256,state="prepared")
        write_journal(journal,record)
        try:
            self.db.close()
            promote(stage,preview.target)
            record["state"]="replaced"
            write_journal(journal,record)
            self._reopen()
            def log():
                Audit(self.db).record("restore.completed",operation,{},{"source_hash":preview.sha256},None)
                return {"restored":True}
            CommandBus(self.db).execute("restore-result:"+operation,"restore.completed",{"source_hash":preview.sha256},log)
            journal.unlink()
            self.security._grants.clear()
            self._previews.clear()
            if self.on_completed:self.on_completed()
        except BaseException:
            if self.db.conn is None:
                self._reopen()
            raise
