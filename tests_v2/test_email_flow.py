from copy import copy
from tests_v2.support import DatabaseCase
from tests_v2.email_support import EmailHarness,EMAIL,SUBJECT,URL,user,session
from salva_ai_v2.security.service import SecurityService
from salva_ai_v2.security.accounts import AccountService
from salva_ai_v2.common.errors import BusinessError


class EmailFlowTest(DatabaseCase):
    def setUp(self):
        super().setUp();self.security=SecurityService(self.db,self.clock)
        self.accounts=AccountService(self.db,self.security,self.clock);self.accounts.create('bar','Senha fictícia 42','007')
        self.h=EmailHarness(self.db,self.clock);self.flow=self.h.flow
    def bind(self):
        self.db.conn.execute('UPDATE establishment_account SET email=?,email_subject=?,email_issuer=?,email_verified_at=? WHERE id=1',(EMAIL,SUBJECT,URL,self.clock.now().isoformat()))

    def test_email_identity_is_bound_to_purpose_revision_and_issuer(self):
        with self.assertRaises(BusinessError):self.flow.request_code(EMAIL,'SETUP',lambda x:None,lambda x:None)
        self.bind()
        for purpose,email in [('ENROLL',EMAIL),('RECOVER','other@example.com')]:
            with self.subTest(purpose=purpose),self.assertRaises(BusinessError):self.flow.request_code(email,purpose,lambda x:None,lambda x:None)
        challenge=self.h.request('RECOVER')
        with self.assertRaises(BusinessError):self.h.verify(challenge,identity=user(id='00000000-0000-4000-8000-000000000002'))
        self.h.advance(61);proof=self.h.proof('RECOVER')
        self.assertEqual(self.flow.validate(proof,'RECOVER').subject,SUBJECT)
        self.db.conn.execute("UPDATE establishment_account SET email_issuer='https://another.supabase.co'")
        with self.assertRaises(BusinessError):self.flow.validate(proof,'RECOVER')

    def test_proof_cannot_be_forged_replayed_or_reused_after_revision_change(self):
        from salva_ai_v2.security.email_models import EmailProof
        proof=self.h.proof()
        for fake in (EmailProof(proof.id),copy(proof)):
            with self.assertRaises(BusinessError):self.flow.validate(fake,'ENROLL')
        with self.assertRaises(BusinessError):self.flow.validate(proof,'RECOVER')
        with self.db.transaction():self.flow.consume(proof,'ENROLL')
        with self.assertRaises(BusinessError):self.flow.validate(proof,'ENROLL')
        self.h.advance(61);proof=self.h.proof();self.db.conn.execute('UPDATE establishment_account SET revision=revision+1')
        with self.assertRaises(BusinessError):self.flow.validate(proof,'ENROLL')

    def test_wait_and_attempts_survive_restart_and_clock_rollback(self):
        challenge=self.h.request();self.assertEqual(self.flow.remaining_wait(EMAIL),60)
        self.clock.advance(-100);self.h.tick+=30
        self.assertEqual(self.flow.remaining_wait(EMAIL),30)
        with self.assertRaises(BusinessError):self.h.request()
        # Incorrect codes are confirmed by the provider; transport failures do not count.
        for n in range(5):
            self.h.transport.responses.append((403,{},{}));errors=[]
            self.flow.verify_code(challenge,'111111',lambda x:self.fail('Incorrect OTP accepted'),errors.append)
            self.h.runner.run_next();self.assertTrue(errors)
        self.assertEqual(self.scalar('SELECT attempts FROM email_auth_challenges WHERE id=?',(challenge.id,)),5)
        with self.assertRaises(BusinessError):self.flow.verify_code(challenge,'654321',lambda x:None,lambda x:None)
        restarted=EmailHarness(self.db,self.clock)
        self.assertGreater(restarted.flow.remaining_wait(EMAIL),0)

    def test_live_proof_expires_after600_monotonic_seconds(self):
        proof=self.h.proof();self.clock.advance(-3600);self.h.tick+=601
        with self.assertRaises(BusinessError):self.flow.validate(proof,'ENROLL')

    def test_late_callback_after_cancel_cannot_issue_proof(self):
        challenge=self.h.request();self.h.transport.responses.extend([(200,{},session()),(200,{},user())])
        result=[];errors=[];self.flow.verify_code(challenge,'654321',result.append,errors.append)
        self.flow.invalidate_all();self.h.runner.run_next()
        self.assertEqual(result,[])
        self.assertEqual(self.scalar('SELECT state FROM email_auth_challenges WHERE id=?',(challenge.id,)),'CANCELED')

    def test_timeout_does_not_change_credentials_or_claim_confirmation(self):
        before=tuple(self.db.conn.execute('SELECT * FROM establishment_account').fetchone())
        self.h.transport.responses.append(TimeoutError('fictitious secret'));results=[];errors=[]
        self.flow.request_code(EMAIL,'ENROLL',results.append,errors.append);self.h.runner.run_next()
        self.assertTrue(errors);self.assertEqual(results,[])
        self.assertEqual(before,tuple(self.db.conn.execute('SELECT * FROM establishment_account').fetchone()))
        self.assertGreater(self.flow.remaining_wait(EMAIL),0)

    def test_consumption_rolls_back_and_restart_invalidates_local_proof(self):
        proof=self.h.proof()
        with self.assertRaises(RuntimeError):
            with self.db.transaction():self.flow.consume(proof,'ENROLL');raise RuntimeError('disk')
        self.flow.validate(proof,'ENROLL')
        EmailHarness(self.db,self.clock)
        with self.assertRaises(BusinessError):self.flow.validate(proof,'ENROLL')

    def test_provider_throttle_limits_verification_without_counting_bad_code(self):
        challenge=self.h.request();self.h.transport.responses.append((429,{'Retry-After':'90'},{}));errors=[]
        self.flow.verify_code(challenge,'654321',lambda x:None,errors.append);self.h.runner.run_next()
        self.assertTrue(errors)
        self.assertEqual(self.scalar('SELECT attempts FROM email_auth_challenges WHERE id=?',(challenge.id,)),0)
        self.assertGreaterEqual(self.flow.remaining_wait(EMAIL),90)
        with self.assertRaises(BusinessError):self.flow.verify_code(challenge,'654321',lambda x:None,lambda x:None)
