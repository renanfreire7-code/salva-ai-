from pathlib import Path
from datetime import date
from tests_v2.delivery_support import DeliveryCase


class ResultsTest(DeliveryCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/reporting/queries.py').exists(), 'Resultados ainda não implementados')
        from salva_ai_v2.reporting.queries import ReportingQueries
        self.reports = ReportingQueries(self.db)

    def test_product_delivery_and_operating_result(self):
        from salva_ai_v2.finance.models import ExpenseDraft
        self.pricing.set_promotion(self.pid, 3, 1200, True, 'promo1')
        order = self.delivery.confirm(self.draft(qty=3), 'order1')
        self.delivery.dispatch(order.id, 'dispatch1')
        self.finance.add_expense(ExpenseDraft('Despesa teste', 'Outras despesas', 100, date(2026,10,1), date(2026,10,16)), False, 'expense1')
        result = self.reports.monthly('2026-10')
        self.assertEqual(result.product_result_cents, 500)
        self.assertEqual((result.delivery_revenue_cents, result.delivery_cost_cents, result.total_result_cents), (500, 700, 300))
        self.assertEqual(sum(r.allocated_cents for r in self.reports.profitability('2026-10')), 100)

    def test_export_bundle_uses_reais_not_internal_cents(self):
        from decimal import Decimal
        order = self.delivery.confirm(self.draft(qty=3), 'order1')
        self.delivery.dispatch(order.id, 'dispatch1')
        bundle = self.reports.bundle('2026-10')
        self.assertEqual(bundle.sheets['Lucro por produto'][1][2], Decimal('15.00'))
        self.assertIn('R$', bundle.sheets['Lucro por produto'][0][2])

    def test_das_once_and_no_sales_no_fake_margin(self):
        from salva_ai_v2.finance.models import ExpenseDraft
        from salva_ai_v2.finance.settings import FinancialSettings
        settings = FinancialSettings(self.db, self.security)
        settings.set_das(100, self.grant('settings.finance'), 'Configuração inicial', 'das1')
        self.finance.add_expense(ExpenseDraft('DAS', 'DAS MEI', 100, date(2026,10,1), date(2026,10,16)), False, 'expense1')
        result = self.reports.monthly('2026-10')
        self.assertEqual(result.das_cents, 100)
        self.assertEqual(result.total_result_cents, -100)
        self.assertEqual(self.reports.profitability('2026-10'), [])

    def test_later_correction_does_not_rewrite_previous_month(self):
        from salva_ai_v2.sales.models import Payment
        cart = self.sales.create_cart('cart1')
        self.sales.set_cart_qty(cart, self.pid, 1, 'add1')
        sale = self.sales.sell(cart, Payment('MONEY', 500), 'sell1')
        self.clock.advance(31*86400)
        self.sales.reverse_sale(sale.id, True, Payment('MONEY', 500), False, self.grant('sale.reverse'), 'Correção no mês seguinte', 'reverse1')
        self.assertEqual(self.reports.monthly('2026-10').revenue_cents, 500)
        self.assertEqual(self.reports.monthly('2026-11').revenue_cents, -500)
        self.assertEqual(self.reports.monthly('2026-11').cogs_cents, -200)
