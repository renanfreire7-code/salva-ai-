from pathlib import Path
from unittest.mock import patch
from tests_v2.delivery_support import DeliveryCase


class RestoreTest(DeliveryCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(Path('salva_ai_v2/maintenance/restore.py').exists(), 'Restauração ainda não implementada')
        from salva_ai_v2.maintenance.backup import BackupService
        from salva_ai_v2.maintenance.restore import RestoreService
        self.backups=BackupService(self.db,self.root/'backups')
        self.restore=RestoreService(self.root,self.backups,self.security)
        self.source=self.backups.create('manual','backup1').path

    def test_restore_preserves_current_and_loads_snapshot(self):
        self.inventory.create_product('Produto posterior',1000,1,0,'new1')
        preview=self.restore.prepare(self.source,self.grant('backup.restore'))
        self.restore.apply(preview,True)
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),1)
        preserved=list((self.root/'backups').glob('antes_restauracao_*.sqlite3'))
        self.assertEqual(len(preserved),1)
        self.assertTrue(self.backups.verify(preserved[0]).integrity_ok)

    def test_source_changed_after_preview_rejected(self):
        from salva_ai_v2.common.errors import BusinessError
        preview=self.restore.prepare(self.source,self.grant('backup.restore'))
        self.source.write_bytes(b'arquivo trocado')
        with self.assertRaises(BusinessError):
            self.restore.apply(preview,True)
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),1)

    def test_cancel_and_same_file_do_not_replace(self):
        from salva_ai_v2.common.errors import BusinessError
        preview=self.restore.prepare(self.source,self.grant('backup.restore'))
        before=self.db.path.read_bytes()
        self.restore.apply(preview,False)
        self.assertEqual(self.db.path.read_bytes(),before)
        with self.assertRaises(BusinessError):
            self.restore.prepare(self.db.path,self.grant('backup.restore'))

    def test_replace_failure_keeps_database_recoverable(self):
        preview=self.restore.prepare(self.source,self.grant('backup.restore'))
        with patch('salva_ai_v2.maintenance.restore.promote',side_effect=OSError('disco bloqueado')):
            with self.assertRaises(OSError):
                self.restore.apply(preview,True)
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),1)
        self.assertTrue(list((self.root/'backups').glob('antes_restauracao_*.sqlite3')))
