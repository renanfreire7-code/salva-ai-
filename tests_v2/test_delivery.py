from tests_v2.delivery_support import DeliveryCase


class DeliveryTest(DeliveryCase):
    def test_dispatch_once_and_historical_fees(self):
        order = self.delivery.confirm(self.draft(), 'order1')
        self.delivery.configure_fees(600, 800, 'fees2')
        self.assertEqual(self.inventory.position(self.pid).reserved, 8)
        trip = self.delivery.dispatch(order.id, 'dispatch1')
        self.assertEqual(self.delivery.dispatch(order.id, 'dispatch1'), trip)
        self.assertEqual(self.delivery.order(order.id).courier_fee_cents, 700)
        self.assertEqual(self.inventory.position(self.pid).physical, 12)
        self.assertEqual(self.inventory.position(self.pid).reserved, 0)
        self.assertEqual(self.scalar("SELECT count(*) FROM obligations WHERE source_type='TRIP'"), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 1)

    def test_invalid_address_and_stock_rollback(self):
        from dataclasses import replace
        from salva_ai_v2.common.errors import BusinessError
        for draft in (replace(self.draft(), address=''), self.draft(100)):
            with self.assertRaises(BusinessError):
                self.delivery.confirm(draft, 'bad' + str(draft.lines[0].qty))
        self.assertEqual(self.scalar("SELECT count(*) FROM orders WHERE kind='DELIVERY'"), 0)
        self.assertEqual(self.inventory.position(self.pid).reserved, 0)

    def test_second_dispatch_rejected_and_closing_blocked(self):
        from salva_ai_v2.common.errors import BusinessError
        order = self.delivery.confirm(self.draft(), 'order1')
        self.delivery.dispatch(order.id, 'dispatch1')
        with self.assertRaises(BusinessError):
            self.delivery.dispatch(order.id, 'dispatch2')
        self.assertIn('Pedidos em andamento', self.cash.blockers(self.session))
