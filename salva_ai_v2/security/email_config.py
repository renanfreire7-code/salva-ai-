"""Somente URL/chave pública; segredos de envio pertencem ao serviço online."""
import base64,json,os,re,tempfile
from dataclasses import dataclass,field
from pathlib import Path
from ..common.errors import BusinessError


@dataclass(frozen=True)
class SupabaseConfig:
    url:str
    publishable_key:str=field(repr=False)

    def __post_init__(self):
        url=self.url.strip().rstrip('/') if isinstance(self.url,str) else ''
        key=self.publishable_key.strip() if isinstance(self.publishable_key,str) else ''
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url):
            raise BusinessError('Informe a URL HTTPS do projeto Supabase, sem outros caminhos.')
        public=bool(re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]{24,}',key))
        if not public:
            try:
                parts=key.split('.')
                payload=json.loads(base64.urlsafe_b64decode(parts[1]+'='*(-len(parts[1])%4))) if len(parts)==3 else {}
                public=payload.get('role')=='anon'
            except (ValueError,TypeError,IndexError,AttributeError):public=False
        if not public:raise BusinessError('Use somente a chave publishable ou anon pública do projeto.')
        object.__setattr__(self,'url',url);object.__setattr__(self,'publishable_key',key)


def _check_issuer(config,bound_issuer):
    if bound_issuer and config.url!=bound_issuer:
        raise BusinessError('Este e-mail está vinculado a outro projeto. A configuração anterior foi preservada.')
    return config


def load_email_config(path,bound_issuer=None):
    path=Path(path)
    if not path.exists():return None
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or set(data)!={'url','publishable_key'}:raise ValueError()
        return _check_issuer(SupabaseConfig(**data),bound_issuer)
    except (OSError,ValueError,TypeError) as error:
        raise BusinessError('Não foi possível ler a configuração pública de e-mail.') from None


def save_email_config(path,config,bound_issuer=None):
    _check_issuer(config,bound_issuer);path=Path(path);temporary=None
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.auth_service.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump({'url':config.url,'publishable_key':config.publishable_key},stream,indent=2)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    except OSError:
        raise BusinessError('Não foi possível salvar a configuração. A anterior foi preservada.') from None
    finally:
        if temporary and temporary.exists():
            try:temporary.unlink()
            except OSError:pass
