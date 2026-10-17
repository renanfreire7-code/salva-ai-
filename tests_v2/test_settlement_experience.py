from pathlib import Path
import tempfile
import unittest


class SettlementExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine,CartLine
        from salva_ai_v2.delivery.models import DeliveryDraft
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681');s=self.app.services
        self.pid=s.inventory.create_product('Cerveja',500,1,0,'p')
        s.inventory.receive_purchase([PurchaseLine(self.pid,20,4000)],0,s.clock.today(),s.clock.today(),'buy')
        s.cash.open(10000,'open');s.delivery.configure_fees(500,700,'fees')
        self.order=s.delivery.confirm(DeliveryDraft('Cliente','123','Rua 10','Portão',[CartLine(self.pid,8)],'MONEY','COURIER'),'order')
        self.trip=s.delivery.dispatch(self.order.id,'dispatch')
        self.collection=s.delivery.record_payment(self.order.id,'MONEY',4500,'COURIER',4500,'receipt')

    def test_selection_without_ctrl_shows_complete_order(self):
        from salva_ai_v2.ui.settlement import SettlementView
        import tkinter as tk
        window=tk.Toplevel(self.app.window);view=SettlementView(window,self.app.services);view.pack(fill='both',expand=True)
        view.toggle_order(self.order.id,True)
        self.assertEqual(view.selected_collections,{self.collection})
        self.assertEqual(view.selected_trips,{self.trip})
        self.assertEqual(view.selection_totals(),(4500,700))
        view.tree.selection_set(str(self.order.id));view.show_selected()
        self.assertIn('Cerveja',str(view.details.items_tree.item(str(self.pid),'values')))
        window.destroy()

    def test_completed_settlement_remains_discriminated(self):
        from salva_ai_v2.ui.settlement import SettlementView
        import tkinter as tk
        s=self.app.services
        grant=s.security.authorize('681','delivery.settle')
        settled=s.settlements.settle([self.collection],[self.trip],3800,0,700,grant,'settle')
        window=tk.Toplevel(self.app.window);view=SettlementView(window,s);view.pack(fill='both',expand=True)
        view.records_tree.selection_set(str(settled.id));view.show_record()
        text=view.record_text.get('1.0','end')
        self.assertIn('38,00',text);self.assertIn('7,00',text)
        self.assertIn('Cerveja',text);self.assertIn('Rua 10',text)
        self.assertEqual(view.selection_totals(),(0,0))
        window.destroy()
