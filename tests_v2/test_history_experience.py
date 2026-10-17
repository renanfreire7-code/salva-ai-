from pathlib import Path
import tempfile
import unittest


class HistoryExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681942');s=self.app.services
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
