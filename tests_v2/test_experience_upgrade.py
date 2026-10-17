import hashlib
from pathlib import Path
from tests_v2.commerce_support import CommerceCase
from tests_v2.support import DatabaseCase


class SnapshotTest(CommerceCase):
    def test_first_name_survives_rename_remove_reinclude_and_sale(self):
        from salva_ai_v2.sales.models import Payment
        cart=self.sales.create_cart('cart')
        self.sales.set_cart_qty(cart,self.pid,1,'first')
        self.inventory.update_product(self.pid,'Nome novo',500,12,6,self.grant('product.edit'),'Alteração de cadastro','rename')
        self.sales.set_cart_qty(cart,self.pid,0,'remove')
        self.sales.set_cart_qty(cart,self.pid,2,'reinclude')
        self.assertEqual(self.sales.lines(cart)[0]['name'],'Lata')
        sale=self.sales.sell(cart,Payment('PIX'),'sell')
        self.assertEqual(self.scalar('SELECT name_snapshot FROM sale_items WHERE sale_id=?',(sale.id,)),'Lata')

    def test_reopened_tab_keeps_previous_sale_items(self):
        from salva_ai_v2.sales.models import Payment
        tab=self.sales.create_tab('Cliente','tab')
        self.sales.set_tab_qty(tab,self.pid,1,None,None,'qty')
        sale=self.sales.pay_tab(tab,Payment('PIX'),'paid')
        self.sales.reverse_sale(sale.id,True,Payment('PIX'),True,self.grant('sale.reverse'),'Cliente retomou comanda','reverse')
        self.inventory.update_product(self.pid,'Outro nome',500,12,6,self.grant('product.edit'),'Novo nome de produto','rename')
        next_sale=self.sales.pay_tab(tab,Payment('PIX'),'paid-again')
        self.assertEqual(self.scalar('SELECT name_snapshot FROM sale_items WHERE sale_id=?',(sale.id,)),'Lata')
        self.assertEqual(self.scalar('SELECT name_snapshot FROM sale_items WHERE sale_id=?',(next_sale.id,)),'Lata')


class ExperienceUpgradeTest(DatabaseCase):
    def test_populated_previous_schema_keeps_ids_money_pin_and_backup(self):
        from salva_ai_v2.common.db import Database,APPLICATION_ID
        from salva_ai_v2.maintenance.backup import BackupService
        import sqlite3
        path=self.root/'previous.sqlite3'
        conn=sqlite3.connect(path)
        for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
            if migration.name>'013_review_reconciliation.sql':
                continue
            source=migration.read_text()
            conn.executescript(source)
            conn.execute('INSERT INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(source.encode()).hexdigest()))
        conn.execute(f'PRAGMA application_id={APPLICATION_ID}')
        conn.execute("INSERT INTO products(id,name,price_cents,pack_size,min_stock,stock,value_cents) VALUES(41,'Produto existente',500,12,6,10,2000)")
        conn.execute("INSERT INTO cash_sessions(id,opened_at,opening_cents) VALUES(9,'2026-10-16T12:00:00-03:00',10000)")
        conn.execute("INSERT INTO orders VALUES(17,'DELIVERY','Cliente','PREPARING',9,'2026-10-16T12:00:00-03:00')")
        conn.execute('INSERT INTO order_items VALUES(17,41,2,500,NULL,NULL)')
        conn.execute("INSERT INTO delivery_orders(order_id,phone,address,reference,method,collection,delivery_fee_cents,courier_fee_cents) VALUES(17,'123','Rua','Portão','MONEY','COURIER',500,700)")
        conn.commit();conn.close()
        db=Database(path,self.clock)
        try:
            from salva_ai_v2.security.service import SecurityService
            from tests_v2.security_support import seed_legacy_pin
            security=SecurityService(db);seed_legacy_pin(db)
            backups=BackupService(db,self.root/'upgrade-backups')
            db.upgrade(backups)
            row=db.conn.execute('SELECT * FROM delivery_orders WHERE order_id=17').fetchone()
            self.assertEqual(row['payment_timing'],'UNSPECIFIED')
            self.assertIsNone(row['change_for_cents'])
            self.assertEqual(db.conn.execute('SELECT name_snapshot FROM order_items WHERE order_id=17').fetchone()[0],'Produto existente')
            self.assertEqual(tuple(db.conn.execute('SELECT stock,value_cents FROM products WHERE id=41').fetchone()),(10,2000))
            security.authorize('681942','product.edit')
            paths=backups.list_backups();self.assertEqual(len(paths),1)
            self.assertTrue(backups.verify(paths[0]).integrity_ok)
            db.upgrade(backups)
            self.assertEqual(len(backups.list_backups()),1)
        finally:
            db.close()
