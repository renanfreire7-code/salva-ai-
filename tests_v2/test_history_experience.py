from pathlib import Path
import tempfile
import unittest


class HistoryExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681');s=self.app.services
        self.pid=s.inventory.create_product('Cerveja',500,1,0,'p')
        s.inventory.receive_purchase([PurchaseLine(self.pid,20,4000)],0,s.clock.today(),s.clock.today(),'buy')
        s.cash.open(10000,'open')

    def test_commercial_rows_show_sale_items_and_keep_audit_accessible(self):
        from salva_ai_v2.sales.models import Payment
        s=self.app.services;cart=s.sales.create_cart('cart')
        s.sales.set_cart_qty(cart,self.pid,2,'qty');sale=s.sales.sell(cart,Payment('PIX'),'sale')
        view=self.app.history_view;view.refresh()
        self.assertIn(f'sale:{sale.id}',view.tree.get_children())
        view.tree.selection_set(f'sale:{sale.id}');view.show_selected()
        values=str(view.details.items_tree.item(str(self.pid),'values'))
        self.assertIn('Cerveja',values)
        self.assertIn('10,00',values)
        audit=view.open_audit()
        self.assertTrue(callable(audit.backup_center))
        self.assertTrue(callable(audit.reverse))
        audit.winfo_toplevel().destroy()

    def test_delivery_history_has_separate_key_and_complete_detail(self):
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        s=self.app.services
        order=s.delivery.confirm(DeliveryDraft('João','123','Rua 10','Portão',[CartLine(self.pid,2)],'PIX','BAR','ADVANCE','PIX'),'order')
        view=self.app.history_view;view.refresh()
        view.tree.selection_set(f'delivery:{order.id}');view.show_selected()
        self.assertIn('João',view.details.summary.get())
        text=view.details.facts.get('1.0','end')
        self.assertIn('Rua 10',text)
        self.assertIn('Antecipado',text)

    def test_counter_and_tab_history_show_actual_mode_and_cash_change(self):
        from salva_ai_v2.sales.models import Payment
        s=self.app.services;view=self.app.history_view
        cart=s.sales.create_cart('cart');s.sales.set_cart_qty(cart,self.pid,2,'qty')
        cash=s.sales.sell(cart,Payment('MONEY',2000),'cash')
        tab=s.sales.create_tab('Cliente Pix','tab');s.sales.set_tab_qty(tab,self.pid,2,None,None,'tab-qty')
        pix=s.sales.pay_tab(tab,Payment('PIX'),'pix')
        view.refresh()
        for sale,method in [(cash,'Dinheiro'),(pix,'Pix')]:
            with self.subTest(method=method):
                key=f'sale:{sale.id}';view.tree.selection_set(key);view.show_selected()
                self.assertIn(method,str(view.tree.item(key,'values')))
                text=view.details.facts.get('1.0','end');self.assertIn(method,text)
                if sale==cash:
                    self.assertIn('Cliente entregou: R$ 20,00',text);self.assertIn('Troco: R$ 10,00',text)
                else:self.assertNotIn('Troco:',text)
        s.sales.reverse_sale(cash.id,True,None,False,s.security.authorize('681','sale.reverse'),'Reembolso ainda pendente','reverse')
        view.refresh();self.assertIn('Reembolso pendente',str(view.tree.item(f'sale:{cash.id}','values')))

    def test_delivery_history_keeps_payment_state_separate_from_delivery(self):
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        s=self.app.services;view=self.app.history_view
        order=s.delivery.confirm(DeliveryDraft('João','123','Rua','',[CartLine(self.pid,2)],'PIX','BAR','ON_DELIVERY','PIX'),'order')
        s.delivery.dispatch(order.id,'out');s.delivery.mark_delivered(order.id,'delivered');view.refresh()
        key=f'delivery:{order.id}';values=str(view.tree.item(key,'values'))
        self.assertIn('Entregue',values);self.assertIn('Pendente',values)
        s.delivery.record_payment(order.id,'PIX',1000,'BAR',None,'payment');view.refresh()
        values=str(view.tree.item(key,'values'));self.assertIn('Pago',values);self.assertIn('Pix',values)
        s.delivery.cancel(order.id,s.security.authorize('681','delivery.cancel'),'Cliente devolveu o pedido','cancel');view.refresh()
        self.assertIn('Reembolso pendente',str(view.tree.item(key,'values')))
