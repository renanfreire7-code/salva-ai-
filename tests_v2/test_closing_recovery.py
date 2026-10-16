from pathlib import Path
from unittest.mock import patch
from tests_v2.delivery_support import DeliveryCase


class ClosingRecoveryTest(DeliveryCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/cash/closing.py').exists(), 'Fechamento ainda não implementado')
        from salva_ai_v2.maintenance.backup import BackupService
        from salva_ai_v2.cash.closing import ClosingService
        from salva_ai_v2.reporting.queries import ReportingQueries
        self.backups=BackupService(self.db,self.root/'backups')
        self.closing=ClosingService(self.db,self.cash,self.backups,ReportingQueries(self.db))

    def test_failure_after_closed_resumes_without_duplicate(self):
        from salva_ai_v2.common.errors import BusinessError
        with patch.object(self.backups,'create',side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):
                self.closing.begin(10000,None,None,'close1')
        self.assertTrue(self.cash.blockers(self.session))
        with self.assertRaises(BusinessError):
            self.cash.open(0,'open2')
        result=self.closing.resume(self.session)
        self.assertTrue(result.complete)
        self.assertTrue(self.backups.verify(result.backup_path).integrity_ok)
        self.assertEqual(self.scalar("SELECT count(*) FROM audit_events WHERE kind='cash.closed'"),1)
        self.assertEqual(self.closing.begin(10000,None,None,'close1'),result)

    def test_failure_after_backup_and_report_resumes(self):
        with patch.object(self.closing,'_finish',side_effect=OSError('interrompido')):
            with self.assertRaises(OSError):
                self.closing.begin(10000,None,None,'close1')
        result=self.closing.resume(self.session)
        self.assertTrue(result.report_path.is_file())
        self.assertTrue(result.backup_path.is_file())

    def test_variance_and_open_order_block(self):
        from salva_ai_v2.common.errors import BusinessError
        with self.assertRaises(BusinessError):
            self.closing.begin(9900,None,'Falta de dinheiro','bad1')
        order=self.delivery.confirm(self.draft(),'order1')
        with self.assertRaises(BusinessError):
            self.closing.begin(10000,None,None,'bad2')
        self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cliente desistiu','cancel1')
        result=self.closing.begin(9900,self.grant('cash.close'),'Falta de dinheiro','close1')
        self.assertIn('Falta de dinheiro',result.report_path.read_text())
