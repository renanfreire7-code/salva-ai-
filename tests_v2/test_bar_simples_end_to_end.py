from pathlib import Path
from dataclasses import replace
import tempfile,unittest
from unittest.mock import patch
from tests_v2.test_access_end_to_end import seed_previous_store
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.inventory.models import CartLine
from salva_ai_v2.sales.models import Payment


class BarSimplesEndToEndTest(unittest.TestCase):
    def test_v02_to_bar_simples_complete_operation_and_restore(self):
        with tempfile.TemporaryDirectory(prefix='Bar Simples ensaio com acentuação ') as folder:
            root=Path(folder);old=seed_previous_store(root);app=build_application(root)
            try:
                self.assertTrue(app.authenticated);self.assertFalse(hasattr(app,'access_view'))
                s=app.services;pid=old['pid']
                grant=lambda action:s.security.authorize('681942',action)
                s.pricing.set_promotion(pid,3,1200,True,'promo');s.inventory.assign_shortcut(1,pid,'shortcut')
                def pay(dialog):
                    dialog.inputs['method'].set('Pix');dialog.update_method()
                    with patch('salva_ai_v2.ui.payment.messagebox.askyesno',return_value=True):self.assertTrue(dialog.submit())
                    return dialog.result
                view=app.sales_view;view.search.set('hei');view.filter_products();view.choose_product();view.qty.delete(0,'end');view.qty.insert(0,'3');view.add_and_focus()
                with patch('salva_ai_v2.ui.payment.PaymentDialog.show',pay):view.checkout()
                self.assertEqual(view.total_cents,0)
                tab=s.sales.create_tab('Cliente comanda','tab');app.tabs_view.refresh();app.tabs_view.tabs_tree.selection_set(str(tab))
                view=app.tabs_view;view.search.set('hei');view.filter_products();view.choose_product();view.qty.delete(0,'end');view.qty.insert(0,'1');view.add_and_focus()
                with patch('salva_ai_v2.ui.payment.PaymentDialog.show',pay):view.checkout()
                self.assertEqual(s.sales.open_tabs(),[])
                s.delivery.configure_fees(500,700,'fees')
                prepaid=DeliveryDraft('Cliente Pix','11','Rua A','Farmácia',[CartLine(pid,1)],'PIX','BAR','ADVANCE','PIX',None,'','Apto 202')
                first=s.delivery.confirm(prepaid,'advance');s.delivery.record_payment(first.id,'PIX',1000,'BAR',None,'advance-receipt')
                trip1=s.delivery.dispatch(first.id,'advance-out');s.delivery.mark_delivered(first.id,'advance-delivered')
                cash=replace(prepaid,customer='Cliente dinheiro',lines=[CartLine(pid,3)],payment_method='MONEY',collection='COURIER',payment_timing='ON_DELIVERY',payment_channel='MONEY',change_for_cents=2000)
                second=s.delivery.confirm(cash,'cash');fund=s.settlements.fund_courier(300,grant('delivery.float'),'Troco para pedido','fund')
                trip2=s.delivery.dispatch(second.id,'cash-out');receipt=s.delivery.record_payment(second.id,'MONEY',1700,'COURIER',2000,'cash-receipt');s.delivery.mark_delivered(second.id,'cash-delivered')
                s.settlements.settle([receipt],[trip2],1000,0,700,grant('delivery.settle'),'settle-money')
                s.settlements.return_float(fund,300,'return-float');s.settlements.settle([],[trip1],0,700,0,grant('delivery.settle'),'settle-digital')
                self.assertEqual(s.settlements.pending_custody_cents(),0);self.assertEqual(s.cash.position(old['session']).expected_cents,10300)
                self.assertEqual(s.inventory.position(pid).physical,11)
                self.assertEqual(s.delivery_queries.detail(second.id)['order']['complement'],'Apto 202')
                closing=s.closing.begin(10300,None,None,'close');self.assertTrue(closing.complete)
                backup=closing.backup_path
                app.close();app=build_application(root);self.assertTrue(app.authenticated);s=app.services
                self.assertEqual(s.delivery.confirm(cash,'cash'),second)
                oldcart=app.db.conn.execute('SELECT order_id FROM sales WHERE id=?',(old['sale'],)).fetchone()[0]
                self.assertEqual(s.sales.sell(oldcart,Payment('PIX'),'sale').id,old['sale'])
                preview=s.restore.prepare(backup,s.security.authorize('681942','backup.restore'));s.restore.apply(preview,True)
                self.assertTrue(app.authenticated)
                self.assertEqual(app.services.inventory.position(pid).physical,11)
            finally:app.close()
