import hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from salva_ai_v2.common.db import Database,APPLICATION_ID
from salva_ai_v2.maintenance.backup import BackupService
from salva_ai_v2.security.accounts import AccountService
from salva_ai_v2.security.service import SecurityService


class EmailUpgradeTest(unittest.TestCase):
    def test_upgrade016_preserves_account_pin_and_business_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'dados'/'salva_ai.sqlite3';path.parent.mkdir()
            conn=sqlite3.connect(path)
            for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
                if migration.name>'016_delivery_complement.sql':continue
                data=migration.read_bytes();conn.executescript(data.decode())
                conn.execute('INSERT INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(data).hexdigest()))
            conn.execute(f'PRAGMA application_id={APPLICATION_ID}');conn.commit();conn.close()
            db=Database(path)
            try:
                security=SecurityService(db);AccountService(db,security).create('bar','Senha fictícia 42','007')
                from salva_ai_v2.inventory.service import InventoryService
                from salva_ai_v2.inventory.models import PurchaseLine
                from salva_ai_v2.cash.service import CashService
                from salva_ai_v2.pricing.service import PricingService
                from salva_ai_v2.sales.service import SalesService
                from salva_ai_v2.sales.models import Payment
                inv=InventoryService(db,security);pid=inv.create_product('Produto preservado',500,1,0,'product')
                inv.receive_purchase([PurchaseLine(pid,10,2000)],0,db.clock.today(),db.clock.today(),'purchase')
                cash=CashService(db,security);cash.open(10000,'cash');sales=SalesService(db,inv,PricingService(db),cash,security)
                cart=sales.create_cart('cart');sales.set_cart_qty(cart,pid,1,'qty');sales.sell(cart,Payment('PIX'),'sale')
                tables=('products','orders','order_items','sales','cash_sessions','admin_credentials')
                before={t:[tuple(r) for r in db.conn.execute('SELECT * FROM '+t)] for t in tables}
                oldaccount=tuple(db.conn.execute('SELECT * FROM establishment_account').fetchone())
                backups=BackupService(db,root/'backups');db.upgrade(backups)
                self.assertIn('email',{r[1] for r in db.conn.execute('PRAGMA table_info(establishment_account)')})
                for table in tables:self.assertEqual(before[table],[tuple(r) for r in db.conn.execute('SELECT * FROM '+table)],table)
                account=db.conn.execute('SELECT * FROM establishment_account').fetchone()
                self.assertEqual(tuple(account)[:len(oldaccount)],oldaccount)
                self.assertIsNone(account['email']);self.assertIsNone(account['email_subject'])
                self.assertTrue(backups.list_backups());self.assertTrue(backups.verify(backups.list_backups()[0]).integrity_ok)
            finally:db.close()
