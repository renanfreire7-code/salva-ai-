from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class MigrationTest(unittest.TestCase):
    def test_failed_migration_rolls_back_schema_and_keeps_backup(self):
        from salva_ai_v2.common.db import Database,APPLICATION_ID
        from salva_ai_v2.maintenance.backup import BackupService
        import hashlib
        class FailingConnection(sqlite3.Connection):
            def execute(self,sql,*args,**kwargs):
                if sql.lstrip().startswith('CREATE TABLE products'):
                    raise sqlite3.OperationalError('falha simulada na atualização')
                return super().execute(sql,*args,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'old_v2.sqlite3'
            conn=sqlite3.connect(path)
            sql=Path('salva_ai_v2/migrations/001_foundation.sql').read_text()
            conn.executescript(sql)
            conn.execute(f'PRAGMA application_id={APPLICATION_ID}')
            conn.execute('INSERT INTO schema_migrations VALUES(?,?)',('001_foundation.sql',hashlib.sha256(sql.encode()).hexdigest()))
            conn.commit();conn.close()
            db=Database(path);db.close()
            db.conn=sqlite3.connect(path,isolation_level=None,factory=FailingConnection)
            db.conn.row_factory=sqlite3.Row
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    db.upgrade(BackupService(db,root/'backups'))
                self.assertEqual(db.conn.execute('SELECT count(*) FROM schema_migrations').fetchone()[0],1)
                self.assertIsNone(db.conn.execute("SELECT 1 FROM sqlite_master WHERE name='admin_credentials'").fetchone())
                self.assertEqual(len(list((root/'backups').glob('antes_atualizacao_*.sqlite3'))),1)
            finally:
                db.close()

    def test_upgrade_backs_up_before_applying_and_repeats(self):
        from salva_ai_v2.common.db import Database,APPLICATION_ID
        from salva_ai_v2.maintenance.backup import BackupService
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'old_v2.sqlite3'
            conn=sqlite3.connect(path)
            import hashlib
            sql=Path('salva_ai_v2/migrations/001_foundation.sql').read_text()
            conn.executescript(sql)
            conn.execute(f'PRAGMA application_id={APPLICATION_ID}')
            conn.execute('INSERT INTO schema_migrations VALUES(?,?)',('001_foundation.sql',hashlib.sha256(sql.encode()).hexdigest()))
            conn.commit();conn.close()
            db=Database(path)
            try:
                backups=BackupService(db,root/'backups')
                db.upgrade(backups)
                self.assertEqual(len(list((root/'backups').glob('antes_atualizacao_*.sqlite3'))),1)
                db.upgrade(backups)
                self.assertEqual(len(list((root/'backups').glob('antes_atualizacao_*.sqlite3'))),1)
                self.assertTrue(db.conn.execute("SELECT 1 FROM sqlite_master WHERE name='products'").fetchone())
            finally:
                db.close()
