from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from tests_v2.application_support import build_test_application
from salva_ai_v2.common.commands import CommandBus
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.inventory.models import CartLine, PurchaseLine


class FinalReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=build_test_application(Path(self.tmp.name));self.addCleanup(self.app.close)

    def restore_preview(self):
        s=self.app.services
        backup=s.backups.create('manual','backup').path
        grant=self.app.security.authorize('681','backup.restore')
        return s.restore,s.restore.prepare(backup,grant)

    def test_restore_log_failure_relocks_before_returning_error(self):
        restore,preview=self.restore_preview();execute=CommandBus.execute
        def fail_completed(bus,command_id,kind,*args,**kwargs):
            if kind=='restore.completed':raise sqlite3.OperationalError('Disco indisponível')
            return execute(bus,command_id,kind,*args,**kwargs)
        with patch.object(CommandBus,'execute',fail_completed):
            with self.assertRaises(sqlite3.OperationalError):restore.apply(preview,True)
        self.assertFalse(self.app.authenticated)
        self.assertEqual(self.app.views,[])
        self.assertFalse(hasattr(self.app,'services'))
        self.assertEqual(self.app.security._grants,{})

    def test_restore_failure_and_broken_access_screen_close_application(self):
        restore,preview=self.restore_preview()
        with patch.object(restore,'_reopen',side_effect=sqlite3.OperationalError('Migração falhou')),patch('salva_ai_v2.ui.access.AccessView',side_effect=RuntimeError('Entrada indisponível')):
            with self.assertRaises((sqlite3.OperationalError,RuntimeError)):restore.apply(preview,True)
        self.assertFalse(self.app.authenticated)
        self.assertIsNone(self.app.db.conn)
        self.assertTrue(self.app._closed)

    def test_legacy_redelivery_summary_matches_immediate_dispatch(self):
        from salva_ai_v2.ui.delivery_actions import action_summary
        s=self.app.services
        p=s.inventory.create_product('Cerveja',500,1,0,'product')
        s.inventory.receive_purchase([PurchaseLine(p,10,2000)],0,s.clock.today(),s.clock.today(),'purchase')
        s.cash.open(10000,'cash');s.delivery.configure_fees(500,700,'fees')
        old=s.delivery.confirm(DeliveryDraft('Cliente','123','Rua','',[CartLine(p,1)],'MONEY','BAR'),'order')
        s.delivery.cancel(old.id,s.security.authorize('681','delivery.cancel'),'Cliente ausente','cancel')
        text=action_summary(s.delivery_queries.detail(old.id),'REDELIVER')
        self.assertIn('sai imediatamente',text)
        self.assertIn('corrida',text)
        self.assertNotIn('somente ao sair',text)
        new=s.delivery.redeliver(old.id,s.security.authorize('681','delivery.redeliver'),'Novo envio combinado','retry')
        new_order=self.app.db.conn.execute('SELECT order_id FROM delivery_orders WHERE previous_order_id=?',(old.id,)).fetchone()[0]
        self.assertEqual(s.delivery.order(new_order).state,'OUT')
        self.assertEqual(self.app.db.conn.execute('SELECT fee_cents FROM trips WHERE id=?',(new,)).fetchone()[0],700)

    def test_long_confirmation_scrolls_and_keeps_actions_visible(self):
        from salva_ai_v2.ui.delivery_actions import ActionConfirmation
        dialog=ActionConfirmation(self.app.window,'Conferir operação','\n'.join(f'{n}: '+('Produto completo '*30) for n in range(40)))
        self.app.window.update()
        self.assertLessEqual(dialog.winfo_height(),self.app.window.winfo_screenheight())
        self.assertTrue(dialog.scrollbar.winfo_ismapped())
        self.assertLess(dialog.content.yview()[1],1)
        dialog.content.yview_moveto(1);self.app.window.update()
        self.assertEqual(dialog.content.yview()[1],1)
        self.assertLess(dialog.confirm_button.winfo_rooty()+dialog.confirm_button.winfo_height(),self.app.window.winfo_screenheight())
        dialog.cancel();self.assertFalse(dialog.result)
        dialog=ActionConfirmation(self.app.window,'Conferir operação','Texto completo')
        dialog.confirm();self.assertTrue(dialog.result)
