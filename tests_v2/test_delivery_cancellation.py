from tests_v2.delivery_support import DeliveryCase


class DeliveryCancellationTest(DeliveryCase):
    def setUp(self):
        super().setUp()

    def test_cancel_before_dispatch_releases_stock_without_trip(self):
        order = self.delivery.confirm(self.draft(), 'order1')
        self.delivery.cancel(order.id, self.grant('delivery.cancel'), 'Cliente desistiu', 'cancel1')
        self.assertEqual(self.inventory.position(self.pid).reserved, 0)
        self.assertEqual(self.inventory.position(self.pid).physical, 20)
        self.assertEqual(self.scalar('SELECT count(*) FROM trips'), 0)

    def test_paid_cancel_keeps_trip_and_requires_return_and_refund(self):
        from salva_ai_v2.inventory.models import CartLine
        order = self.delivery.confirm(self.draft(), 'order1')
        trip = self.delivery.dispatch(order.id, 'dispatch1')
        self.delivery.record_payment(order.id, 'MONEY', 4500, 'COURIER', 4500, 'collect1')
        self.delivery.cancel(order.id, self.grant('delivery.cancel'), 'Cliente cancelou', 'cancel1')
        self.assertEqual(self.scalar("SELECT amount_cents FROM obligations WHERE source_type='TRIP'"), 700)
        self.assertEqual(self.inventory.position(self.pid).physical, 12)
        self.assertIn('Reembolso pendente', self.cash.blockers(self.session))
        self.delivery.confirm_return(order.id, [CartLine(self.pid, 8)], self.grant('delivery.return'), 'Mercadoria conferida', 'return1')
        self.assertEqual(self.inventory.position(self.pid).physical, 20)
        self.delivery.refund(order.id, 'MONEY', 4500, False, self.grant('delivery.refund'), 'Devolvido pelo entregador', 'refund1')
        self.assertEqual(self.scalar('SELECT SUM(delta_cents) FROM custody_entries'), 0)
        self.assertNotIn('Reembolso pendente', self.cash.blockers(self.session))
        self.assertEqual(self.scalar('SELECT count(*) FROM trips'), 1)

    def test_double_return_rejected(self):
        from salva_ai_v2.inventory.models import CartLine
        from salva_ai_v2.common.errors import BusinessError
        order = self.delivery.confirm(self.draft(), 'order1')
        self.delivery.dispatch(order.id, 'dispatch1')
        self.delivery.cancel(order.id, self.grant('delivery.cancel'), 'Cliente cancelou', 'cancel1')
        self.delivery.confirm_return(order.id, [CartLine(self.pid, 8)], self.grant('delivery.return'), 'Retorno conferido', 'ret1')
        with self.assertRaises(BusinessError):
            self.delivery.confirm_return(order.id, [CartLine(self.pid, 1)], self.grant('delivery.return'), 'Retorno duplicado', 'ret2')

    def test_counter_sale_reversal_cannot_bypass_delivery_flow(self):
        from salva_ai_v2.common.errors import BusinessError
        order=self.delivery.confirm(self.draft(),'order1')
        self.delivery.dispatch(order.id,'dispatch1')
        sale=self.scalar('SELECT id FROM sales WHERE order_id=?',(order.id,))
        with self.assertRaises(BusinessError):
            self.sales.reverse_sale(sale,True,None,False,self.grant('sale.reverse'),'Correção pelo fluxo errado','wrong1')
