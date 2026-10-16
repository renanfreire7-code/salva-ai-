from pathlib import Path
from tests_v2.support import DatabaseCase


class PricingTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/pricing/service.py').exists(), 'Promoções ainda não implementadas')
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.pricing.service import PricingService
        self.inventory = InventoryService(self.db, SecurityService(self.db))
        self.pid = self.inventory.create_product('Lata', 500, 12, 6, 'p1')
        self.pricing = PricingService(self.db)

    def test_complete_groups_and_leftovers(self):
        from salva_ai_v2.pricing.models import PriceCondition
        condition = PriceCondition(500, 3, 1200)
        self.assertEqual([self.pricing.quote(condition, n).total_cents for n in (1, 2, 3, 4, 6)],
                         [500, 1000, 1200, 1700, 2400])
        self.assertEqual(self.pricing.quote(condition, 4).savings_cents, 300)

    def test_snapshot_survives_change(self):
        self.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        before = self.pricing.snapshot(self.pid)
        self.pricing.set_promotion(self.pid, 3, 1100, True, 'promo2')
        self.assertEqual(self.pricing.quote(before, 3).total_cents, 1200)
        self.assertEqual(self.pricing.quote(self.pricing.snapshot(self.pid), 3).total_cents, 1100)

    def test_invalid_groups_and_disable(self):
        from salva_ai_v2.common.errors import BusinessError
        for qty, price in ((1, 100), (3, 1500), (3, -1), (3, 0)):
            with self.assertRaises(BusinessError):
                self.pricing.set_promotion(self.pid, qty, price, True, f'bad{qty}:{price}')
        self.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        self.pricing.set_promotion(self.pid, 3, 1200, False, 'off1')
        self.assertEqual(self.pricing.quote(self.pricing.snapshot(self.pid), 3).total_cents, 1500)
