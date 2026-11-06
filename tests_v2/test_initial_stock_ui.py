import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests_v2.application_support import build_test_application
from salva_ai_v2.ui.forms import FormDialog


class InitialStockUITest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.app=build_test_application(Path(tmp.name));self.addCleanup(self.app.close)
        self.view=self.app.products_view

    def dialog(self,callback):
        dialogs=[]
        with patch('salva_ai_v2.ui.products.ask_fields',side_effect=lambda *a,**kw:dialogs.append(FormDialog(*a,**kw))):callback()
        return dialogs[0]

    def fill(self,dialog,**values):
        for key,value in values.items():
            dialog.inputs[key].delete(0,'end');dialog.inputs[key].insert(0,str(value))

    def save(self,dialog):
        with patch.object(self.app.admin,'request',side_effect=lambda action:self.app.security.authorize('681',action)):
            return dialog.submit()

    def test_existing_product_receives_initial_stock_and_shows_totals(self):
        pid=self.app.services.inventory.create_product('Heineken',800,12,0,'p')
        self.view.refresh();self.view.tree.selection_set(str(pid))
        d=self.dialog(self.view.initial_stock);self.fill(d,qty=24,unit_cost='4,50')
        self.assertTrue(self.save(d));self.app.refresh()
        self.assertEqual(len(self.app.services.inventory.products()),1)
        self.assertIn('R$ 108,00',str(self.view.tree.item(str(pid),'values')))
        self.assertIn('Inicial registrado: R$ 108,00',self.view.stock_summary.get())
        self.assertIn('Valor atual: R$ 108,00',self.view.stock_summary.get())

    def test_new_product_with_cost_validation_and_atomic_creation(self):
        d=self.dialog(self.view.create);self.fill(d,name='Água',price='3,00',initial_qty=30,initial_cost='0,00')
        self.assertFalse(self.save(d));self.assertEqual(self.app.services.inventory.products(),[])
        self.assertTrue(d.winfo_exists());self.assertEqual(d.inputs['name'].get(),'Água')
        self.fill(d,initial_cost='1,20');self.assertTrue(self.save(d))
        self.assertEqual(self.app.services.inventory.stock_totals()['initial_value_cents'],3600)

    def test_zero_initial_stock_and_cancel_do_not_require_pin_or_add_stock(self):
        d=self.dialog(self.view.create);self.fill(d,name='Sem saldo',price='5,00')
        with patch.object(self.app.admin,'request',side_effect=AssertionError('Não deveria pedir PIN')):
            self.assertTrue(d.submit())
        pid=self.app.services.inventory.products()[0]['id'];self.view.refresh();self.view.tree.selection_set(str(pid))
        d=self.dialog(self.view.initial_stock);self.fill(d,qty=3,unit_cost='2,00');d.destroy()
        self.assertEqual(self.app.services.inventory.position(pid).physical,0)

    def test_form_and_actions_fit_notebook_resolution(self):
        from tkinter import ttk
        self.app.window.geometry('1366x768');self.app.show_view(self.view)
        d=self.dialog(self.view.create);self.app.window.update()
        self.assertLessEqual(d.winfo_height(),768)
        self.assertLessEqual(d.save_button.winfo_rooty()+d.save_button.winfo_height(),d.winfo_rooty()+d.winfo_height())
        self.assertIn('initial_qty',d.inputs);self.assertIn('initial_cost',d.inputs)
        for frame in self.view.winfo_children():
            for widget in frame.winfo_children():
                if isinstance(widget,ttk.Button) and widget.winfo_ismapped():
                    self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.app.window.winfo_rootx()+self.app.window.winfo_width())
        d.destroy()

    def test_update_from_043_preserves_existing_database_and_initializes_only_empty_product(self):
        import zipfile,subprocess,sys,sqlite3
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'old';data=root/'dados existentes'
            with zipfile.ZipFile(Path(__file__).resolve().parents[1]/'dist/Bar_Simples_0.4.3-dev_sem_login.zip') as archive:
                archive.extractall(old)
            code='''from pathlib import Path
import sys
from salva_ai_v2 import __version__
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.inventory.models import PurchaseLine
assert __version__ == '0.4.3-dev'
a=build_application(Path(sys.argv[1]))
a.security.setup('681')
s=a.services
p=s.inventory.create_product('Já comprado',800,12,0,'p')
s.inventory.receive_purchase([PurchaseLine(p,10,3000)],0,s.clock.today(),s.clock.today(),'buy')
s.inventory.create_product('Falta iniciar',500,1,0,'empty')
s.cash.open(5000,'cash')
a.close()
'''
            result=subprocess.run([sys.executable,'-c',code,str(data)],cwd=old,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            dbfile=data/'dados'/'salva_ai.sqlite3'
            with sqlite3.connect(dbfile) as db:
                names=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                before={n:db.execute(f'SELECT * FROM "{n}"').fetchall() for n in names}
            from salva_ai_v2.bootstrap import build_application
            app=build_application(data)
            try:
                after={n:[tuple(r) for r in app.db.conn.execute(f'SELECT * FROM "{n}"')] for n in names}
                self.assertEqual(before,after)
                empty=next(p['id'] for p in app.services.inventory.products() if p['name']=='Falta iniciar')
                app.services.inventory.initialize_stock(empty,3,200,app.security.authorize('681','stock.adjust'),'initial')
                self.assertEqual(app.services.inventory.stock_totals()['current_value_cents'],3600)
                self.assertEqual(app.services.cash.position(app.services.cash.active()['id']).expected_cents,5000)
                self.assertEqual(app.db.conn.execute('SELECT count(*) FROM obligations').fetchone()[0],1)
            finally:app.close()
