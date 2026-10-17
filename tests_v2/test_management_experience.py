from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ManagementExperienceTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)
        self.app.security.setup('681')

    def test_finance_filters_apply_only_when_requested_and_clear_resets(self):
        from salva_ai_v2.finance.models import ExpenseDraft
        s=self.app.services;today=s.clock.today()
        id=s.finance.add_expense(ExpenseDraft('Conta teste','Energia',2000,today,today),False,'expense')
        view=self.app.finance_view;self.app.refresh()
        view.text.set('Inexistente');view.refresh()
        self.assertIn(str(id),view.tree.get_children())
        view.period.apply();self.assertNotIn(str(id),view.tree.get_children())
        view.period.clear();self.assertIn(str(id),view.tree.get_children())
        self.assertEqual(view.filters().date_basis,'incurred')
        previous=view.tree.get_children();view.period.start.set('99/99/9999')
        self.assertFalse(view.period.apply());self.assertEqual(view.tree.get_children(),previous)

    def test_active_delivery_from_yesterday_remains_visible(self):
        from salva_ai_v2.inventory.models import PurchaseLine,CartLine
        from salva_ai_v2.delivery.models import DeliveryDraft
        s=self.app.services;pid=s.inventory.create_product('Produto',500,1,0,'p')
        s.inventory.receive_purchase([PurchaseLine(pid,5,1000)],0,s.clock.today(),s.clock.today(),'buy');s.cash.open(10000,'open')
        yesterday=s.clock.now()-timedelta(days=1)
        with patch.object(s.clock,'now',return_value=yesterday):
            order=s.delivery.confirm(DeliveryDraft('Ontem','123','Rua','',[CartLine(pid,1)],'PIX','BAR','ADVANCE','PIX'),'order')
        view=self.app.delivery_view;view.refresh()
        self.assertIn(str(order.id),view.tree.get_children())
        view.payment_filter.set('Pago');view.apply_filters()
        self.assertNotIn(str(order.id),view.tree.get_children())
        view.clear_filters();self.assertIn(str(order.id),view.tree.get_children())

    def test_expense_validation_keeps_form_and_creates_only_once(self):
        from salva_ai_v2.ui.forms import FormDialog
        dialogs=[];view=self.app.finance_view
        with patch('salva_ai_v2.ui.finance.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.create()
        dialog=dialogs[0]
        dialog.inputs['description'].insert(0,'Conta nova')
        dialog.inputs['amount'].delete(0,'end');dialog.inputs['amount'].insert(0,'errado')
        self.assertFalse(dialog.submit());self.assertEqual(dialog.inputs['description'].get(),'Conta nova')
        dialog.inputs['amount'].delete(0,'end');dialog.inputs['amount'].insert(0,'10,00')
        self.assertTrue(dialog.submit())
        self.assertEqual(self.app.db.conn.execute("SELECT count(*) FROM obligations WHERE description='Conta nova'").fetchone()[0],1)

    def test_supplier_credit_payment_history_uses_human_label(self):
        from salva_ai_v2.inventory.models import PurchaseLine,CartLine
        s=self.app.services;pid=s.inventory.create_product('Produto',500,1,0,'p')
        purchase=s.inventory.receive_purchase([PurchaseLine(pid,5,1000)],0,s.clock.today(),s.clock.today(),'buy')
        credit=s.inventory.return_to_supplier(purchase,[CartLine(pid,1)],s.security.authorize('681','purchase.return'),'Retorno conferido','return')
        s.inventory.settle_supplier_credit(credit,200,'OFFSET',None,False,s.clock.today(),s.security.authorize('681','purchase.credit.settle'),'Crédito abatido','offset')
        view=self.app.finance_view;view.refresh();view.tree.selection_set('1')
        payment_view=view.payments()
        self.assertIn('Crédito do fornecedor',str(payment_view.payments_tree.item('1','values')))
        payment_view.winfo_toplevel().destroy()

    def test_payment_selectors_keep_invalid_drawer_choice_for_correction(self):
        from tkinter import ttk
        from salva_ai_v2.ui.forms import FormDialog
        from salva_ai_v2.finance.models import ExpenseDraft
        s=self.app.services;today=s.clock.today()
        id=s.finance.add_expense(ExpenseDraft('Energia','Energia',500,today,today),False,'expense')
        view=self.app.finance_view;view.refresh();view.tree.selection_set(str(id));dialogs=[]
        with patch('salva_ai_v2.ui.finance.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.pay()
        dialog=dialogs[0]
        self.assertIsInstance(dialog.inputs['method'],ttk.Combobox)
        self.assertIsInstance(dialog.inputs['drawer'],ttk.Combobox)
        dialog.inputs['drawer'].set('Sim')
        with patch.object(view,'grant',side_effect=lambda action:s.security.authorize('681',action)):
            self.assertFalse(dialog.submit())
        self.assertTrue(dialog.winfo_exists());self.assertEqual(s.finance.paid_cents(id),0)
        dialog.inputs['drawer'].set('Não');self.assertTrue(dialog.submit())
        self.assertEqual(s.finance.paid_cents(id),500)

    def test_recurring_form_preserves_values_until_valid_and_generates_pending(self):
        from salva_ai_v2.ui.forms import FormDialog
        from tkinter import ttk
        recurring=self.app.finance_view.recurring()
        self.assertIsNotNone(recurring)
        dialogs=[]
        with patch('salva_ai_v2.ui.recurrence.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):recurring.create()
        dialog=dialogs[0]
        dialog.inputs['description'].insert(0,'Conta mensal')
        dialog.inputs['amount'].delete(0,'end');dialog.inputs['amount'].insert(0,'10,00')
        dialog.inputs['day'].delete(0,'end');dialog.inputs['day'].insert(0,'32')
        self.assertFalse(dialog.submit());self.assertEqual(dialog.inputs['description'].get(),'Conta mensal')
        dialog.inputs['day'].delete(0,'end');dialog.inputs['day'].insert(0,'31')
        self.assertTrue(dialog.submit())
        recurring.refresh();recurring.tree.selection_set('1')
        with patch('salva_ai_v2.ui.recurrence.messagebox.askyesno',return_value=True):recurring.generate()
        self.assertEqual(self.app.services.finance.paid_cents(1),0)
        self.assertEqual(self.app.db.conn.execute('SELECT count(*) FROM obligations').fetchone()[0],1)
        recurring.winfo_toplevel().destroy()

    def test_cash_header_displays_pending_closure_after_backup_failure(self):
        s=self.app.services;s.cash.open(10000,'open')
        with patch.object(s.backups,'create',side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):s.closing.begin(10000,None,None,'close')
        self.app.refresh()
        self.assertIn('pendente',self.app.window.cash_state.get().lower())

    def test_promotion_form_uses_real_yes_no_and_preserves_invalid_price(self):
        from tkinter import ttk
        from salva_ai_v2.ui.forms import FormDialog
        s=self.app.services;pid=s.inventory.create_product('Produto',500,1,0,'p');self.app.refresh()
        view=self.app.products_view;view.tree.selection_set(str(pid));dialogs=[]
        with patch('salva_ai_v2.ui.products.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.promotion()
        dialog=dialogs[0]
        self.assertIsInstance(dialog.inputs['active'],ttk.Combobox)
        dialog.inputs['price'].delete(0,'end');dialog.inputs['price'].insert(0,'20,00')
        self.assertFalse(dialog.submit());self.assertEqual(dialog.inputs['qty'].get(),'3')
        dialog.inputs['price'].delete(0,'end');dialog.inputs['price'].insert(0,'12,00');self.assertTrue(dialog.submit())
        self.assertEqual(s.pricing.snapshot(pid).group_cents,1200)

    def test_rate_configuration_preserves_values_and_saves_atomically(self):
        from salva_ai_v2.ui.forms import FormDialog
        s=self.app.services;view=self.app.results_view;dialogs=[]
        with patch('salva_ai_v2.ui.results.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):view.configure()
        dialog=dialogs[0];dialog.inputs['PIX'].insert(0,'inválido')
        self.assertFalse(dialog.submit());self.assertIsNone(s.settings.das())
        dialog.inputs['PIX'].delete(0,'end');dialog.inputs['PIX'].insert(0,'0')
        dialog.inputs['DEBIT'].insert(0,'1,50');dialog.inputs['CREDIT'].insert(0,'3,50');dialog.inputs['das'].insert(0,'80,00')
        with patch.object(view,'grant',side_effect=lambda action:s.security.authorize('681',action)),patch.object(view,'reason',return_value='Taxas confirmadas'):
            self.assertTrue(dialog.submit())
        self.assertEqual(s.settings.rates()['DEBIT'],150);self.assertEqual(s.settings.das(),8000)
