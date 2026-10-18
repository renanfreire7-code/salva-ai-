"""Adapter OTP do Supabase. Somente rede: nunca usa banco ou widgets."""
from datetime import datetime
import json,re,time
from urllib.request import Request,build_opener,HTTPRedirectHandler,HTTPSHandler
from urllib.error import HTTPError,URLError
from uuid import UUID
from .email_models import VerifiedIdentity,EmailProviderError
from ..common.errors import BusinessError

LIMIT=1048576


def normalize_email(value):
    value=value.strip().casefold() if isinstance(value,str) else ''
    if len(value)>254 or not re.fullmatch(r'[^\s@<>\x00-\x1f]+@[^\s@<>\x00-\x1f]+\.[^\s@<>\x00-\x1f]+',value):
        raise BusinessError('Informe um e-mail válido.')
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def _transport(method,url,headers,body):
    request=Request(url,data=body,headers=headers,method=method)
    opener=build_opener(_NoRedirect(),HTTPSHandler())
    try:
        with opener.open(request,timeout=10) as response:
            return response.status,dict(response.headers),response.read(LIMIT+1)
    except HTTPError as error:
        with error:return error.code,dict(error.headers),error.read(LIMIT+1)


class SupabaseOTPClient:
    def __init__(self,config,transport=None):
        self.config=config;self.transport=transport or _transport

    def _call(self,method,path,data=None,token=None):
        headers={'apikey':self.config.publishable_key,'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        body=json.dumps(data).encode() if data is not None else None
        try:status,response_headers,raw=self.transport(method,self.config.url+path,headers,body)
        except (OSError,URLError,TimeoutError):raise EmailProviderError('NETWORK') from None
        if status==429:
            try:wait=max(60,min(86400,int(next((v for k,v in response_headers.items() if k.lower()=='retry-after'),'60'))))
            except (ValueError,TypeError):wait=60
            raise EmailProviderError('RATE_LIMIT',wait)
        if status in (400,403,422) and path=='/auth/v1/verify':raise EmailProviderError('INVALID_CODE')
        if status in (400,401,403,422):raise EmailProviderError('CONFIG')
        if status<200 or status>=300 or len(raw)>LIMIT:raise EmailProviderError('RESPONSE')
        try:
            result=json.loads(raw)
            if not isinstance(result,dict):raise ValueError()
            return result
        except (ValueError,TypeError,UnicodeError):raise EmailProviderError('RESPONSE') from None

    def send_code(self,email,*,create_user):
        self._call('POST','/auth/v1/otp',{'email':normalize_email(email),'create_user':bool(create_user)})

    def verify_code(self,email,code):
        email=normalize_email(email)
        if not isinstance(code,str) or not re.fullmatch('[0-9]{6}',code):raise EmailProviderError('INVALID_CODE')
        session=self._call('POST','/auth/v1/verify',{'email':email,'token':code,'type':'email'})
        token=session.get('access_token');ttl=session.get('expires_in')
        if not isinstance(token,str) or not token or not isinstance(session.get('token_type'),str) or session['token_type'].lower()!='bearer' or isinstance(ttl,bool) or not isinstance(ttl,(int,float)) or not 0<ttl<=86400:
            raise EmailProviderError('RESPONSE')
        identity=self._call('GET','/auth/v1/user',token=token)
        try:
            subject=str(UUID(identity['id']))
            returned_email=normalize_email(identity['email'])
            confirmed=datetime.fromisoformat(identity['email_confirmed_at'].replace('Z','+00:00'))
            initial=session['user']
            if confirmed.tzinfo is None or returned_email!=email or str(UUID(initial['id']))!=subject or normalize_email(initial['email'])!=email:raise ValueError()
        except (KeyError,ValueError,TypeError,AttributeError,BusinessError):raise EmailProviderError('RESPONSE') from None
        return VerifiedIdentity(subject,email,self.config.url,confirmed.timestamp(),time.time()+ttl)
