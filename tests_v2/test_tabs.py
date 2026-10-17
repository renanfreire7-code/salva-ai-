from tests_v2.commerce_support import CommerceCase


class TabsTest(CommerceCase):
    def test_reduction_and_cancel_require_authorization(self):
        from salva_ai_v2.common.errors import BusinessError
        tab=self.sales.create_tab('João','tab1')
        self.sales.set_tab_qty(tab,self.pid,3,None,None,'add1')
        with self.assertRaises(BusinessError):
            self.sales.set_tab_qty(tab,self.pid,2,None,'Correção teste','reduce1')
        with self.assertRaises(BusinessError):
            self.sales.cancel_tab(tab,None,'Cancelamento teste','cancel1')
        self.assertEqual(self.inventory.position(self.pid).reserved,3)
        self.sales.cancel_tab(tab,self.grant('tab.cancel'),'Cliente desistiu','cancel2')
        self.assertEqual(self.inventory.position(self.pid).reserved,0)
        self.assertEqual(self.inventory.position(self.pid).physical,20)

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
