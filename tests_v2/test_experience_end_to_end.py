import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from salva_ai_v2.common.db import APPLICATION_ID
from salva_ai_v2.inventory.models import CartLine, PurchaseLine
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.sales.models import Payment


class ExperienceEndToEndTest(unittest.TestCase):
    def test_upgrade_trade_delivery_settlement_restart_close_and_restore(self):
        from salva_ai_v2.bootstrap import build_application
        with tempfile.TemporaryDirectory(prefix='ensaio com acentuação ') as directory:
            root=Path(directory);path=root/'dados'/'salva_ai.sqlite3';path.parent.mkdir()
            db=sqlite3.connect(path)
            for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
                if migration.name>'013_review_reconciliation.sql':continue
                source=migration.read_text();db.executescript(source)
                db.execute('INSERT INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(source.encode()).hexdigest()))
            db.execute(f'PRAGMA application_id={APPLICATION_ID}');db.commit();db.close()
            app=build_application(root)
            try:
                s=app.services;s.security.setup('681942')
                grant=lambda action:s.security.authorize('681942',action)
                self.assertEqual(len(s.backups.list_backups()),1)
                pid=s.inventory.create_product('Cerveja Heineken Latão',500,12,6,'product')
                s.inventory.receive_purchase([PurchaseLine(pid,20,4000)],0,s.clock.today(),s.clock.today(),'purchase')
                s.pricing.set_promotion(pid,3,1200,True,'promotion');session=s.cash.open(10000,'open')
                tab=s.sales.create_tab('Cliente balcão','tab');s.sales.set_tab_qty(tab,pid,3,None,None,'tab-items')
                sale=s.sales.pay_tab(tab,Payment('PIX'),'sale')
                self.assertEqual(s.commerce.detail(f'sale:{sale.id}')['row'].total_cents,1200)
                s.pricing.set_promotion(pid,3,1200,False,'promotion-off')
                s.delivery.configure_fees(500,700,'fees')
                advance=DeliveryDraft('Cliente Pix','11','Rua A','',[CartLine(pid,1)],'PIX','BAR','ADVANCE','PIX')
                prepaid=s.delivery.confirm(advance,'advance');s.delivery.record_payment(prepaid.id,'PIX',1000,'BAR',None,'advance-receipt')
                trip1=s.delivery.dispatch(prepaid.id,'advance-dispatch');s.delivery.mark_delivered(prepaid.id,'advance-delivered')
                cashdraft=DeliveryDraft('Cliente dinheiro','22','Rua B','Portão azul',[CartLine(pid,8)],'MONEY','COURIER','ON_DELIVERY','MONEY',5000)
                cashorder=s.delivery.confirm(cashdraft,'cash-order')
                fund=s.settlements.fund_courier(500,grant('delivery.float'),'Fundo de troco','float')
                trip2=s.delivery.dispatch(cashorder.id,'cash-dispatch')
                receipt=s.delivery.record_payment(cashorder.id,'MONEY',4500,'COURIER',5000,'cash-receipt')
                s.delivery.mark_delivered(cashorder.id,'cash-delivered')
                settled=s.settlements.settle([receipt],[trip2],3800,0,700,grant('delivery.settle'),'settle-money')
                s.settlements.return_float(fund,500,'return-float')
                s.settlements.settle([],[trip1],0,700,0,grant('delivery.settle'),'settle-digital')
                self.assertEqual(s.settlements.pending_custody_cents(),0)
                self.assertEqual(s.cash.position(session).expected_cents,13100)
                self.assertEqual(s.inventory.position(pid).physical,8)
                self.assertEqual(s.delivery_queries.settlement_detail(settled.id)['items'][0]['order_id'],cashorder.id)
                self.assertEqual(s.delivery_queries.detail(cashorder.id)['order']['name'],'Cliente dinheiro')
                app.close();app=build_application(root);s=app.services
                self.assertEqual(s.delivery.confirm(cashdraft,'cash-order'),cashorder)
                self.assertEqual(s.delivery.record_payment(cashorder.id,'MONEY',4500,'COURIER',5000,'cash-receipt'),receipt)
                closing=s.closing.begin(13100,None,None,'close')
                self.assertTrue(closing.complete);self.assertTrue(s.backups.verify(closing.backup_path).integrity_ok)
                s.inventory.create_product('Depois do backup',100,1,0,'later')
                preview=s.restore.prepare(closing.backup_path,s.security.authorize('681942','backup.restore'))
                s.restore.apply(preview,True)
                self.assertEqual(app.db.conn.execute('SELECT count(*) FROM products').fetchone()[0],1)
            finally:app.close()
