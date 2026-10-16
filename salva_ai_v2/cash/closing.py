from dataclasses import dataclass
from pathlib import Path
import json
from ..common.service import integer
from ..common.commands import canonical,CommandBus
from ..common.audit import Audit
from ..common.errors import BusinessError,ConflictError
from ..maintenance.backup import sync_file,promote
from ..reporting.html import cash_html


@dataclass(frozen=True)
class ClosingResult:
    session_id: int
    complete: bool
    report_path: Path
    backup_path: Path
    external_copy_ok: bool | None = None


class ClosingService:
    def __init__(self,db,cash,backups,reports):
        self.db,self.cash,self.backups,self.reports=db,cash,backups,reports
        self.report_dir=backups.backup_dir.parent/"relatorios"

    def pending(self):
        return [r[0] for r in self.db.conn.execute("SELECT session_id FROM closing_jobs WHERE complete=0")]

    def begin(self,counted_cents,grant,reason,command_id):
        integer(counted_cents,"Dinheiro contado")
        payload=canonical(dict(counted_cents=counted_cents,reason=reason))
        job=self.db.conn.execute("SELECT * FROM closing_jobs WHERE command_id=?",(command_id,)).fetchone()
        if job:
            if job["payload"]!=payload:
                raise ConflictError("Este fechamento já foi iniciado com outros valores.")
            return self.resume(job["session_id"])
        with self.db.transaction():
            session=self.cash.require_open()
            blockers=self.cash.blockers(session["id"])
            if blockers:
                raise BusinessError("Resolva antes de fechar: "+", ".join(blockers))
            expected=self.cash.position(session["id"]).expected_cents
            if expected!=counted_cents:
                self.cash.protect(grant,"cash.close",reason)
            self.db.conn.execute("UPDATE cash_sessions SET state='CLOSING',expected_cents=?,counted_cents=?,variance_cents=?,reason=? WHERE id=?",
                (expected,counted_cents,counted_cents-expected,reason,session["id"]))
            self.db.conn.execute("INSERT INTO closing_jobs(session_id,command_id,payload) VALUES(?,?,?)",(session["id"],command_id,payload))
            Audit(self.db).record("cash.closing",session["id"],dict(session),dict(counted_cents=counted_cents,expected_cents=expected),reason)
        return self.resume(session["id"])

    def _mark_closed(self,session_id):
        with self.db.transaction():
            session=self.cash.one("cash_sessions",session_id)
            if session["state"]!="CLOSED":
                self.db.conn.execute("UPDATE cash_sessions SET state='CLOSED',closed_at=? WHERE id=?", (self.db.clock.now().isoformat(),session_id))
                Audit(self.db).record("cash.closed",session_id,dict(session),dict(self.cash.one("cash_sessions",session_id)),session["reason"])

    def _finish(self,job,result):
        def perform():
            self.db.conn.execute("UPDATE closing_jobs SET complete=1,report_path=?,backup_path=?,external_copy_ok=? WHERE session_id=?",
                (str(result.report_path),str(result.backup_path),result.external_copy_ok,result.session_id))
            Audit(self.db).record("cash.artifacts_ready",result.session_id,{},dict(complete=True),None)
            return dict(session_id=result.session_id,report_path=str(result.report_path),backup_path=str(result.backup_path),external_copy_ok=result.external_copy_ok)
        CommandBus(self.db).execute(job["command_id"],"cash.close_complete",json.loads(job["payload"]),perform)

    def resume(self,session_id):
        job=self.db.conn.execute("SELECT * FROM closing_jobs WHERE session_id=?",(session_id,)).fetchone()
        if job is None:
            raise BusinessError("Fechamento pendente não encontrado.")
        if job["complete"]:
            self.backups.verify(job["backup_path"])
            if not Path(job["report_path"]).is_file():
                raise BusinessError("Relatório do fechamento não foi localizado.")
            return ClosingResult(session_id,True,Path(job["report_path"]),Path(job["backup_path"]),None if job["external_copy_ok"] is None else bool(job["external_copy_ok"]))
        self.report_dir.mkdir(parents=True,exist_ok=True)
        path=self.report_dir/f"caixa_{session_id}.html"
        temp=path.with_suffix(".tmp.html")
        cash_html(temp,self.reports.cash_report(session_id))
        sync_file(temp);promote(temp,path)
        self._mark_closed(session_id)
        backup=self.backups.create("fechamento","closing-backup:"+job["command_id"])
        result=ClosingResult(session_id,True,path,backup.path,backup.external_copy_ok)
        self._finish(job,result)
        return result

