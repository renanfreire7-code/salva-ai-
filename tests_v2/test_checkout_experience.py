from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class CheckoutExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681942');s=self.app.services
        self.pid=s.inventory.create_product('Cerveja Heineken Latão',500,12,6,'p')
        s.inventory.receive_purchase([PurchaseLine(self.pid,20,4000)],0,s.clock.today(),s.clock.today(),'buy')
        s.pricing.set_promotion(self.pid,3,1200,True,'promo');s.cash.open(10000,'open')
        self.app.refresh()

    def test_catalog_search_and_payment_keep_order_until_confirmed(self):
        from salva_ai_v2.ui.payment import PaymentDialog
        view=self.app.sales_view
        view.search.set('CHL');view.filter_products()
        self.assertEqual(view.product_tree.get_children(),(str(self.pid),))
        view.add_product(self.pid,3)
        dialog=PaymentDialog(view,view.total_cents,on_submit=view.submit)
        dialog.inputs['received'].delete(0,'end');dialog.inputs['received'].insert(0,'10,00')
        self.assertFalse(dialog.submit())
        self.assertEqual(view.total_cents,1200)
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM sales').fetchone()[0],0)
        dialog.inputs['received'].delete(0,'end');dialog.inputs['received'].insert(0,'20,00')
        dialog.update_change()
        self.assertIn('8,00',dialog.change.get())
        with patch('salva_ai_v2.ui.payment.messagebox.askyesno',return_value=True):
            self.assertTrue(dialog.submit())
        self.assertEqual(view.total_cents,0)
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM sales').fetchone()[0],1)

    def test_pix_selector_disables_cash_and_never_changes_drawer(self):
        from salva_ai_v2.ui.payment import PaymentDialog
        self.app.sales_view.add_product(self.pid,1)
        dialog=PaymentDialog(self.app.sales_view,500,on_submit=self.app.sales_view.submit)
        dialog.inputs['method'].set('Pix');dialog.update_method()
        self.assertEqual(str(dialog.inputs['received'].cget('state')),'disabled')
        with patch('salva_ai_v2.ui.payment.messagebox.askyesno',return_value=True):dialog.submit()
        session=self.app.services.cash.active()['id']
        self.assertEqual(self.app.services.cash.position(session).expected_cents,10000)

    def test_product_form_validation_preserves_name_then_creates(self):
        from salva_ai_v2.ui.forms import FormDialog
        dialogs=[]
        def capture(*args,**kwargs):
            dialogs.append(FormDialog(*args,**kwargs))
        with patch('salva_ai_v2.ui.products.ask_fields',side_effect=capture):
            self.app.products_view.create()
        dialog=dialogs[0]
        dialog.inputs['name'].insert(0,'Produto novo')
        dialog.inputs['price'].delete(0,'end');dialog.inputs['price'].insert(0,'inválido')
        self.assertFalse(dialog.submit())
        self.assertEqual(dialog.inputs['name'].get(),'Produto novo')
        dialog.inputs['price'].delete(0,'end');dialog.inputs['price'].insert(0,'8,00')
        self.assertTrue(dialog.submit())
        self.assertTrue(any(p['name']=='Produto novo' for p in self.app.services.inventory.products()))

    def test_purchase_form_uses_choices_and_preserves_input_after_error(self):
        from tkinter import ttk
        from salva_ai_v2.ui.forms import FormDialog
        dialogs=[]
        view=self.app.products_view;view.tree.selection_set(str(self.pid))
        with patch('salva_ai_v2.ui.products.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):
            view.purchase()
        dialog=dialogs[0]
        self.assertIsInstance(dialog.inputs['payment'],ttk.Combobox)
        dialog.inputs['cost'].insert(0,'errado')
        self.assertFalse(dialog.submit())
        self.assertEqual(dialog.inputs['qty'].get(),'1')
        dialog.inputs['cost'].delete(0,'end');dialog.inputs['cost'].insert(0,'2,00')
        self.assertTrue(dialog.submit())
        self.assertEqual(self.app.services.inventory.position(self.pid).physical,21)

    def test_edit_product_commits_from_preserved_form(self):
        from salva_ai_v2.ui.forms import FormDialog
        dialogs=[];view=self.app.products_view;view.tree.selection_set(str(self.pid))
        with patch('salva_ai_v2.ui.products.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.edit()
        dialog=dialogs[0]
        dialog.inputs['price'].delete(0,'end');dialog.inputs['price'].insert(0,'8,00')
        with patch.object(view,'grant',side_effect=lambda action:self.app.security.authorize('681942',action)),patch.object(view,'reason',return_value='Preço revisado'):
            self.assertTrue(dialog.submit())
        self.assertEqual(self.app.services.inventory.products()[0]['price_cents'],800)
