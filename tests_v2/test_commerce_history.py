from tests_v2.commerce_support import CommerceCase
from salva_ai_v2.sales.models import Payment


class CommerceHistoryTest(CommerceCase):
    def queries(self):
        from salva_ai_v2.reporting.commerce import CommerceQueries
        return CommerceQueries(self.db)

    def filters(self,**kwargs):
        from salva_ai_v2.reporting.commerce_models import CommerceFilter
        return CommerceFilter(self.clock.today(),self.clock.today(),**kwargs)

    def test_reopened_tab_has_separate_sales_with_frozen_items(self):
        tab=self.sales.create_tab('João','tab')
        self.sales.set_tab_qty(tab,self.pid,1,None,None,'qty')
        first=self.sales.pay_tab(tab,Payment('PIX'),'first')
        self.sales.reverse_sale(first.id,True,Payment('PIX'),True,self.grant('sale.reverse'),'Cliente retomou consumo','reverse')
        self.sales.set_tab_qty(tab,self.pid,2,None,None,'more')
        second=self.sales.pay_tab(tab,Payment('PIX'),'second')
        self.inventory.update_product(self.pid,'Nome novo',500,12,6,self.grant('product.edit'),'Renomeado no cadastro','rename')
        rows=self.queries().list(self.filters(kind='TAB'))
        self.assertEqual({r.sale_id for r in rows},{first.id,second.id})
        self.assertEqual(self.queries().detail(f'sale:{first.id}')['items'][0].qty,1)
        self.assertEqual(self.queries().detail(f'sale:{second.id}')['items'][0].qty,2)
        self.assertEqual(self.queries().detail(f'sale:{first.id}')['items'][0].name,'Lata')
        self.assertEqual(next(r for r in rows if r.sale_id==first.id).state,'REVERSED')

    def test_counter_history_search_and_sale_date(self):
        cart=self.sales.create_cart('cart')
        self.sales.set_cart_qty(cart,self.pid,3,'qty')
        sale=self.sales.sell(cart,Payment('MONEY',2000),'sale')
        rows=self.queries().list(self.filters(text='Lata'))
        self.assertEqual([(r.key,r.total_cents,r.kind) for r in rows],[(f'sale:{sale.id}',1200,'CART')])
        self.assertEqual(self.queries().list(self.filters(text="' OR 1=1 --")),[])
        self.clock.advance(86400)
        self.assertEqual(self.queries().list(self.filters()),[])
