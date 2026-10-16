from pathlib import Path
from unittest.mock import patch
from tests_v2.support import DatabaseCase


class SalesTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/sales/service.py').exists(), 'Vendas ainda não implementadas')
        from salva_ai_v2.security.service import SecurityService
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.pricing.service import PricingService
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.sales.service import SalesService
        from salva_ai_v2.inventory.models import PurchaseLine
        self.security = SecurityService(self.db)
        self.security.setup('681942')
        self.inventory = InventoryService(self.db, self.security)
        self.pricing = PricingService(self.db)
        self.cash = CashService(self.db, self.security, self.clock)
        self.sales = SalesService(self.db, self.inventory, self.pricing, self.cash, self.security)
        self.pid = self.inventory.create_product('Lata', 500, 12, 6, 'p1')
        self.inventory.receive_purchase([PurchaseLine(self.pid, 20, 4000)], 0, self.clock.today(), self.clock.today(), 'buy1')
        self.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        self.session = self.cash.open(10000, 'open1')

    def grant(self, action):
        return self.security.authorize('681942', action)

    def test_cash_sale_exact_cogs_and_replay(self):
        from salva_ai_v2.sales.models import Payment
        cart = self.sales.create_cart('cart1')
        self.sales.set_cart_qty(cart, self.pid, 3, 'cartadd1')
        sale = self.sales.sell(cart, Payment('MONEY', 2000), 'sell1')
        self.assertEqual((sale.total_cents, sale.change_cents), (1200, 800))
        self.assertEqual(self.sales.sell(cart, Payment('MONEY', 2000), 'sell1'), sale)
        self.assertEqual(self.inventory.position(self.pid).physical, 17)
        self.assertEqual(self.cash.position(self.session).expected_cents, 11200)
        self.assertEqual(self.scalar('SELECT SUM(cogs_cents) FROM sale_items'), 600)

    def test_tab_freezes_price_and_preserves_reservation(self):
        from salva_ai_v2.sales.models import Payment
        tab = self.sales.create_tab('João', 'tab1')
        self.sales.set_tab_qty(tab, self.pid, 3, None, None, 'add1')
        self.pricing.set_promotion(self.pid, 3, 1100, True, 'promo2')
        self.assertEqual(self.inventory.position(self.pid).reserved, 3)
        self.assertIn('Comandas abertas', self.cash.blockers(self.session))
        self.sales.set_tab_qty(tab, self.pid, 0, self.grant('tab.reduce'), 'Remoção teste', 'remove1')
        self.sales.set_tab_qty(tab, self.pid, 3, None, None, 'add2')
        sale = self.sales.pay_tab(tab, Payment('PIX', None), 'pay1')
        self.assertEqual(sale.total_cents, 1200)
        self.assertEqual(self.inventory.position(self.pid).reserved, 0)
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)

    def test_invalid_payment_and_rollback(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.common.errors import BusinessError
        cart = self.sales.create_cart('cart1')
        self.sales.set_cart_qty(cart, self.pid, 3, 'add1')
        with self.assertRaises(BusinessError):
            self.sales.sell(cart, Payment('MONEY', 100), 'short1')
        with patch('salva_ai_v2.common.audit.Audit.record', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                self.sales.sell(cart, Payment('PIX', None), 'fail1')
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 0)
        self.assertEqual(self.inventory.position(self.pid).physical, 20)

    def test_inactive_product_can_pay_reserved_but_not_increase(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.common.errors import BusinessError
        tab = self.sales.create_tab('João', 'tab1')
        self.sales.set_tab_qty(tab, self.pid, 3, None, None, 'add1')
        self.inventory.deactivate(self.pid, self.grant('product.deactivate'), 'Fora de linha', 'off1')
        with self.assertRaises(BusinessError):
            self.sales.set_tab_qty(tab, self.pid, 4, None, None, 'more1')
        sale = self.sales.pay_tab(tab, Payment('PIX', None), 'pay1')
        self.assertEqual(sale.total_cents, 1200)

    def test_reverse_preserves_original_and_reopens_same_session(self):
        from salva_ai_v2.sales.models import Payment
        tab = self.sales.create_tab('João', 'tab1')
        self.sales.set_tab_qty(tab, self.pid, 3, None, None, 'add1')
        sale = self.sales.pay_tab(tab, Payment('MONEY', 1200), 'pay1')
        self.sales.reverse_sale(sale.id, True, Payment('MONEY', 1200), True,
                                self.grant('sale.reverse'), 'Pagamento por engano', 'reverse1')
        self.assertEqual(self.inventory.position(self.pid).physical, 20)
        self.assertEqual(self.inventory.position(self.pid).reserved, 3)
        self.assertEqual(self.cash.position(self.session).expected_cents, 10000)
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 1)
