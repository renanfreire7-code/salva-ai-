from pathlib import Path
from tests_v2.delivery_support import DeliveryCase


class EndToEndTest(DeliveryCase):
    def test_trade_delivery_expense_close_backup_and_restore(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.finance.models import ExpenseDraft
        from salva_ai_v2.delivery.settlement import SettlementService
        from salva_ai_v2.maintenance.backup import BackupService
        from salva_ai_v2.maintenance.restore import RestoreService
        from salva_ai_v2.cash.closing import ClosingService
        from salva_ai_v2.reporting.queries import ReportingQueries
        self.pricing.set_promotion(self.pid,3,1200,True,'promo1')
        tab=self.sales.create_tab('Cliente fictício','tab1')
        self.sales.set_tab_qty(tab,self.pid,3,None,None,'add1')
        self.sales.pay_tab(tab,Payment('MONEY',2000),'pay1')
        expense=self.finance.add_expense(ExpenseDraft('Energia teste','Energia',100,self.clock.today(),self.clock.today()),False,'exp1')
        self.finance.pay_obligation(expense,100,self.clock.today(),'MONEY',True,self.grant('cash.withdraw'),'expense-pay')
        order=self.delivery.confirm(self.draft(qty=3),'order1')
        trip=self.delivery.dispatch(order.id,'dispatch1')
        payment=self.delivery.record_payment(order.id,'MONEY',1700,'COURIER',1700,'collect1')
        self.delivery.mark_delivered(order.id,'delivered1')
        settlements=SettlementService(self.db,self.cash,self.finance,self.security)
        settlements.settle([payment],[trip],1000,0,700,self.grant('delivery.settle'),'settle1')
        self.assertEqual(self.cash.blockers(self.session),[])
        expected=self.cash.position(self.session).expected_cents
        backups=BackupService(self.db,self.root/'backups')
        closed=ClosingService(self.db,self.cash,backups,ReportingQueries(self.db)).begin(expected,None,None,'close1')
        self.assertTrue(closed.complete)
        restore=RestoreService(self.root,backups,self.security)
        preview=restore.prepare(closed.backup_path,self.grant('backup.restore'))
        restore.apply(preview,True)
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'),2)
        self.assertEqual(self.scalar("SELECT count(*) FROM cash_sessions WHERE state='CLOSED'"),1)
        self.assertEqual(self.db.conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
