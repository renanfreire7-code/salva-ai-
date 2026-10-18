import hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from salva_ai_v2.common.db import Database,APPLICATION_ID
from salva_ai_v2.common.errors import AuthorizationError
from tests_v2.security_support import seed_legacy_pin


def seed_previous_store(root):
    path=Path(root)/'dados'/'salva_ai.sqlite3';path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path)
    for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
        if migration.name>'014_service_experience.sql':continue
        sql=migration.read_text();conn.executescript(sql)
        conn.execute('INSERT INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(sql.encode()).hexdigest()))
    conn.execute(f'PRAGMA application_id={APPLICATION_ID}');conn.commit();conn.close()
    db=Database(path)
    try:
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.inventory.models import PurchaseLine
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.pricing.service import PricingService
        from salva_ai_v2.sales.service import SalesService
        from salva_ai_v2.sales.models import Payment
        key=seed_legacy_pin(db);security=SecurityService(db);inventory=InventoryService(db,security);cash=CashService(db,security)
        pricing=PricingService(db);sales=SalesService(db,inventory,pricing,cash,security)
        pid=inventory.create_product('Cerveja Heineken Latão',500,12,6,'p')
        inventory.receive_purchase([PurchaseLine(pid,20,4000)],0,db.clock.today(),db.clock.today(),'buy')
        session=cash.open(10000,'open');cart=sales.create_cart('cart');sales.set_cart_qty(cart,pid,1,'qty')
        sale=sales.sell(cart,Payment('PIX'),'sale')
        return dict(pid=pid,session=session,sale=sale.id,key=key)
    finally:db.close()


class AccessEndToEndTest(unittest.TestCase):
    def test_populated_v02_upgrade_login_sensitive_action_restart_recovery_restore(self):
        from salva_ai_v2.bootstrap import build_application
        with tempfile.TemporaryDirectory(prefix='bar com acentuação ') as directory:
            root=Path(directory);old=seed_previous_store(root);app=build_application(root)
            try:
                self.assertEqual(app.accounts.mode,'TRANSITION');self.assertEqual(app.views,[])
                from salva_ai_v2.maintenance.backup import BackupService
                backups=BackupService(app.db,root/'backups');source=backups.list_backups()[0]
                self.assertTrue(backups.verify(source).integrity_ok)
                proof=app.security.authorize('681942','access.configure')
                key=app.accounts.create('bar','12345678','007',proof)
                app.unlock(app.accounts.login('bar','12345678'));s=app.services
                self.assertEqual(s.inventory.position(old['pid']).physical,19)
                self.assertEqual(s.cash.position(old['session']).expected_cents,10000)
                self.assertEqual(s.commerce.detail(f"sale:{old['sale']}")['items'][0].name,'Cerveja Heineken Latão')
                grant=app.security.authorize('007','product.edit')
                s.inventory.update_product(old['pid'],'Nome novo',500,12,6,grant,'Nome corrigido','edit')
                with self.assertRaises(AuthorizationError):app.security.validate(grant,'product.edit')
                app.close();app=build_application(root);self.assertFalse(app.authenticated)
                newkey=app.accounts.recover(key,'Outra senha 42','009');self.assertNotEqual(key,newkey)
                app.unlock(app.accounts.login('bar','Outra senha 42'));s=app.services
                preview=s.restore.prepare(source,app.security.authorize('009','backup.restore'));s.restore.apply(preview,True)
                self.assertFalse(app.authenticated);self.assertEqual(app.accounts.mode,'TRANSITION')
                self.assertEqual(app.security.pin_length,6);app.security.authorize('681942','product.edit')
                self.assertEqual(app.db.conn.execute('SELECT stock FROM products WHERE id=?',(old['pid'],)).fetchone()[0],19)
                self.assertEqual(app.db.conn.execute('SELECT count(*) FROM sales').fetchone()[0],1)
            finally:app.close()

    def test_abandoned_setup_is_retryable(self):
        from salva_ai_v2.bootstrap import build_application
        with tempfile.TemporaryDirectory() as directory:
            app=build_application(Path(directory));app.access_view.wizard.inputs['email'].insert(0,'draft@example.com');app.close()
            app=build_application(Path(directory))
            try:self.assertEqual(app.accounts.mode,'SETUP');self.assertFalse(app.security.configured)
            finally:app.close()
