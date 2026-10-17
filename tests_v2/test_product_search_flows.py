from pathlib import Path
import tempfile,unittest
from tests_v2.application_support import build_test_application


class ProductSearchFlowsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=build_test_application(Path(self.tmp.name));self.addCleanup(self.app.close)
        from salva_ai_v2.inventory.models import PurchaseLine
        s=self.app.services
        self.pid=s.inventory.create_product('Cerveja Heineken Latão',500,1,0,'p')
        self.other=s.inventory.create_product('Cerveja outra marca',500,1,0,'other')
        s.inventory.receive_purchase([PurchaseLine(self.pid,30,6000),PurchaseLine(self.other,10,2000)],0,s.clock.today(),s.clock.today(),'buy')
        s.inventory.assign_shortcut(1,self.pid,'key');s.cash.open(10000,'open');self.app.refresh()

    def test_hei_prefix_and_initials_in_all_three_flows(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("salva_ai_v2.ui.product_table"))
        from salva_ai_v2.ui.product_table import ProductTable
        tab=self.app.services.sales.create_tab('Cliente','tab');self.app.tabs_view.refresh();self.app.tabs_view.tabs_tree.selection_set(str(tab))
        editor=self.app.delivery_view.create()
        for view in (self.app.sales_view,self.app.tabs_view,editor):
            with self.subTest(view=type(view).__name__):
                self.assertIsInstance(view.candidates,ProductTable)
                for query in ('hei','cer hei','CHL'):
                    view.search.set(query);view.filter_products();self.assertEqual(view.candidates.get_children(),(str(self.pid),))
                view.choose_product();self.assertEqual(view.selected_name.get(),'Cerveja Heineken Latão')
                self.assertEqual(view.selected_product(),self.pid)
                view.search.set('cer');view.filter_products()
                from salva_ai_v2.common.errors import BusinessError
                with self.assertRaises(BusinessError):view.selected_product()
                view.select_shortcut(1);self.assertEqual(view.selected_product(),self.pid)
        editor.winfo_toplevel().destroy()

    def test_full_names_in_every_product_surface(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('salva_ai_v2.ui.product_table'))
        from salva_ai_v2.ui.product_table import ProductTable
        app=self.app
        surfaces=[app.products_view.tree,app.sales_view.tree,app.sales_view.product_tree,app.tabs_view.items_tree,
            app.purchases_view.items_tree,app.history_view.details.items_tree,app.results_view.tree,app.replenishment_view.tree]
        for table in surfaces:self.assertIsInstance(table,ProductTable)
        editor=app.delivery_view.create();self.assertIsInstance(editor.tree,ProductTable);editor.winfo_toplevel().destroy()
        settle=app.delivery_view.settlement();self.assertIsInstance(settle.details.items_tree,ProductTable);settle.winfo_toplevel().destroy()

    def test_candidates_precede_order_lines_and_actions_fit_long_names(self):
        app=self.app
        s=app.services;name=('Cerveja Heineken '+('edição especial '*12)).strip()
        s.inventory.update_product(self.pid,name,500,1,0,s.security.authorize('681','product.edit'),'Nome completo para conferir','rename')
        app.window.geometry('1260x680');app.window.update()
        editor=app.delivery_view.create();editor.search.set('hei');editor.filter_products();app.window.update()
        self.assertLess(editor.candidates.winfo_rooty(),editor.tree.winfo_rooty())
        self.assertEqual(editor.candidates.cell(str(self.pid),'Produto').cget('text'),name)
        editor.choose_product();editor.qty.event_generate('<Return>');app.window.update()
        self.assertEqual(editor.lines,{self.pid:1})
        self.assertEqual(editor.tree.cell(str(self.pid),'Produto').cget('text'),name)
        from tkinter import ttk
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        for control in descendants(editor):
            if isinstance(control,ttk.Button) and control.winfo_ismapped():
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),editor.winfo_toplevel().winfo_rooty()+editor.winfo_toplevel().winfo_height())
        editor.winfo_toplevel().destroy()

    def test_history_details_keep_product_and_payment_readable(self):
        from salva_ai_v2.sales.models import Payment
        app=self.app;s=app.services
        cart=s.sales.create_cart('cart');s.sales.set_cart_qty(cart,self.pid,1,'qty');sale=s.sales.sell(cart,Payment('PIX'),'sale')
        app.window.geometry('1260x680');app.show_view(app.history_view)
        app.history_view.tree.selection_set(f'sale:{sale.id}');app.history_view.show_selected();app.window.update()
        self.assertGreaterEqual(app.history_view.details.winfo_width(),450)
        self.assertGreaterEqual(app.history_view.details.facts.winfo_height(),70)
