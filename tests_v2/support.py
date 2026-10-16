import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from salva_ai_v2.common.db import Database


class FakeClock:
    def __init__(self):
        self.value = datetime(2026, 10, 16, 12, tzinfo=timezone(timedelta(hours=-3)))

    def now(self):
        return self.value

    def today(self):
        return self.value.date()

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = FakeClock()
        self.db = Database(self.root / "dados.sqlite3", self.clock)
        self.db.migrate()
        self.addCleanup(self.db.close)

    def scalar(self, sql, params=()):
        return self.db.conn.execute(sql, params).fetchone()[0]

