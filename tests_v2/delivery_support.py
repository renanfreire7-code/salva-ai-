from tests_v2.support import DatabaseCase
from pathlib import Path


class DeliveryCase(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.inventory.models import PurchaseLine
        from salva_ai_v2.pricing.service import PricingService
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.sales.service import SalesService
        from salva_ai_v2.finance.service import FinanceService
        from salva_ai_v2.delivery.service import DeliveryService
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.inventory = InventoryService(self.db, self.security)
        self.pricing = PricingService(self.db)
        self.cash = CashService(self.db, self.security)
        self.finance = FinanceService(self.db, self.cash, self.security)
        self.sales = SalesService(self.db, self.inventory, self.pricing, self.cash, self.security)
        self.delivery = DeliveryService(self.db, self.inventory, self.pricing, self.sales, self.cash, self.finance, self.security, self.clock)
        self.pid = self.inventory.create_product('Cerveja', 500, 12, 6, 'p1')
        self.inventory.receive_purchase([PurchaseLine(self.pid, 20, 4000)], 0, self.clock.today(), self.clock.today(), 'buy1')
        self.session = self.cash.open(10000, 'open1')
        self.delivery.configure_fees(500, 700, 'fees1')

    def draft(self, qty=8, method='MONEY', collection='COURIER'):
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        return DeliveryDraft('Cliente teste', '11999990000', 'Rua fictícia, 10', 'Portão azul', [CartLine(self.pid, qty)], method, collection)

    def grant(self, action):
        return self.security.authorize('681942', action)
