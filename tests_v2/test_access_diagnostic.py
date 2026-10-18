import hashlib
from pathlib import Path
import sqlite3
from tests_v2.support import DatabaseCase
from salva_ai_v2.security.service import SecurityService


class AccessDiagnosticTest(DatabaseCase):
    def setup_files(self):
        from scripts.diagnose_access import diagnose
        self.diagnose=diagnose
        self.data=self.root/'estabelecimento'
        (self.data/'dados').mkdir(parents=True)
        self.target=self.data/'dados'/'salva_ai.sqlite3'
        self.key=SecurityService(self.db,self.clock).setup('007')
        with sqlite3.connect(self.target) as destination:self.db.conn.backup(destination)

    def test_diagnoses_copy_whitespace_without_altering_credentials(self):
        self.setup_files()
        original=hashlib.sha256(self.target.read_bytes()).digest()
        self.assertEqual(self.diagnose(self.data,self.key)['active']['match'],'EXACT')
        self.assertEqual(self.diagnose(self.data,' '+self.key+'\n')['active']['match'],'OUTER_WHITESPACE')
        wrapped=self.key[:20]+'\n'+self.key[20:]
        self.assertEqual(self.diagnose(self.data,wrapped)['active']['match'],'INNER_WHITESPACE')
        self.assertEqual(original,hashlib.sha256(self.target.read_bytes()).digest())
        report=repr(self.diagnose(self.data,self.key))
        self.assertNotIn(self.key,report)
        row=self.db.conn.execute('SELECT recovery_hash,recovery_salt FROM admin_credentials').fetchone()
        for secret in row:self.assertNotIn(repr(secret),report)

    def test_distinguishes_key_matching_backup_after_recovery(self):
        self.setup_files()
        backups=self.data/'backups';backups.mkdir()
        (backups/'anterior.sqlite3').write_bytes(self.target.read_bytes())
        with sqlite3.connect(self.target) as destination:
            self.db.conn.backup(destination)
        from salva_ai_v2.common.db import Database
        active=Database(self.target,self.clock)
        try:newkey=SecurityService(active,self.clock).recover(self.key,'009')
        finally:active.close()
        report=self.diagnose(self.data,self.key)
        self.assertEqual(report['active']['match'],'NO_MATCH')
        self.assertEqual(report['active']['recoveries'],1)
        self.assertEqual(report['backup_matches'],1)
        self.assertEqual(self.diagnose(self.data,newkey)['active']['match'],'EXACT')

    def test_missing_or_other_database_is_not_created_or_changed(self):
        self.setup_files()
        missing=self.root/'ausente'
        self.assertEqual(self.diagnose(missing,self.key)['active']['match'],'MISSING')
        self.assertFalse(missing.exists())
        with sqlite3.connect(self.target) as conn:
            conn.execute('PRAGMA application_id=123')
        original=self.target.read_bytes()
        self.assertEqual(self.diagnose(self.data,self.key)['active']['match'],'OTHER_DATABASE')
        self.assertEqual(original,self.target.read_bytes())

    def test_bad_key_or_corrupt_file_gives_safe_report(self):
        self.setup_files()
        report=self.diagnose(self.data,'chave fictícia incorreta')
        self.assertEqual(report['active']['match'],'NO_MATCH')
        self.assertNotIn('chave fictícia incorreta',repr(report))
        self.target.write_bytes(b'arquivo que nao e SQLite')
        self.assertEqual(self.diagnose(self.data,self.key)['active']['match'],'READ_ERROR')
