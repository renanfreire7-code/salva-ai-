import importlib
import sqlite3
import tempfile
import unittest
from pathlib import Path


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'novo.sqlite3'
        self.Database = importlib.import_module('salva_ai_v2.common.db').Database
        self.db = self.Database(self.path)
        self.addCleanup(lambda: self.db.close())
        self.db.migrate()

    def test_replay_survives_restart(self):
        from salva_ai_v2.common.commands import CommandBus
        from salva_ai_v2.common.audit import Audit
        bus = CommandBus(self.db)
        def insert():
            Audit(self.db).record('test', '1', {}, {'value': 7}, None)
            return {'value': 7}
        first = bus.execute('one', 'test', {'value': 7}, insert)
        self.db.close()
        self.db = self.Database(self.path)
        result = CommandBus(self.db).execute('one', 'test', {'value': 7}, lambda: self.fail('Reexecutou'))
        self.assertEqual(first, result)
        self.assertEqual(self.db.conn.execute('SELECT count(*) FROM audit_events').fetchone()[0], 1)

    def test_conflicting_payload(self):
        from salva_ai_v2.common.commands import CommandBus
        from salva_ai_v2.common.errors import ConflictError
        bus = CommandBus(self.db)
        bus.execute('one', 'test', {'a': 1}, lambda: {})
        with self.assertRaises(ConflictError):
            bus.execute('one', 'test', {'a': 2}, lambda: {})

    def test_rollback_includes_audit_and_command(self):
        from salva_ai_v2.common.commands import CommandBus
        from salva_ai_v2.common.audit import Audit
        def broken():
            Audit(self.db).record('test', '1', {}, {}, None)
            raise ValueError('falha simulada')
        with self.assertRaises(ValueError):
            CommandBus(self.db).execute('bad', 'test', {}, broken)
        for table in ('audit_events', 'command_results'):
            self.assertEqual(self.db.conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 0)

    def test_migration_repeat_and_foreign_keys(self):
        before = self.db.conn.execute('SELECT count(*) FROM schema_migrations').fetchone()[0]
        self.db.migrate()
        self.assertEqual(self.db.conn.execute('PRAGMA foreign_keys').fetchone()[0], 1)
        self.assertEqual(self.db.conn.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], before)

    def test_legacy_is_rejected_without_write(self):
        from salva_ai_v2.common.errors import BusinessError
        other = self.path.parent / 'antigo.sqlite3'
        c = sqlite3.connect(other)
        c.execute('CREATE TABLE products(id INTEGER PRIMARY KEY)')
        c.close()
        original = other.read_bytes()
        with self.assertRaises(BusinessError):
            self.Database(other).migrate()
        self.assertEqual(other.read_bytes(), original)

    def test_money_conserves_cents(self):
        from salva_ai_v2.common.money import round_half_up, allocate
        self.assertEqual(round_half_up(1, 2), 1)
        self.assertEqual(round_half_up(-1, 2), -1)
        self.assertEqual(allocate(1, {1: 1, 2: 1, 3: 1}), {1: 1, 2: 0, 3: 0})
        self.assertEqual(sum(allocate(100, {1: 3, 2: 7}).values()), 100)

    def test_invalid_destination_does_not_fallback(self):
        from salva_ai_v2.common.errors import BusinessError
        blocked=self.path.parent/'nao_e_pasta'
        blocked.write_text('arquivo, não diretório')
        with self.assertRaises(BusinessError):
            self.Database(blocked/'db.sqlite3')
