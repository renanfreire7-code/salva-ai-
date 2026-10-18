"""Contratos de rede; nenhum token do provedor é uma prova local."""
from dataclasses import dataclass,field
from typing import Protocol,Callable
from ..common.errors import BusinessError


@dataclass(frozen=True)
class VerifiedIdentity:
    subject:str
    email:str
    issuer:str
    verified_at:float
    expires_at:float


@dataclass(frozen=True,eq=False)
class EmailChallenge:
    id:str=field(repr=False)
    purpose:str
    email:str
    account_revision:int|None


@dataclass(frozen=True,eq=False)
class EmailProof:
    id:str=field(repr=False)


class EmailProviderError(BusinessError):
    def __init__(self,kind,retry_after_seconds=0):
        self.kind=kind;self.retry_after_seconds=retry_after_seconds
        messages={'INVALID_CODE':'Código inválido ou vencido. Confira ou solicite outro.',
                  'RATE_LIMIT':'Aguarde antes de solicitar ou conferir outro código.',
                  'CONFIG':'Confira a configuração do serviço de e-mail e do remetente.',
                  'NETWORK':'Não foi possível conectar ao serviço de e-mail. Tente novamente.',
                  'RESPONSE':'Não foi possível confirmar a resposta do serviço de e-mail.'}
        super().__init__(messages.get(kind,messages['RESPONSE']))


class NetworkRunner(Protocol):
    def submit(self,job:Callable,on_success:Callable,on_error:Callable)->str:...
    def close(self)->None:...
