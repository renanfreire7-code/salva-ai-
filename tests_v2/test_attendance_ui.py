from pathlib import Path
import tempfile
import unittest


class AttendanceUITest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = build_application(Path(self.tmp.name))
        self.addCleanup(self.app.close)
        self.app.security.setup('681942')
        s = self.app.services
        self.pid = s.inventory.create_product('Cerveja Pilsen', 500, 12, 6, 'p1')
        s.inventory.receive_purchase([PurchaseLine(self.pid, 20, 4000)], 0, s.clock.today(), s.clock.today(), 'buy1')
        s.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        s.cash.open(10000, 'open1')
        self.app.refresh()

    def test_selection_does_not_sell_and_confirm_resets_cart(self):
        from salva_ai_v2.sales.models import Payment
        view = self.app.sales_view
        view.add_product(self.pid, 3)
        self.assertEqual(view.total_cents, 1200)
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM sales').fetchone()[0], 0)
        view.submit(Payment('MONEY', 2000))
        self.assertEqual(view.total_cents, 0)
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM sales').fetchone()[0], 1)

    def test_invalid_payment_preserves_cart(self):
        from salva_ai_v2.sales.models import Payment
        from salva_ai_v2.common.errors import BusinessError
        view = self.app.sales_view
        view.add_product(self.pid, 3)
        with self.assertRaises(BusinessError):
            view.submit(Payment('MONEY', 10))
        self.assertEqual(view.total_cents, 1200)

    def test_search_and_shortcuts_only_select(self):
        from salva_ai_v2.inventory.queries import search_products
        self.assertEqual(search_products(self.app.services.inventory.products(), '001')[0]['id'], self.pid)
        self.assertEqual(search_products(self.app.services.inventory.products(), 'cerveja')[0]['id'], self.pid)
        self.app.services.inventory.assign_shortcut(1, self.pid, 'key1')
        self.app.sales_view.select_shortcut(1)
        self.app.sales_view.filter_products()
        self.assertEqual(self.app.sales_view.selected_product(), self.pid)
        self.assertEqual(self.app.sales_view.total_cents, 0)
