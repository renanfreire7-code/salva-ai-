"""Uma conta local; sessões em memória e transição de credenciais atômica."""
import hmac
import secrets
from math import ceil
from .models import LoginSession
from .service import ITERATIONS
from ..common.audit import Audit
from ..common.errors import BusinessError,AuthorizationError


class AccountService:
    def __init__(self,db,security,clock=None,*,emails=None,backups=None):
        self.db,self.security,self.clock=db,security,clock or db.clock
        self._sessions={}
        self.emails,self.backups=emails,backups

    @property
    def configured(self):
        return self.db.conn.execute('SELECT 1 FROM establishment_account WHERE id=1').fetchone() is not None

    @property
    def mode(self):
        return 'LOGIN' if self.configured else 'TRANSITION' if self.security.configured else 'SETUP'

    def _password(self,password):
        if not isinstance(password,str) or len(password)<8:
            raise BusinessError('Use uma senha com pelo menos oito caracteres.')

    def _username(self,username):
        username=username.strip().casefold() if isinstance(username,str) else ''
        if not 1<=len(username)<=64:raise BusinessError('Informe um usuário com até 64 caracteres.')
        return username

    def create(self,username,password,pin,proof=None):
        username=self._username(username)
        self._password(password);self.security._pin(pin)
        salt=secrets.token_bytes(16)
        with self.db.transaction():
            if self.configured:raise BusinessError('A conta do estabelecimento já foi criada.')
            if self.security.configured:
                key=self.security.replace_pin(pin,proof,'access.configure')
            else:key=self.security.setup(pin)
            self.db.conn.execute('INSERT INTO establishment_account(id,username,salt,password_hash,iterations) VALUES(1,?,?,?,?)',
                (username,salt,self.security._hash(password,salt),ITERATIONS))
            Audit(self.db).record('access.created','establishment',{}, {'configured':True},None)
        self.logout()
        return key

    def remaining_wait(self):
        row=self.db.conn.execute('SELECT blocked_until,last_time FROM establishment_account WHERE id=1').fetchone()
        return max(0,ceil(row['blocked_until']-max(self.clock.now().timestamp(),row['last_time']))) if row else 0

    def login(self,username,password):
        error=None
        with self.db.transaction():
            row=self.db.conn.execute('SELECT * FROM establishment_account WHERE id=1').fetchone()
            if not row:raise AuthorizationError('Configure a conta do estabelecimento.')
            now=max(self.clock.now().timestamp(),row['last_time'])
            self.db.conn.execute('UPDATE establishment_account SET last_time=? WHERE id=1',(now,))
            if now<row['blocked_until']:error='Aguarde antes de tentar novamente.'
            else:
                user=username.strip().casefold() if isinstance(username,str) else ''
                hashed=self.security._hash(password if isinstance(password,str) else '',row['salt'],row['iterations'])
                if not hmac.compare_digest(hashed,row['password_hash']) or user!=row['username']:
                    failures=row['failures']+1;wait=min(900,30*2**min(max(0,failures-5),5)) if failures>=5 else 0
                    self.db.conn.execute('UPDATE establishment_account SET failures=?,blocked_until=? WHERE id=1',(failures,now+wait))
                    error='Usuário ou senha incorretos.'
                else:self.db.conn.execute('UPDATE establishment_account SET failures=0,blocked_until=0 WHERE id=1')
        if error:raise AuthorizationError(error)
        session=LoginSession(secrets.token_urlsafe(32),row['revision']);self._sessions[session.id]=session
        return session

    def validate_session(self,session):
        row=self.db.conn.execute('SELECT revision FROM establishment_account WHERE id=1').fetchone()
        if not isinstance(session,LoginSession) or self._sessions.get(session.id) is not session or not row or row['revision']!=session.revision:
            raise AuthorizationError('Entre novamente no Bar Simples.')

    def logout(self):
        self._sessions.clear();self.security._grants.clear()

    def recover(self,recovery_key,new_password,new_pin,*,new_username=None):
        username=self._username(new_username) if new_username is not None else None
        self._password(new_password);self.security._pin(new_pin)
        salt=secrets.token_bytes(16)
        with self.db.transaction():
            if not self.configured:raise AuthorizationError('Conclua a configuração do acesso.')
            key=self.security.recover(recovery_key,new_pin)
            self.db.conn.execute('UPDATE establishment_account SET username=COALESCE(?,username),salt=?,password_hash=?,iterations=?,revision=revision+1,failures=0,blocked_until=0 WHERE id=1',
                (username,salt,self.security._hash(new_password,salt),ITERATIONS))
            Audit(self.db).record('access.recovered','establishment',{}, {'recovery_key_rotated':True,'username_redefined':username is not None},None)
        self.logout();return key

    def _email_identity(self,proof,purpose):
        if self.emails is None:raise BusinessError('Configure o serviço de e-mail antes de continuar.')
        return self.emails.validate(proof,purpose)

    def _bind_email(self,identity):
        from datetime import datetime,timezone
        self.db.conn.execute('UPDATE establishment_account SET email=?,email_subject=?,email_issuer=?,email_verified_at=? WHERE id=1',
            (identity.email,identity.subject,identity.issuer,datetime.fromtimestamp(identity.verified_at,timezone.utc).isoformat()))

    def _finish_email_change(self):
        self.logout();self.emails.invalidate_all()

    def create_with_email(self,proof,username,password,pin,legacy_proof=None):
        self._username(username);self._password(password);self.security._pin(pin)
        identity=self._email_identity(proof,'SETUP')
        with self.db.transaction():
            self.emails.consume(proof,'SETUP')
            # Existing create clears sessions only for an unconfigured account.
            key=self.create(username,password,pin,legacy_proof)
            self._bind_email(identity)
        self._finish_email_change()
        return key

    def reenroll_with_email(self,proof,username,password,current_pin):
        from uuid import uuid4
        username=self._username(username);self._password(password)
        identity=self._email_identity(proof,'ENROLL')
        if self.backups is None:raise BusinessError('O backup é necessário antes de refazer o acesso.')
        initial=self.security.authorize(current_pin,'access.reenroll')
        self.security._grants.pop(initial.id,None)
        backup=self.backups.create('antes_recadastro',str(uuid4()))
        self.backups.verify(backup.path)
        grant=self.security.authorize(current_pin,'access.reenroll')
        salt=secrets.token_bytes(16)
        with self.db.transaction():
            self.emails.consume(proof,'ENROLL')
            self.security.consume(grant,'access.reenroll')
            self.db.conn.execute('UPDATE establishment_account SET username=?,salt=?,password_hash=?,iterations=?,revision=revision+1,failures=0,blocked_until=0 WHERE id=1',
                (username,salt,self.security._hash(password,salt),ITERATIONS))
            self._bind_email(identity)
            Audit(self.db).record('access.email_enrolled','establishment',{}, {'email_confirmed':True},None)
        self._finish_email_change()

    def recover_with_email(self,proof,username,password):
        username=self._username(username);self._password(password)
        self._email_identity(proof,'RECOVER');salt=secrets.token_bytes(16)
        with self.db.transaction():
            self.emails.consume(proof,'RECOVER')
            self.db.conn.execute('UPDATE establishment_account SET username=?,salt=?,password_hash=?,iterations=?,revision=revision+1,failures=0,blocked_until=0 WHERE id=1',
                (username,salt,self.security._hash(password,salt),ITERATIONS))
            Audit(self.db).record('access.email_recovered','establishment',{}, {'email_confirmed':True},None)
        self._finish_email_change()
