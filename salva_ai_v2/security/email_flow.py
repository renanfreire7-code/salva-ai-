"""Desafios locais: rede no runner; banco e callbacks na thread proprietária."""
from math import ceil
import secrets,threading,time
from .email_models import EmailChallenge,EmailProof,VerifiedIdentity,EmailProviderError
from .email_provider import normalize_email
from ..common.errors import BusinessError,AuthorizationError


class EmailAccessService:
    def __init__(self,db,client,runner,clock=None,monotonic=None):
        self.db,self.client,self.runner=db,client,runner
        self.clock=clock or db.clock;self.monotonic=monotonic or time.monotonic
        self._thread=threading.get_ident();self._generation=0;self._challenges={};self._proofs={}
        self._last_mono=self.monotonic()
        high=self.db.conn.execute('SELECT last_time FROM email_auth_clock WHERE id=1').fetchone()[0]
        self._last_time=max(high,self.clock.now().timestamp())
        self.invalidate_all()

    def _main(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('EmailAccessService requer a thread principal.')

    def _now(self,persist=False):
        self._main();mono=self.monotonic()
        high=self.db.conn.execute('SELECT last_time FROM email_auth_clock WHERE id=1').fetchone()[0]
        now=max(high,self.clock.now().timestamp(),self._last_time+max(0,mono-self._last_mono))
        self._last_time,self._last_mono=now,mono
        if persist:self.db.conn.execute('UPDATE email_auth_clock SET last_time=? WHERE id=1',(now,))
        return now

    @property
    def available(self):return self.client is not None

    def _account(self):return self.db.conn.execute('SELECT * FROM establishment_account WHERE id=1').fetchone()

    @property
    def bound(self):
        row=self._account()
        return bool(row and any(row[name] is not None for name in ('email','email_subject','email_issuer','email_verified_at')))

    def _context(self,email,purpose):
        if not self.available:raise BusinessError('Configure o serviço de e-mail antes de continuar. O cadastro atual foi mantido.')
        row=self._account()
        if purpose=='SETUP' and row is None:return None,None
        if purpose=='ENROLL' and row and not self.bound:return row['revision'],None
        if purpose=='RECOVER' and row and self.bound:
            if not all(row[name] for name in ('email','email_subject','email_issuer','email_verified_at')):raise BusinessError('O vínculo de e-mail está incompleto. Preserve o banco e solicite suporte.')
            if row['email_issuer']!=self.client.config.url:raise BusinessError('Configure o projeto de e-mail vinculado a esta conta.')
            if row['email']!=email:raise BusinessError('Informe o e-mail cadastrado neste estabelecimento.')
            return row['revision'],row['email_subject']
        raise AuthorizationError('Esta operação não está disponível para o cadastro atual.')

    def remaining_wait(self,email=None):
        now=self._now()
        maximum=self.db.conn.execute('SELECT COALESCE(MAX(next_send_at),0) FROM email_auth_challenges').fetchone()[0]
        return max(0,ceil(maximum-now))

    def invalidate_all(self):
        self._main();self._generation+=1;self._challenges.clear();self._proofs.clear()
        if self.db.conn is not None:
            self.db.conn.execute("UPDATE email_auth_challenges SET state='CANCELED' WHERE state IN ('SENDING','SENT','VERIFYING','VERIFIED')")

    def _row(self,challenge):
        if self._challenges.get(challenge.id) is not challenge:raise AuthorizationError('Solicite e confirme um novo código.')
        row=self.db.conn.execute('SELECT * FROM email_auth_challenges WHERE id=?',(challenge.id,)).fetchone()
        if not row or row['purpose']!=challenge.purpose or row['email']!=challenge.email or row['account_revision']!=challenge.account_revision:raise AuthorizationError('Solicite e confirme um novo código.')
        revision,subject=self._context(challenge.email,challenge.purpose)
        if revision!=challenge.account_revision or subject!=row['expected_subject'] or row['issuer']!=self.client.config.url:raise AuthorizationError('O cadastro mudou. Solicite um novo código.')
        return row

    def _live(self,challenge,generation):
        return generation==self._generation and self._challenges.get(challenge.id) is challenge

    def _safe(self,error):
        return error if isinstance(error,EmailProviderError) else BusinessError('Não foi possível concluir a confirmação. Tente novamente.')

    def _throttle(self,challenge,error,now):
        if isinstance(error,EmailProviderError) and error.kind=='RATE_LIMIT':
            until=now+max(60,error.retry_after_seconds)
            self.db.conn.execute('UPDATE email_auth_challenges SET next_send_at=MAX(next_send_at,?),verify_after=MAX(verify_after,?) WHERE id=?',(until,until,challenge.id))

    def request_code(self,email,purpose,on_success,on_error):
        self._main();email=normalize_email(email);revision,subject=self._context(email,purpose)
        now=self._now(persist=True)
        wait=self.remaining_wait(email)
        if wait:raise BusinessError(f'Aguarde {wait} segundos antes de reenviar.')
        self.invalidate_all()
        challenge=EmailChallenge(secrets.token_urlsafe(32),purpose,email,revision)
        with self.db.transaction():
            self.db.conn.execute('INSERT INTO email_auth_challenges(id,purpose,email,issuer,expected_subject,account_revision,created_at,next_send_at,expires_at,state) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (challenge.id,purpose,email,self.client.config.url,subject,revision,now,now+60,now+600,'SENDING'))
        self._challenges[challenge.id]=challenge;generation=self._generation;client=self.client
        def sent(_):
            if not self._live(challenge,generation):return
            try:
                row=self._row(challenge)
                if row['state']!='SENDING':return
                self.db.conn.execute("UPDATE email_auth_challenges SET state='SENT' WHERE id=?",(challenge.id,))
            except BusinessError as error:on_error(error);return
            on_success(challenge)
        def failed(error):
            if not self._live(challenge,generation):return
            with self.db.transaction():
                now=self._now(persist=True);self._throttle(challenge,error,now)
                self.db.conn.execute("UPDATE email_auth_challenges SET state='FAILED' WHERE id=?",(challenge.id,))
            on_error(self._safe(error))
        self.runner.submit(lambda:client.send_code(email,create_user=purpose!='RECOVER'),sent,failed)

    def verify_code(self,challenge,code,on_success,on_error):
        self._main();row=self._row(challenge);now=self._now(persist=True)
        if row['state']!='SENT' or row['attempts']>=5 or now>=row['expires_at']:raise AuthorizationError('Código vencido ou tentativas esgotadas. Solicite outro.')
        if now<row['verify_after']:raise BusinessError(f"Aguarde {ceil(row['verify_after']-now)} segundos antes de conferir outro código.")
        if not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit():raise BusinessError('Informe o código de seis dígitos recebido no e-mail.')
        self.db.conn.execute("UPDATE email_auth_challenges SET state='VERIFYING' WHERE id=?",(challenge.id,))
        generation=self._generation;client=self.client
        def verified(identity):
            if not self._live(challenge,generation):return
            try:
                row=self._row(challenge);now=self._now(persist=True)
                if row['state']!='VERIFYING' or now>=row['expires_at']:raise AuthorizationError('Código vencido. Solicite outro.')
                if not isinstance(identity,VerifiedIdentity) or identity.email!=challenge.email or identity.issuer!=row['issuer'] or (row['expected_subject'] and identity.subject!=row['expected_subject']):raise AuthorizationError('Não foi possível confirmar a identidade deste e-mail.')
                expires=min(now+600,identity.expires_at)
                if expires<=now:raise AuthorizationError('Confirmação vencida. Solicite outro código.')
                proof=EmailProof(secrets.token_urlsafe(32))
                self.db.conn.execute("UPDATE email_auth_challenges SET state='VERIFIED' WHERE id=?",(challenge.id,))
                self._proofs[proof.id]=(proof,challenge,identity,expires,self.monotonic()+min(600,expires-now))
            except BusinessError as error:
                self.db.conn.execute("UPDATE email_auth_challenges SET state='FAILED' WHERE id=?",(challenge.id,));on_error(error);return
            on_success(proof)
        def failed(error):
            if not self._live(challenge,generation):return
            with self.db.transaction():
                now=self._now(persist=True);self._throttle(challenge,error,now)
                wrong=isinstance(error,EmailProviderError) and error.kind=='INVALID_CODE'
                self.db.conn.execute("UPDATE email_auth_challenges SET attempts=attempts+?,state=CASE WHEN attempts+?>=5 THEN 'LOCKED' ELSE 'SENT' END WHERE id=?",(int(wrong),int(wrong),challenge.id))
            on_error(self._safe(error))
        self.runner.submit(lambda:client.verify_code(challenge.email,code),verified,failed)

    def validate(self,proof,purpose):
        self._main()
        saved=self._proofs.get(proof.id) if isinstance(proof,EmailProof) else None
        if not saved or saved[0] is not proof:raise AuthorizationError('Confirme seu e-mail com um novo código.')
        _,challenge,identity,expires,mono_expires=saved
        row=self._row(challenge)
        if challenge.purpose!=purpose or row['state']!='VERIFIED' or self._now(persist=True)>=expires or self.monotonic()>=mono_expires:raise AuthorizationError('Confirmação vencida ou já utilizada. Solicite outro código.')
        return identity

    def consume(self,proof,purpose):
        if not self.db.conn.in_transaction:raise RuntimeError('Confirmação exige transação aberta.')
        self.validate(proof,purpose)
        challenge=self._proofs[proof.id][1]
        self.db.conn.execute("UPDATE email_auth_challenges SET state='COMPLETED' WHERE id=?",(challenge.id,))
