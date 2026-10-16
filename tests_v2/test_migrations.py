from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class MigrationTest(unittest.TestCase):
    def test_upgrade_backs_up_before_applying_and_repeats(self):
        from salva_ai_v2.common.db import Database,APPLICATION_ID
        self.assertTrue(hasattr(Database,'upgrade'), 'Atualização protegida ainda não implementada')
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
