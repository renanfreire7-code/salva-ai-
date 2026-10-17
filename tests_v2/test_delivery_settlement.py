from tests_v2.delivery_support import DeliveryCase


class DeliverySettlementTest(DeliveryCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.delivery.settlement import SettlementService
        self.settlements = SettlementService(self.db, self.cash, self.finance, self.security)
        self.order = self.delivery.confirm(self.draft(), 'order1')
        self.trip = self.delivery.dispatch(self.order.id, 'dispatch1')

    def test_offset_only_physical_difference_in_drawer(self):
        payment = self.delivery.record_payment(self.order.id, 'MONEY', 4500, 'COURIER', 4500, 'collect1')
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)
        s = self.settlements.settle([payment], [self.trip], 3800, 0, 700, self.grant('delivery.settle'), 'settle1')
        self.assertEqual((s.handed_in_cents, s.offset_cents), (3800, 700))
        self.assertEqual(self.cash.position(self.session).expected_cents, 13800)
        self.assertEqual(self.settlements.pending_custody_cents(), 0)
        self.assertEqual(self.settlements.settle([payment], [self.trip], 3800, 0, 700, None, 'settle1'), s)

    def test_delivery_does_not_imply_payment(self):
        self.delivery.mark_delivered(self.order.id, 'delivered1')
        self.assertEqual(self.delivery.order(self.order.id).paid_cents, 0)
        self.assertIn('Pedidos sem pagamento confirmado', self.cash.blockers(self.session))

    def test_change_float_and_explicit_return(self):
        from salva_ai_v2.common.errors import BusinessError
        with self.assertRaises(BusinessError):
            self.delivery.record_payment(self.order.id, 'MONEY', 4500, 'COURIER', 5000, 'collect1')
        transfer = self.settlements.fund_courier(500, self.grant('delivery.float'), 'Troco para entrega', 'float1')
        self.delivery.record_payment(self.order.id, 'MONEY', 4500, 'COURIER', 5000, 'collect2')
        self.assertEqual(self.cash.position(self.session).expected_cents, 9500)
        self.assertEqual(self.settlements.pending_custody_cents(), 5000)
        self.settlements.return_float(transfer, 500, 'return1')
        self.assertEqual(self.settlements.pending_custody_cents(), 4500)
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)

    def test_digital_received_by_bar_not_courier_cash(self):
        from salva_ai_v2.common.errors import BusinessError
        other = self.delivery.confirm(self.draft(method='PIX'), 'order2')
        with self.assertRaises(BusinessError):
            self.delivery.record_payment(other.id, 'PIX', 4500, 'COURIER', None, 'bad1')
        self.delivery.record_payment(other.id, 'PIX', 4500, 'BAR', None, 'pix1')
        self.assertEqual(self.settlements.pending_custody_cents(), 0)
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)
