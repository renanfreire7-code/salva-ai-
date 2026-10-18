"""Transporte controlado só em testes; as provas passam pelo fluxo de rede real."""
from salva_ai_v2.security.email_config import SupabaseConfig
from salva_ai_v2.security.email_provider import SupabaseOTPClient
from tests_v2.test_email_config import URL,KEY
from tests_v2.test_email_provider import FakeTransport,EMAIL,SUBJECT,user,session


class ManualRunner:
    def __init__(self):self.jobs=[];self.closed=False
    def submit(self,job,on_success,on_error):
        self.jobs.append((job,on_success,on_error));return str(len(self.jobs))
    def run_next(self):
        job,success,error=self.jobs.pop(0)
        try:result=job()
        except Exception as caught:error(caught)
        else:success(result)
    def close(self):self.closed=True;self.jobs.clear()


class EmailHarness:
    def __init__(self,db,clock):
        from salva_ai_v2.security.email_flow import EmailAccessService
        self.transport=FakeTransport();self.runner=ManualRunner();self.tick=0.;self.clock=clock
        self.client=SupabaseOTPClient(SupabaseConfig(URL,KEY),transport=self.transport)
        self.flow=EmailAccessService(db,self.client,self.runner,clock=clock,monotonic=lambda:self.tick)
    def advance(self,seconds):self.tick+=seconds;self.clock.advance(seconds)
    def request(self,purpose='ENROLL',email=EMAIL):
        results=[];errors=[]
        self.flow.request_code(email,purpose,results.append,errors.append)
        self.transport.responses.append((200,{},{}));self.runner.run_next()
        if errors:raise errors[0]
        return results[0]
    def verify(self,challenge,*,identity=None):
        self.transport.responses.extend([(200,{},session()),(200,{},identity or user())]);results=[];errors=[]
        self.flow.verify_code(challenge,'654321',results.append,errors.append);self.runner.run_next()
        if errors:raise errors[0]
        return results[0]
    def proof(self,purpose='ENROLL',email=EMAIL):return self.verify(self.request(purpose,email))
