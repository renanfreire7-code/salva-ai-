import hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from tests_v2.application_support import build_credential_application as build_application
from salva_ai_v2.common.errors import BusinessError
from tests_v2.test_access_end_to_end import seed_previous_store
from tests_v2.email_support import EmailHarness
from tests_v2.support import FakeClock
from tests_v2.test_email_provider import EMAIL
from salva_ai_v2.sales.models import Payment
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.inventory.models import CartLine


class EmailEndToEndTests(unittest.TestCase):
    def test_populated032_reenrollment_offline_sales_recovery_and_restore(self):
        with tempfile.TemporaryDirectory(prefix='bar preservado ') as folder:
            root=Path(folder);old=seed_previous_store(root)
            # Finish old account transition before upgrading this populated fixture to017.
            from salva_ai_v2.common.db import Database
            from salva_ai_v2.security.accounts import AccountService
            from salva_ai_v2.security.service import SecurityService
            db=Database(root/'dados'/'salva_ai.sqlite3')
            for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
                if not '015'<=migration.name<'017':continue
                data=migration.read_bytes();db.conn.executescript(data.decode());db.conn.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(data).hexdigest()))
            security=SecurityService(db);AccountService(db,security).create('old','old-password','007',security.authorize('681942','access.configure'));db.close()
            app=build_application(root)
            try:
                h=EmailHarness(app.db,FakeClock());app.emails=h.flow;app.accounts.emails=h.flow;app.require_login()
                tables=('products','orders','order_items','sales','cash_sessions','cash_entries')
                def snapshot():return {t:[tuple(r) for r in app.db.conn.execute('SELECT * FROM '+t)] for t in tables}
                before=snapshot();pin=app.db.conn.execute('SELECT pin_hash FROM admin_credentials').fetchone()[0]
                app.accounts.reenroll_with_email(h.proof(),'new','new-password','007');self.assertEqual(before,snapshot())
                backup=app.backups.create('manual','email-before-ops').path
                app.unlock(app.accounts.login('new','new-password'));s=app.services
                # Business operations have no provider dependency.
                h.client.transport=lambda *a,**kw:self.fail('Unexpected network during offline operation')
                cart=s.sales.create_cart('newcart');s.sales.set_cart_qty(cart,old['pid'],1,'newqty');s.sales.sell(cart,Payment('PIX'),'newsale')
                tab=s.sales.create_tab('31 / Cliente','tab');s.sales.set_tab_qty(tab,old['pid'],1,None,None,'tabqty')
                s.delivery.configure_fees(500,700,'fees')
                draft=DeliveryDraft('Cliente','11999990000','Rua de teste, 10','Portão azul',[CartLine(old['pid'],1)],'PIX','BAR')
                s.delivery.confirm(draft,'delivery')
                after=snapshot();h.client.transport=h.transport;h.advance(61)
                previous=app.accounts.login('new','new-password')
                app.accounts.recover_with_email(h.proof('RECOVER'),'recovered','recovered-password')
                self.assertEqual(after,snapshot());self.assertEqual(pin,app.db.conn.execute('SELECT pin_hash FROM admin_credentials').fetchone()[0])
                with self.assertRaises(BusinessError):app.accounts.validate_session(previous)
                app.require_login();app.unlock(app.accounts.login('recovered','recovered-password'))
                h.advance(61);errors=[];h.flow.request_code(EMAIL,'RECOVER',lambda _:self.fail('Late callback after restore'),errors.append)
                from tests_v2.test_email_provider import user
                h.transport.responses.append((200,{},{}))
                preview=app.services.restore.prepare(backup,app.security.authorize('007','backup.restore'));app.services.restore.apply(preview,True)
                h.runner.run_next();self.assertEqual(errors,[]);self.assertFalse(app.authenticated)
                app.accounts.login('new','new-password');self.assertEqual(before,snapshot())
            finally:app.close()

    def test_atomic_failure_retry_and_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            app=build_application(Path(folder))
            try:
                h=EmailHarness(app.db,FakeClock());app.emails=h.flow;app.accounts.emails=h.flow
                app.accounts.create('old','old-password','007');active=app.accounts.login('old','old-password')
                proof=h.proof();app.db.conn.execute("CREATE TRIGGER fail_access BEFORE UPDATE OF username ON establishment_account BEGIN SELECT RAISE(ABORT,'fixture'); END")
                with self.assertRaises(sqlite3.Error):app.accounts.reenroll_with_email(proof,'new','new-password','007')
                app.accounts.validate_session(active);h.flow.validate(proof,'ENROLL')
                app.close();app=build_application(Path(folder))
                fresh=EmailHarness(app.db,FakeClock());app.emails=fresh.flow;app.accounts.emails=fresh.flow
                app.accounts.login('old','old-password')
                with self.assertRaises(BusinessError):app.accounts.reenroll_with_email(proof,'new','new-password','007')
                app.db.conn.execute('DROP TRIGGER fail_access');fresh.advance(61)
                app.accounts.reenroll_with_email(fresh.proof(),'new','new-password','007')
                app.accounts.login('new','new-password');app.security.authorize('007','fixture')
            finally:app.close()
