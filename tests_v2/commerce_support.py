from tests_v2.support import DatabaseCase


class CommerceCase(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.pricing.service import PricingService
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.sales.service import SalesService
        from salva_ai_v2.inventory.models import PurchaseLine
        self.security = SecurityService(self.db)
        self.security.setup('681')
        self.inventory = InventoryService(self.db, self.security)
        self.pricing = PricingService(self.db)
        self.cash = CashService(self.db, self.security, self.clock)
        self.sales = SalesService(self.db, self.inventory, self.pricing, self.cash, self.security)
        self.pid = self.inventory.create_product('Lata', 500, 12, 6, 'p1')
        self.inventory.receive_purchase([PurchaseLine(self.pid, 20, 4000)], 0, self.clock.today(), self.clock.today(), 'buy1')
        self.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        self.session = self.cash.open(10000, 'open1')


    def grant(self, action):
        return self.security.authorize('681', action)
