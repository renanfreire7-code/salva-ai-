import json,unittest,ssl
from datetime import datetime,timezone
from tests_v2.test_email_config import URL,KEY
from salva_ai_v2.common.errors import BusinessError

SUBJECT='00000000-0000-4000-8000-000000000001'
EMAIL='operator@example.com'
TOKEN='fictitious-session-token'


def user(**changes):
    result={'id':SUBJECT,'email':EMAIL,'email_confirmed_at':'2026-10-17T12:00:00Z'};result.update(changes);return result


def session(**changes):
    result={'access_token':TOKEN,'token_type':'bearer','expires_in':3600,'user':user()};result.update(changes);return result


class FakeTransport:
    def __init__(self,*responses):self.responses=list(responses);self.calls=[]
    def __call__(self,method,url,headers,body):
        self.calls.append((method,url,headers,json.loads(body) if body else None))
        result=self.responses.pop(0)
        if isinstance(result,Exception):raise result
        status,extra,data=result
        return status,extra,json.dumps(data).encode() if not isinstance(data,bytes) else data


class EmailProviderTest(unittest.TestCase):
    def client(self,transport):
        from salva_ai_v2.security.email_provider import SupabaseOTPClient
        from salva_ai_v2.security.email_config import SupabaseConfig
        return SupabaseOTPClient(SupabaseConfig(URL,KEY),transport=transport)

    def test_request_has_only_email_and_creation_policy(self):
        transport=FakeTransport((200,{},{}));self.client(transport).send_code(EMAIL,create_user=False)
        method,url,headers,body=transport.calls[0]
        self.assertEqual((method,url),('POST',URL+'/auth/v1/otp'))
        self.assertEqual(body,{'email':EMAIL,'create_user':False});self.assertEqual(headers['apikey'],KEY)

    def test_verify_requires_authoritative_confirmed_user(self):
        transport=FakeTransport((200,{},session()),(200,{},user()))
        identity=self.client(transport).verify_code(EMAIL,'654321')
        self.assertEqual((identity.subject,identity.email,identity.issuer),(SUBJECT,EMAIL,URL))
        self.assertEqual(transport.calls[0][3],{'email':EMAIL,'token':'654321','type':'email'})
        self.assertEqual(transport.calls[1][0:2],('GET',URL+'/auth/v1/user'))
        self.assertEqual(transport.calls[1][2]['Authorization'],'Bearer '+TOKEN)
        self.assertNotIn(TOKEN,repr(identity))

    def test_forged_metadata_other_email_and_uid_are_rejected(self):
        variants=[user(email_confirmed_at=None,user_metadata={'email_verified':True}),user(email='another@example.com'),user(id='00000000-0000-4000-8000-000000000002'),user(id='invalid')]
        for data in variants:
            with self.subTest(data=data),self.assertRaises(BusinessError):
                self.client(FakeTransport((200,{},session()),(200,{},data))).verify_code(EMAIL,'654321')
        for data in (session(access_token=''),session(token_type='other'),session(token_type=None),session(expires_in=-1)):
            with self.subTest(data=data),self.assertRaises(BusinessError):self.client(FakeTransport((200,{},data))).verify_code(EMAIL,'654321')

    def test_network_failures_never_expose_payloads(self):
        from salva_ai_v2.security.email_models import EmailProviderError
        for response in ((401,{}, {'error':TOKEN}),(429,{'Retry-After':'90'},{'error':'654321'}),(302,{'Location':'https://evil.example'},{}),(200,{},b'invalid json '+TOKEN.encode()),(200,{},b'x'*(1048576+1)),TimeoutError(TOKEN),ssl.SSLError(TOKEN)):
            with self.subTest(response=str(response)[:30]):
                with self.assertRaises(EmailProviderError) as caught:self.client(FakeTransport(response)).verify_code(EMAIL,'654321')
                text=str(caught.exception);self.assertNotIn(TOKEN,text);self.assertNotIn('654321',text)
                if isinstance(response,tuple) and response[0]==429:self.assertEqual(caught.exception.retry_after_seconds,90)

    def test_bad_code_is_local_validation_not_network(self):
        transport=FakeTransport()
        for code in ('12345','abcdef','１２３４５６','654321 '):
            with self.assertRaises(BusinessError):self.client(transport).verify_code(EMAIL,code)
        self.assertEqual(transport.calls,[])
