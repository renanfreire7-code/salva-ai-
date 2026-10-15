import tempfile
import unittest
from pathlib import Path

from core import Store
from finance import migrate


class StoreTestCase(unittest.TestCase):
    """Cria um banco SQLite novo e migrado em uma pasta temporária para cada teste."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = Store(self.root / 'dados' / 'bar.sqlite3')
        migrate(self.store)

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()

    def product(self, name='Seda', price='5,00', pack=10, stock_packs=2):
        self.store.add_product(name, price, pack)
        pid = next(p['id'] for p in self.store.products() if p['name'] == name)
        if stock_packs:
            self.store.adjust_stock(pid, stock_packs, 'Caixa/Fardo (entrada)', '')
        return pid
