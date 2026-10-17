from datetime import date
from unittest.mock import patch
from tests_v2.commerce_support import CommerceCase
from tests_v2.delivery_support import DeliveryCase


class ReviewCommerceTest(CommerceCase):
    def test_history_exposes_sale_number_and_details(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.reporting.queries import ReportingQueries
        from salva_ai_v2.reporting.models import HistoryFilter
        cart=self.sales.create_cart('cart')
        self.sales.set_cart_qty(cart,self.pid,1,'qty')
        sale=self.sales.sell(cart,Payment('PIX'),'sale-command')
        history=ReportingQueries(self.db).history(HistoryFilter(self.clock.today(),self.clock.today(),str(sale.id)))
        event=next(r for r in history if r.kind=='sale.confirmed')
        self.assertIn('Lata',event.description)
        self.assertIn('5,00',event.description)

    def test_payment_month_counts_only_that_month_but_preserves_lifetime_status(self):
        from salva_ai_v2.finance.models import ExpenseDraft,ExpenseFilter
        from salva_ai_v2.finance.service import FinanceService
        finance=FinanceService(self.db,self.cash,self.security)
        expense=finance.add_expense(ExpenseDraft('Conta','Outras',10000,date(2026,9,1),date(2026,9,15)),False,'expense')
        finance.pay_obligation(expense,5000,date(2026,9,15),'PIX',False,None,'pay-sep')
        finance.pay_obligation(expense,5000,date(2026,10,15),'PIX',False,None,'pay-oct')
        filters=ExpenseFilter(date(2026,10,1),date(2026,10,31),'payment')
        self.assertEqual(finance.expense_totals(filters).paid_cents,5000)
        self.assertEqual(finance.list_expenses(filters)[0].status,'PAID')
        self.assertEqual(finance.expense_totals(filters).pending_cents,0)

    def test_supplier_partial_credits_conserve_original_amount(self):
        from salva_ai_v2.inventory.models import PurchaseLine,CartLine
        pid=self.inventory.create_product('Centavos',100,1,0,'tiny')
        purchase=self.inventory.receive_purchase([PurchaseLine(pid,4,2)],0,self.clock.today(),self.clock.today(),'tiny-buy')
        for i in range(4):
            self.inventory.return_to_supplier(purchase,[CartLine(pid,1)],self.grant('purchase.return'),'Retorno conferido',f'return{i}')
        self.assertEqual(self.scalar('SELECT SUM(amount_cents) FROM supplier_credits WHERE purchase_id=?',(purchase,)),2)

    def test_paid_purchase_reversal_creates_credit_and_explicit_receipt(self):
        from salva_ai_v2.finance.service import FinanceService
        from salva_ai_v2.inventory.models import PurchaseLine
        finance=FinanceService(self.db,self.cash,self.security)
        self.inventory.finance=finance
        pid=self.inventory.create_product('Compra incorreta',500,1,0,'new-product')
        purchase=self.inventory.receive_purchase([PurchaseLine(pid,2,1000)],0,self.clock.today(),self.clock.today(),'buy-paid')
        obligation=self.scalar("SELECT id FROM obligations WHERE source_type='PURCHASE' AND source_id=?",(str(purchase),))
        finance.pay_obligation(obligation,600,self.clock.today(),'PIX',False,None,'supplier-pay')
        original_payment=self.scalar('SELECT id FROM obligation_payments WHERE obligation_id=?',(obligation,))
        self.inventory.reverse_purchase(purchase,self.grant('purchase.reverse'),'Valor digitado incorretamente','reverse')
        credit=next(r for r in self.inventory.supplier_credits() if r['purchase_id']==purchase)
        self.assertEqual(credit['pending_cents'],600)
        from salva_ai_v2.common.errors import BusinessError
        with self.assertRaises(BusinessError):
            finance.correct_payment(original_payment,'VOID',0,self.grant('payment.correct'),'Compra já revertida','invalid-original-correction')
        before=self.cash.position(self.session).expected_cents
        self.inventory.settle_supplier_credit(credit['id'],600,'RECEIPT','MONEY',True,self.clock.today(),self.grant('purchase.credit.settle'),'Fornecedor devolveu em dinheiro','credit-received')
        self.assertEqual(self.cash.position(self.session).expected_cents,before+600)
        self.assertEqual(self.inventory.supplier_credits()[0]['pending_cents'],0)
        self.inventory.settle_supplier_credit(credit['id'],600,'RECEIPT','MONEY',True,self.clock.today(),None,'Fornecedor devolveu em dinheiro','credit-received')
        self.assertEqual(self.cash.position(self.session).expected_cents,before+600)

    def test_supplier_credit_can_offset_only_pending_invoice(self):
        from salva_ai_v2.finance.service import FinanceService
        from salva_ai_v2.inventory.models import CartLine
        from salva_ai_v2.common.errors import BusinessError
        self.inventory.finance=FinanceService(self.db,self.cash,self.security)
        credit=self.inventory.return_to_supplier(1,[CartLine(self.pid,2)],self.grant('purchase.return'),'Mercadoria devolvida','credit')
        before=self.cash.position(self.session).expected_cents
        self.inventory.settle_supplier_credit(credit,400,'OFFSET',None,False,self.clock.today(),self.grant('purchase.credit.settle'),'Abatimento confirmado','offset')
        self.assertEqual(self.inventory.finance.paid_cents(1),400)
        self.assertEqual(self.cash.position(self.session).expected_cents,before)
        payment=self.scalar('SELECT id FROM obligation_payments WHERE obligation_id=1')
        with self.assertRaises(BusinessError):
            self.inventory.finance.correct_payment(payment,'VOID',0,self.grant('payment.correct'),'Tentativa de correção','wrong-offset')

    def test_cash_reconciliation_keeps_original_session_and_separate_refunds(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.reporting.queries import ReportingQueries
        from salva_ai_v2.reporting.html import cash_html
        from salva_ai_v2.maintenance.backup import BackupService
        from salva_ai_v2.cash.closing import ClosingService
        reports=ReportingQueries(self.db)
        cart=self.sales.create_cart('cart')
        self.sales.set_cart_qty(cart,self.pid,1,'qty')
        sale=self.sales.sell(cart,Payment('PIX'),'pix-sale')
        closing=ClosingService(self.db,self.cash,BackupService(self.db,self.root/'backups'),reports)
        result=closing.begin(10000,None,None,'close')
        self.assertIn('Pix',result.report_path.read_text())
        self.clock.advance(86400)
        next_session=self.cash.open(10000,'next-open')
        self.sales.reverse_sale(sale.id,True,Payment('PIX'),False,self.grant('sale.reverse'),'Cancelamento posterior','reverse')
        self.assertEqual(reports.cash_report(self.session).payments['PIX'],500)
        report=reports.cash_report(next_session)
        self.assertEqual(report.payments['PIX'],-500)
        self.assertEqual(report.refunds['PIX'],500)

    def test_sync_supports_windows_write_handle_contract(self):
        import os
        from salva_ai_v2.maintenance.backup import sync_file
        path=self.root/'artifact';path.write_bytes(b'content')
        original=os.fsync
        def requires_write(fd):
            os.write(fd,b'')
            original(fd)
        with patch('salva_ai_v2.maintenance.backup.os.fsync',side_effect=requires_write):
            sync_file(path)
        self.assertEqual(path.read_bytes(),b'content')

    def test_migration_recovers_prior_receipts_refunds_and_sale_identity(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.reporting.queries import ReportingQueries
        cart=self.sales.create_cart('old-cart')
        self.sales.set_cart_qty(cart,self.pid,1,'old-qty')
        sale=self.sales.sell(cart,Payment('PIX'),'old-sale')
        self.sales.reverse_sale(sale.id,True,None,False,self.grant('sale.reverse'),'Reembolso posterior','old-reverse')
        self.sales.confirm_refund(sale.id,Payment('PIX'),self.grant('sale.refund'),'Reembolso confirmado','old-refund')
        self.db.conn.execute('DROP TABLE receipt_events')
        self.db.conn.execute('DROP TABLE supplier_credit_settlements')
        self.db.conn.execute("DELETE FROM schema_migrations WHERE version='013_review_reconciliation.sql'")
        self.db.conn.execute("UPDATE audit_events SET object_id='old-sale' WHERE kind='sale.confirmed'")
        self.db.migrate()
        report=ReportingQueries(self.db).cash_report(self.session)
        self.assertEqual((report.receipts['PIX'],report.refunds['PIX'],report.payments['PIX']),(500,500,0))
        self.assertEqual(self.scalar("SELECT object_id FROM audit_events WHERE kind='sale.confirmed'"),str(sale.id))


class ReviewDeliveryTest(DeliveryCase):
    def test_partial_returns_never_create_or_negate_historical_cost(self):
        from salva_ai_v2.inventory.models import PurchaseLine,CartLine
        from salva_ai_v2.sales.models import Payment
        pid=self.inventory.create_product('Centavos',100,1,0,'tiny')
        self.inventory.receive_purchase([PurchaseLine(pid,4,2)],0,self.clock.today(),self.clock.today(),'tiny-buy')
        draft=self.draft(qty=4)
        from dataclasses import replace
        order=self.delivery.confirm(replace(draft,lines=[CartLine(pid,4)]),'tiny-order')
        self.delivery.dispatch(order.id,'dispatch')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Pedido cancelado','cancel')
        for i in range(4):
            self.delivery.confirm_return(order.id,[CartLine(pid,1)],self.grant('delivery.return'),'Unidade conferida',f'return{i}')
            cart=self.sales.create_cart(f'cart{i}')
            self.sales.set_cart_qty(cart,pid,1,f'qty{i}')
            self.sales.sell(cart,Payment('PIX'),f'sale{i}')
        self.assertEqual(self.scalar('SELECT SUM(cogs_cents) FROM delivery_returns WHERE order_id=?',(order.id,)),2)
        self.assertEqual(self.inventory.position(pid).value_cents,0)

    def test_trip_offset_cannot_be_voided_through_generic_payment(self):
        from salva_ai_v2.delivery.settlement import SettlementService
        from salva_ai_v2.common.errors import BusinessError
        order=self.delivery.confirm(self.draft(),'order')
        trip=self.delivery.dispatch(order.id,'trip')
        collection=self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',4500,'receipt')
        settlement=SettlementService(self.db,self.cash,self.finance,self.security)
        settlement.settle([collection],[trip],3800,0,700,self.grant('delivery.settle'),'settle')
        payment=self.scalar("SELECT p.id FROM obligation_payments p JOIN obligations o ON o.id=p.obligation_id WHERE o.source_type='TRIP'")
        with self.assertRaises(BusinessError):
            self.finance.correct_payment(payment,'VOID',0,self.grant('payment.correct'),'Correção pelo financeiro','void')
        self.assertEqual(settlement.trips_pending(),[])

    def test_delivery_report_uses_receipts_and_actual_partial_refunds(self):
        from salva_ai_v2.reporting.queries import ReportingQueries
        reports=ReportingQueries(self.db)
        order=self.delivery.confirm(self.draft(method='PIX',collection='BAR'),'order')
        self.delivery.dispatch(order.id,'dispatch')
        self.assertEqual(reports.cash_report(self.session).payments.get('PIX',0),0)
        self.delivery.record_payment(order.id,'PIX',4500,'BAR',None,'receipt')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cancelamento confirmado','cancel')
        self.assertEqual(reports.cash_report(self.session).payments['PIX'],4500)
        self.delivery.refund(order.id,'PIX',1000,False,self.grant('delivery.refund'),'Parte devolvida','refund')
        report=reports.cash_report(self.session)
        self.assertEqual(report.payments['PIX'],3500)
        self.assertEqual(report.receipts['PIX'],4500)
        self.assertEqual(report.refunds['PIX'],1000)
