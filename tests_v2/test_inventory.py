from pathlib import Path
from uuid import uuid4
from tests_v2.support import DatabaseCase


class InventoryTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/inventory/service.py').exists(), 'Estoque ainda não implementado')
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.security.service import SecurityService
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.inventory = InventoryService(self.db, self.security)
        self.pid = self.inventory.create_product('Lata', 500, 12, 6, 'p1')

    def receive(self, qty, cost, command='buy1', freight=0):
        from salva_ai_v2.inventory.models import PurchaseLine
        return self.inventory.receive_purchase([PurchaseLine(self.pid, qty, cost)], freight,
                                               self.clock.today(), self.clock.today(), command)

    def grant(self, action):
        return self.security.authorize('681942', action)

    def test_weighted_stock_and_purchase_idempotency(self):
        self.receive(10, 2000)
        self.receive(10, 4000, 'buy2')
        self.receive(10, 4000, 'buy2')
        pos = self.inventory.position(self.pid)
        self.assertEqual((pos.physical, pos.value_cents, pos.available), (20, 6000, 20))
        self.assertEqual(self.scalar('SELECT count(*) FROM obligations'), 2)

    def test_fractional_unit_cost_conserves_total(self):
        self.receive(3, 1)
        costs = []
        with self.db.transaction():
            for _ in range(3):
                costs.append(self.inventory.consume(self.pid, 1))
        self.assertEqual(sum(costs), 1)
        self.assertEqual(self.inventory.position(self.pid).value_cents, 0)

    def test_invalid_quantities_and_freight(self):
        from salva_ai_v2.common.errors import BusinessError
        for qty in (0, -1, 1.5, True):
            with self.assertRaises(BusinessError):
                self.receive(qty, 100, str(uuid4()))
        self.receive(2, 1000, freight=100)
        self.assertEqual(self.inventory.position(self.pid).value_cents, 1100)

    def test_reservation_limits_adjustments(self):
        from salva_ai_v2.common.errors import BusinessError
        self.receive(10, 2000)
        with self.db.transaction():
            self.inventory.reserve(self.pid, 'TAB', 1, 8)
        with self.assertRaises(BusinessError):
            self.inventory.adjust(self.pid, -3, 'Perda teste', self.grant('stock.adjust'), 'loss1')
        self.assertEqual(self.inventory.position(self.pid).physical, 10)
        self.inventory.adjust(self.pid, -2, 'Perda teste', self.grant('stock.adjust'), 'loss2')
        self.assertEqual(self.inventory.position(self.pid).available, 0)

    def test_reverse_and_supplier_return_preserve_records(self):
        from salva_ai_v2.inventory.models import CartLine
        from salva_ai_v2.common.errors import BusinessError
        purchase = self.receive(10, 2000)
        result = self.inventory.return_to_supplier(purchase, [CartLine(self.pid, 2)],
                    self.grant('purchase.return'), 'Devolução teste', 'ret1')
        self.assertIsInstance(result, int)
        self.assertEqual(self.inventory.position(self.pid).physical, 8)
        self.assertEqual(self.scalar('SELECT count(*) FROM supplier_credits'), 1)
        with self.assertRaises(BusinessError):
            self.inventory.reverse_purchase(purchase, self.grant('purchase.reverse'), 'Correção teste', 'reverse1')

    def test_deactivation_prevents_new_reservations(self):
        from salva_ai_v2.common.errors import BusinessError
        self.receive(10, 2000)
        self.inventory.deactivate(self.pid, self.grant('product.deactivate'), 'Fora de linha', 'off1')
        with self.assertRaises(BusinessError):
            with self.db.transaction():
                self.inventory.reserve(self.pid, 'TAB', 1, 1)
