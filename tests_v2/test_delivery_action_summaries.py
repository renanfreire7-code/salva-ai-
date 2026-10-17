from pathlib import Path
import tempfile,unittest,importlib.util
from unittest.mock import patch
from tests_v2.application_support import build_test_application
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.inventory.models import PurchaseLine,CartLine
from salva_ai_v2.common.errors import BusinessError


class DeliveryActionSummaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=build_test_application(Path(self.tmp.name));self.addCleanup(self.app.close);self.s=self.app.services
        self.pid=self.s.inventory.create_product('Cerveja Heineken Latão',500,1,0,'p')
        self.s.inventory.receive_purchase([PurchaseLine(self.pid,20,4000)],0,self.s.clock.today(),self.s.clock.today(),'buy')
        self.session=self.s.cash.open(10000,'open');self.s.delivery.configure_fees(500,700,'fees')
        self.draft=DeliveryDraft('João','123','Rua 10','Farmácia',[CartLine(self.pid,2)],'MONEY','BAR','ON_DELIVERY','MONEY',None,'','Apartamento 202')
        self.order=self.s.delivery.confirm(self.draft,'order');self.view=self.app.delivery_view
        self.view.refresh();self.view.tree.selection_set(str(self.order.id))

    def grant(self,action):return self.s.security.authorize('681',action)

    def test_action_labels_and_summary_match_actual_facts(self):
        self.assertEqual(self.view.action_buttons['refund'].cget('text'),'Registrar reembolso')
        self.assertIsNotNone(importlib.util.find_spec('salva_ai_v2.ui.delivery_actions'))
        from salva_ai_v2.ui.delivery_actions import action_summary
        from dataclasses import replace
        other=self.s.delivery.confirm(replace(self.draft,payment_method='CREDIT',payment_timing='ADVANCE',payment_channel='LINK'),'link')
        self.s.delivery.record_payment(other.id,'DEBIT',1500,'BAR',None,'received')
        detail=self.s.delivery_queries.detail(other.id)
        text=action_summary(detail,'CANCEL')
        for expected in ('João','Apartamento 202','Cerveja Heineken Latão','15,00','Débito'):self.assertIn(expected,text)

    def test_declined_summary_or_pin_is_noop(self):
        self.assertIsNotNone(importlib.util.find_spec('salva_ai_v2.ui.delivery_actions'))
        before='\n'.join(self.app.db.conn.iterdump())
        with patch('salva_ai_v2.ui.delivery_actions.messagebox.askyesno',return_value=False),patch.object(self.view,'grant') as grant,patch.object(self.view,'reason',return_value='Teste de reembolso'):
            self.view.cancel();grant.assert_not_called()
        self.assertEqual(before,'\n'.join(self.app.db.conn.iterdump()))
        with patch('salva_ai_v2.ui.delivery_actions.messagebox.askyesno',return_value=True),patch.object(self.view,'grant',side_effect=BusinessError('Operação cancelada.')):
            with self.assertRaises(BusinessError):self.view.cancel()
        self.assertEqual(before,'\n'.join(self.app.db.conn.iterdump()))

    def test_completed_actions_keep_financial_separation(self):
        self.s.delivery.dispatch(self.order.id,'dispatch');self.s.delivery.record_payment(self.order.id,'MONEY',1500,'BAR',1500,'receipt')
        self.s.delivery.cancel(self.order.id,self.grant('delivery.cancel'),'Cliente desistiu','cancel')
        self.s.delivery.refund(self.order.id,'MONEY',1500,True,self.grant('delivery.refund'),'Devolvido ao cliente','refund')
        self.assertEqual(self.s.inventory.position(self.pid).physical,18)
        self.s.delivery.confirm_return(self.order.id,[CartLine(self.pid,2)],self.grant('delivery.return'),'Produto conferido','return')
        self.assertEqual(self.s.inventory.position(self.pid).physical,20);self.assertEqual(self.s.cash.position(self.session).expected_cents,10000)
        new=self.s.delivery.redeliver(self.order.id,self.grant('delivery.redeliver'),'Novo envio combinado','retry')
        self.assertEqual(self.s.delivery.order(new).state,'PREPARING')
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM trips').fetchone()[0],1)

    def test_tab_last_field_enter_only_focuses_create(self):
        view=self.app.tabs_view;self.app.show_view(view);view.customer.insert(0,'Cliente');self.app.window.update()
        view.customer.focus_force();view.customer.event_generate('<Return>');self.app.window.update()
        self.assertEqual(self.s.sales.open_tabs(),[])
        self.assertEqual(view.focus_get(),view.create_button)
        view.create_button.event_generate('<Return>');self.app.window.update();self.assertEqual(len(self.s.sales.open_tabs()),1)

    def test_return_error_preserves_quantity(self):
        self.s.delivery.dispatch(self.order.id,'dispatch');self.s.delivery.cancel(self.order.id,self.grant('delivery.cancel'),'Cliente não encontrado','cancel')
        self.view.scope.set('Todos no período');self.view.apply_filters();self.view.tree.selection_set(str(self.order.id));form=self.view.returned()
        self.assertIsNotNone(form)
        form.tree.selection_set(str(self.pid));form.qty.insert(0,'100')
        with patch('salva_ai_v2.ui.delivery_actions.messagebox.askyesno',return_value=True),patch.object(self.view,'grant',side_effect=self.grant),patch.object(self.view,'reason',return_value='Retorno conferido'):
            self.assertFalse(form.submit())
        self.assertEqual(form.qty.get(),'100');self.assertTrue(form.winfo_exists())
        form.qty.delete(0,'end');form.qty.insert(0,'2')
        with patch('salva_ai_v2.ui.delivery_actions.messagebox.askyesno',return_value=True),patch.object(self.view,'grant',side_effect=self.grant),patch.object(self.view,'reason',return_value='Retorno conferido'),patch.object(self.s.delivery,'confirm_return',side_effect=OSError('Disco cheio')):
            self.assertFalse(form.submit())
        self.assertEqual(form.qty.get(),'2');form.winfo_toplevel().destroy()

    def test_delivery_details_include_complement(self):
        with patch('salva_ai_v2.ui.delivery.messagebox.showinfo'):details=self.view.details()
        self.assertIsNotNone(details)
        self.assertIn('Apartamento 202',details.facts.get('1.0','end'))
        details.winfo_toplevel().destroy()

    def test_refund_declined_summary_preserves_form_and_money(self):
        from salva_ai_v2.ui.forms import FormDialog
        self.s.delivery.record_payment(self.order.id,'MONEY',1500,'BAR',1500,'receipt')
        self.s.delivery.cancel(self.order.id,self.grant('delivery.cancel'),'Cliente desistiu','cancel')
        self.view.refresh();self.view.tree.selection_set(str(self.order.id));dialogs=[]
        with patch('salva_ai_v2.ui.delivery.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):self.view.refund()
        form=dialogs[0];before='\n'.join(self.app.db.conn.iterdump())
        with patch('salva_ai_v2.ui.delivery_actions.messagebox.askyesno',return_value=False),patch.object(self.view,'grant') as grant,patch.object(self.view,'reason',return_value='Teste de reembolso'):
            self.assertFalse(form.submit());grant.assert_not_called()
        self.assertEqual(before,'\n'.join(self.app.db.conn.iterdump()))
        self.assertEqual(form.inputs['amount'].get(),'15,00');form.destroy()
