from dataclasses import replace,asdict
import hashlib
from tests_v2.delivery_support import DeliveryCase
from salva_ai_v2.common.errors import BusinessError


class DeliveryPaymentPlanTest(DeliveryCase):
    def money_plan(self,change=5000):
        return replace(self.draft(),payment_timing='ON_DELIVERY',payment_channel='MONEY',change_for_cents=change)

    def test_forecast_is_not_money_and_insufficient_float_blocks_dispatch(self):
        from salva_ai_v2.delivery.settlement import SettlementService
        order=self.delivery.confirm(self.money_plan(),'plan')
        self.assertEqual(self.cash.position(self.session).expected_cents,10000)
        self.assertEqual(self.scalar('SELECT COALESCE(SUM(delta_cents),0) FROM custody_entries'),0)
        with self.assertRaises(BusinessError):
            self.delivery.dispatch(order.id,'no-float')
        self.assertEqual(self.scalar('SELECT count(*) FROM trips'),0)
        settlements=SettlementService(self.db,self.cash,self.finance,self.security)
        settlements.fund_courier(500,self.grant('delivery.float'),'Troco para pedido','float')
        self.delivery.dispatch(order.id,'dispatch')
        self.assertEqual(self.cash.position(self.session).expected_cents,9500)
        self.assertEqual(settlements.pending_custody_cents(),500)
        row=self.db.conn.execute('SELECT * FROM delivery_orders WHERE order_id=?',(order.id,)).fetchone()
        self.assertEqual(row['change_for_cents'],5000)

    def test_actual_change_difference_requires_conference_and_keeps_plan(self):
        from salva_ai_v2.delivery.settlement import SettlementService
        settlement=SettlementService(self.db,self.cash,self.finance,self.security)
        settlement.fund_courier(6000,self.grant('delivery.float'),'Troco para roteiro','float')
        order=self.delivery.confirm(self.money_plan(),'plan')
        self.delivery.dispatch(order.id,'dispatch')
        with self.assertRaises(BusinessError):
            self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',10000,'receipt')
        payment=self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',10000,'receipt',confirm_change_difference=True)
        row=self.db.conn.execute('SELECT * FROM collections WHERE id=?',(payment,)).fetchone()
        self.assertEqual((row['tendered_cents'],row['change_cents']),(10000,5500))
        self.assertEqual(self.scalar('SELECT change_for_cents FROM delivery_orders WHERE order_id=?',(order.id,)),5000)
        self.assertEqual(settlement.pending_custody_cents(),10500)
        self.assertEqual(self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',10000,'receipt',confirm_change_difference=True),payment)

    def test_advance_requires_receipt_and_digital_has_no_drawer(self):
        plan=replace(self.draft(method='PIX',collection='BAR'),payment_timing='ADVANCE',payment_channel='PIX')
        order=self.delivery.confirm(plan,'plan')
        with self.assertRaises(BusinessError):
            self.delivery.dispatch(order.id,'not-paid')
        self.delivery.record_payment(order.id,'PIX',4500,'BAR',None,'received')
        self.delivery.dispatch(order.id,'dispatch')
        self.assertEqual(self.cash.position(self.session).expected_cents,10000)
        self.assertEqual(self.scalar('SELECT count(*) FROM trips'),1)

    def test_link_has_real_card_method_and_refunds_that_method(self):
        plan=replace(self.draft(method='CREDIT',collection='BAR'),payment_timing='ADVANCE',payment_channel='LINK',link_reference='https://pagamento.exemplo/pedido')
        order=self.delivery.confirm(plan,'plan')
        with self.assertRaises(BusinessError):
            self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',4500,'wrong')
        self.delivery.record_payment(order.id,'DEBIT',4500,'BAR',None,'debit')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Pedido cancelado','cancel')
        self.delivery.refund(order.id,'DEBIT',4500,False,self.grant('delivery.refund'),'Estornado no cartão','refund')
        self.assertEqual(self.cash.position(self.session).expected_cents,10000)

    def test_invalid_plan_does_not_reserve_or_create_order(self):
        plans=[self.money_plan(4500),self.money_plan(4000),replace(self.money_plan(),payment_channel='PIX'),replace(self.money_plan(),payment_timing='ADVANCE')]
        for i,plan in enumerate(plans):
            with self.subTest(i=i),self.assertRaises(BusinessError):
                self.delivery.confirm(plan,f'invalid{i}')
        self.assertEqual(self.scalar('SELECT count(*) FROM orders'),0)
        self.assertEqual(self.inventory.position(self.pid).reserved,0)

    def test_old_default_payload_and_replay_after_reopen(self):
        from salva_ai_v2.common.commands import canonical
        from salva_ai_v2.common.db import Database
        from salva_ai_v2.delivery.service import DeliveryService
        draft=self.draft()
        order=self.delivery.confirm(draft,'old-order')
        self.delivery.dispatch(order.id,'old-dispatch')
        payment=self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',4500,'old-payment')
        old={k:v for k,v in asdict(draft).items() if k in ('customer','phone','address','reference','lines','payment_method','collection')}
        fingerprint=hashlib.sha256(canonical({'draft':old}).encode()).hexdigest()
        self.assertEqual(self.scalar('SELECT fingerprint FROM command_results WHERE id=?',('old-order',)),fingerprint)
        path=self.db.path;self.db.close()
        self.db=Database(path,self.clock);self.addCleanup(self.db.close)
        self.delivery=DeliveryService(self.db,self.inventory,self.pricing,self.sales,self.cash,self.finance,self.security,self.clock)
        self.assertEqual(self.delivery.confirm(draft,'old-order'),order)
        self.assertEqual(self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',4500,'old-payment'),payment)
        self.assertEqual(self.scalar('SELECT count(*) FROM collections'),1)

    def test_advance_redelivery_creates_preparing_attempt_for_new_receipt(self):
        plan=replace(self.draft(method='PIX',collection='BAR'),payment_timing='ADVANCE',payment_channel='PIX')
        order=self.delivery.confirm(plan,'plan')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cliente pediu outra tentativa','cancel')
        new_id=self.delivery.redeliver(order.id,self.grant('delivery.redeliver'),'Nova tentativa combinada','new')
        row=self.db.conn.execute('SELECT * FROM delivery_orders WHERE previous_order_id=?',(order.id,)).fetchone()
        self.assertEqual(row['order_id'],new_id)
        self.assertEqual(row['payment_timing'],'ADVANCE')
        self.assertEqual(self.delivery.order(new_id).state,'PREPARING')
        self.assertEqual(self.scalar('SELECT count(*) FROM trips'),0)
