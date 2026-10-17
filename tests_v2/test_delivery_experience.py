from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class DeliveryExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        from salva_ai_v2.inventory.models import PurchaseLine
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681');s=self.app.services
        self.pid=s.inventory.create_product('Cerveja Heineken Latão',500,12,6,'p')
        s.inventory.receive_purchase([PurchaseLine(self.pid,20,4000)],0,s.clock.today(),s.clock.today(),'buy')
        s.cash.open(10000,'open');s.delivery.configure_fees(500,700,'fees')
        s.inventory.assign_shortcut(1,self.pid,'key');self.app.refresh()

    def editor(self):
        self.app.show_view(self.app.delivery_view)
        editor=self.app.delivery_view.create()
        self.assertIsNotNone(editor)
        return editor

    def populate(self,editor,qty=8):
        for key,value in dict(customer='Cliente',phone='11999999999',address='Rua 10',reference='Portão').items():editor.fields[key].insert(0,value)
        editor.lines[self.pid]=qty;editor.refresh()

    def test_editor_shortcut_and_enter_dont_touch_background_cart(self):
        self.app.sales_view.add_product(self.pid,1)
        editor=self.editor();editor.master.update();editor.picker.focus_force()
        editor.picker.event_generate('<F1>');editor.master.update()
        self.assertEqual(editor.selected_product(),self.pid)
        self.assertEqual(editor.lines,{})
        editor.qty.event_generate('<Return>');editor.master.update()
        self.assertEqual(editor.lines,{self.pid:1})
        self.assertEqual(self.app.sales_view.total_cents,500)
        editor.master.destroy()

    def test_switching_payment_clears_incompatible_change(self):
        editor=self.editor();self.populate(editor)
        editor.change_needed.set('Sim');editor.update_payment()
        editor.change_for.insert(0,'50,00');editor.refresh()
        self.assertIn('5,00',editor.change_summary.get())
        editor.channel.set('Pix');editor.update_payment()
        self.assertEqual(str(editor.change_for.cget('state')),'disabled')
        self.assertEqual(editor.change_for.get(),'')
        order=editor.submit()
        row=self.app.db.conn.execute('SELECT * FROM delivery_orders WHERE order_id=?',(order.id,)).fetchone()
        self.assertEqual((row['payment_channel'],row['change_for_cents']),('PIX',None))

    def test_invalid_stock_preserves_customer_address_and_items(self):
        editor=self.editor();self.populate(editor,100)
        self.assertFalse(editor.submit())
        self.assertTrue(editor.winfo_exists())
        self.assertEqual(editor.fields['address'].get(),'Rua 10')
        self.assertEqual(editor.lines,{self.pid:100})
        self.assertTrue(editor.error.get())
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM orders').fetchone()[0],0)
        editor.master.destroy()

    def test_advance_unpaid_disables_dispatch_and_explains_why(self):
        editor=self.editor();self.populate(editor)
        editor.timing.set('Antecipado');editor.update_payment()
        order=editor.submit();view=self.app.delivery_view
        view.refresh();view.tree.selection_set(str(order.id));view.update_actions()
        self.assertTrue(view.action_buttons['dispatch'].instate(['disabled']))
        self.assertIn('antecipado',view.action_hint.get())
        self.app.services.delivery.record_payment(order.id,'PIX',4500,'BAR',None,'pay')
        view.refresh();view.update_actions()
        self.assertFalse(view.action_buttons['dispatch'].instate(['disabled']))

    def test_receipt_difference_refusal_keeps_form_and_unpaid_order(self):
        from salva_ai_v2.ui.delivery_receipt import DeliveryReceiptDialog
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        s=self.app.services
        s.settlements.fund_courier(6000,s.security.authorize('681','delivery.float'),'Troco para entregas','float')
        draft=DeliveryDraft('Cliente','123','Rua','',[CartLine(self.pid,8)],'MONEY','COURIER','ON_DELIVERY','MONEY',5000)
        order=s.delivery.confirm(draft,'order')
        dialog=DeliveryReceiptDialog(self.app.window,s,order.id)
        dialog.inputs['received'].delete(0,'end');dialog.inputs['received'].insert(0,'100,00')
        with patch('salva_ai_v2.ui.delivery_receipt.messagebox.askyesno',return_value=False):self.assertFalse(dialog.submit())
        self.assertEqual(s.delivery.order(order.id).paid_cents,0)
        self.assertEqual(dialog.inputs['received'].get(),'100,00')
        with patch('salva_ai_v2.ui.delivery_receipt.messagebox.askyesno',return_value=True):self.assertTrue(dialog.submit())
        self.assertEqual(s.delivery.order(order.id).paid_cents,4500)

    def test_link_refund_uses_actual_debit_and_retains_form_after_error(self):
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        from salva_ai_v2.ui.forms import FormDialog
        s=self.app.services;view=self.app.delivery_view
        draft=DeliveryDraft('Cliente','123','Rua','',[CartLine(self.pid,2)],'CREDIT','BAR','ADVANCE','LINK')
        order=s.delivery.confirm(draft,'order');s.delivery.record_payment(order.id,'DEBIT',1500,'BAR',None,'payment')
        s.delivery.cancel(order.id,s.security.authorize('681','delivery.cancel'),'Cancelado pelo cliente','cancel')
        view.refresh();view.tree.selection_set(str(order.id));dialogs=[]
        with patch('salva_ai_v2.ui.delivery.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.refund()
        dialog=dialogs[0];dialog.inputs['amount'].delete(0,'end');dialog.inputs['amount'].insert(0,'999,00')
        with patch.object(view,'grant',side_effect=lambda action:s.security.authorize('681',action)),patch.object(view,'reason',return_value='Reembolso confirmado'):
            self.assertFalse(dialog.submit());self.assertEqual(dialog.inputs['amount'].get(),'999,00')
            dialog.inputs['amount'].delete(0,'end');dialog.inputs['amount'].insert(0,'15,00');self.assertTrue(dialog.submit())
        self.assertEqual(self.app.db.conn.execute('SELECT pending_cents FROM refunds WHERE order_id=?',(order.id,)).fetchone()[0],0)
        self.assertEqual(self.app.db.conn.execute("SELECT method FROM receipt_events WHERE delta_cents<0").fetchone()[0],'DEBIT')
        self.assertEqual(s.cash.position(s.cash.require_open()['id']).expected_cents,10000)

    def test_bar_cash_refund_defaults_to_drawer(self):
        from salva_ai_v2.delivery.models import DeliveryDraft
        from salva_ai_v2.inventory.models import CartLine
        from salva_ai_v2.ui.forms import FormDialog
        s=self.app.services;view=self.app.delivery_view
        order=s.delivery.confirm(DeliveryDraft('Cliente','123','Rua','',[CartLine(self.pid,2)],'MONEY','BAR','ON_DELIVERY','MONEY'),'order')
        s.delivery.record_payment(order.id,'MONEY',1500,'BAR',1500,'payment')
        s.delivery.cancel(order.id,s.security.authorize('681','delivery.cancel'),'Cancelado pelo cliente','cancel')
        view.refresh();view.tree.selection_set(str(order.id));dialogs=[]
        with patch('salva_ai_v2.ui.delivery.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.refund()
        dialog=dialogs[0];self.assertEqual(dialog.inputs['drawer'].get(),'Sim')
        with patch.object(view,'grant',side_effect=lambda action:s.security.authorize('681',action)),patch.object(view,'reason',return_value='Reembolso confirmado'):
            self.assertTrue(dialog.submit())
        self.assertEqual(s.cash.position(s.cash.require_open()['id']).expected_cents,10000)
