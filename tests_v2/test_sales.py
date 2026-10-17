from unittest.mock import patch
from tests_v2.commerce_support import CommerceCase


class SalesTest(CommerceCase):
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


    def test_pending_refund_can_be_concluded_later(self):
        from salva_ai_v2.sales.models import Payment
        cart=self.sales.create_cart('cart1')
        self.sales.set_cart_qty(cart,self.pid,1,'add1')
        sale=self.sales.sell(cart,Payment('MONEY',500),'pay1')
        self.sales.reverse_sale(sale.id,True,None,False,self.grant('sale.reverse'),'Reembolso a concluir','reverse1')
        self.assertIn('Reembolso pendente',self.cash.blockers(self.session))
        self.sales.confirm_refund(sale.id,Payment('MONEY',500),self.grant('sale.refund'),'Dinheiro devolvido','refund1')
        self.assertNotIn('Reembolso pendente',self.cash.blockers(self.session))
        self.assertEqual(self.cash.position(self.session).expected_cents,10000)
