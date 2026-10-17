from dataclasses import replace
from tests_v2.delivery_support import DeliveryCase


class DeliveryDetailsTest(DeliveryCase):
    def queries(self):
        from salva_ai_v2.delivery.queries import DeliveryQueries
        return DeliveryQueries(self.db)

    def test_partial_settlement_details_do_not_multiply_orders(self):
        from salva_ai_v2.delivery.settlement import SettlementService
        settlement=SettlementService(self.db,self.cash,self.finance,self.security)
        order=self.delivery.confirm(self.draft(),'order')
        trip=self.delivery.dispatch(order.id,'dispatch')
        collection=self.delivery.record_payment(order.id,'MONEY',4500,'COURIER',4500,'receipt')
        first=settlement.settle([collection],[],2000,0,0,self.grant('delivery.settle'),'first')
        second=settlement.settle([collection],[trip],1800,0,700,self.grant('delivery.settle'),'second')
        rows=self.queries().settlement_orders(pending_only=False)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['total_cents'],rows[0]['custody_pending_cents'],rows[0]['trip_pending_cents']),(4500,0,0))
        self.assertEqual(self.queries().settlement_orders(),[])
        records=self.queries().settlements()
        self.assertEqual(sum(r['handed_in_cents'] for r in records),3800)
        self.assertEqual(sum(r['offset_cents'] for r in records),700)
        detail=self.queries().settlement_detail(second.id)
        self.assertEqual({r['source_type'] for r in detail['items']},{'COLLECTION','TRIP'})
        self.assertEqual({r['order_id'] for r in detail['items']},{order.id})
        self.assertEqual(self.queries().settlement_detail(first.id)['items'][0]['amount_cents'],2000)

    def test_order_details_keep_items_plan_receipt_and_cancelled_trip(self):
        plan=replace(self.draft(method='PIX',collection='BAR'),payment_timing='ADVANCE',payment_channel='PIX')
        order=self.delivery.confirm(plan,'order')
        self.delivery.record_payment(order.id,'PIX',4500,'BAR',None,'receipt')
        self.delivery.dispatch(order.id,'dispatch')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cancelamento confirmado','cancel')
        self.inventory.update_product(self.pid,'Outro nome',500,12,6,self.grant('product.edit'),'Cadastro atualizado','rename')
        detail=self.queries().detail(order.id)
        self.assertEqual(detail['items'][0]['name'],'Cerveja')
        self.assertEqual(detail['payment_plan']['payment_timing'],'ADVANCE')
        self.assertEqual(detail['collections'][0]['method'],'PIX')
        self.assertEqual(detail['trips'][0]['pending_cents'],700)
        self.assertEqual(detail['refunds'][0]['pending_cents'],4500)
        self.assertEqual(detail['custody_pending_cents'],0)
        self.assertEqual(self.queries().settlement_orders()[0]['trip_pending_cents'],700)

    def test_history_includes_cancelled_before_dispatch_and_distinct_key(self):
        from salva_ai_v2.reporting.commerce import CommerceQueries
        from salva_ai_v2.reporting.commerce_models import CommerceFilter
        order=self.delivery.confirm(self.draft(),'order')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cliente desistiu','cancel')
        query=CommerceQueries(self.db)
        rows=query.list(CommerceFilter(self.clock.today(),self.clock.today(),kind='DELIVERY'))
        self.assertEqual([(r.key,r.state,r.total_cents) for r in rows],[(f'delivery:{order.id}','CANCELED',4500)])
        self.assertEqual(query.detail(rows[0].key)['items'][0].qty,8)
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'),0)
