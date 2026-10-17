import hashlib,sqlite3
from pathlib import Path
from tests_v2.support import DatabaseCase
from tests_v2.security_support import seed_legacy_pin
from salva_ai_v2.security.service import SecurityService
from salva_ai_v2.common.errors import BusinessError
from salva_ai_v2.common.db import Database,APPLICATION_ID
from salva_ai_v2.maintenance.backup import BackupService


class AccessUpgradeTest(DatabaseCase):
    def test_new_pin_requires_three_ascii_digits(self):
        security=SecurityService(self.db)
        for invalid in ('07','0007','１２３','681942'):
            with self.subTest(pin=invalid),self.assertRaises(BusinessError):security.setup(invalid)
        security.setup('007');self.assertEqual(security.pin_length,3)
        self.assertEqual(security.authorize('007','test').action,'test')

    def test_previous_schema_migration_preserves_six_digit_hash_and_backup(self):
        path=self.root/'anterior.sqlite3';conn=sqlite3.connect(path)
        for migration in sorted(Path('salva_ai_v2/migrations').glob('*.sql')):
            if migration.name>'014_service_experience.sql':continue
            sql=migration.read_text();conn.executescript(sql)
            conn.execute('INSERT INTO schema_migrations VALUES(?,?)',(migration.name,hashlib.sha256(sql.encode()).hexdigest()))
        conn.execute(f'PRAGMA application_id={APPLICATION_ID}');conn.commit();conn.close()
        old=Database(path,self.clock)
        try:
            seed_legacy_pin(old);original=old.conn.execute('SELECT pin_hash FROM admin_credentials').fetchone()[0]
            old.conn.execute("INSERT INTO products(id,name,price_cents,pack_size,min_stock,stock,value_cents) VALUES(42,'Existente',500,1,0,8,1600)")
            backup=BackupService(old,self.root/'backups');old.upgrade(backup)
            security=SecurityService(old);self.assertEqual(security.pin_length,6)
            self.assertEqual(security.authorize('681942','test').action,'test')
            with self.assertRaises(BusinessError):security.authorize('681','test')
            self.assertEqual(old.conn.execute('SELECT pin_hash FROM admin_credentials').fetchone()[0],original)
            self.assertEqual(tuple(old.conn.execute('SELECT id,stock,value_cents FROM products').fetchone()),(42,8,1600))
            backups=backup.list_backups();self.assertEqual(len(backups),1);self.assertTrue(backup.verify(backups[0]).integrity_ok)
        finally:old.close()
