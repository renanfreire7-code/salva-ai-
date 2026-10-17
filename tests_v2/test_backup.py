from pathlib import Path
from tests_v2.support import DatabaseCase


class BackupTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.maintenance.backup import BackupService
        self.backups = BackupService(self.db, self.root/'backups')

    def test_consistent_backup_and_repeat(self):
        info = self.backups.create('manual', 'backup1')
        self.assertTrue(info.integrity_ok)
        self.assertEqual(info.path, self.backups.create('manual', 'backup1').path)
        self.assertEqual(self.backups.verify(info.path).schema_version, info.schema_version)

    def test_corrupt_foreign_or_future_database_rejected(self):
        import sqlite3
        from salva_ai_v2.common.errors import BusinessError
        bad=self.root/'bad.sqlite3';bad.write_bytes(b'not a database')
        with self.assertRaises(BusinessError):
            self.backups.verify(bad)
        foreign=self.root/'foreign.sqlite3'
        c=sqlite3.connect(foreign);c.execute('CREATE TABLE unrelated(x)');c.close()
        with self.assertRaises(BusinessError):
            self.backups.verify(foreign)
        info=self.backups.create('manual','backup1')
        c=sqlite3.connect(info.path)
        c.execute("INSERT INTO schema_migrations VALUES('999_future.sql','future')");c.commit();c.close()
        with self.assertRaises(BusinessError):
            self.backups.verify(info.path)

    def test_missing_external_directory_reports_failure(self):
        self.backups.external_dir=self.root/'pendrive_ausente'
        info=self.backups.create('manual','backup1')
        self.assertTrue(info.integrity_ok)
        self.assertFalse(info.external_copy_ok)

    def test_same_directory_is_not_an_additional_copy(self):
        self.backups.external_dir=self.root/'backups'
        self.assertFalse(self.backups.create('manual','backup1').external_copy_ok)
