import sqlite3
import unittest
from unittest import mock

from core import BusinessError, money, parse_money
from tests.helpers import StoreTestCase


class MoneyTest(unittest.TestCase):
    def test_parse_money_accepts_brazilian_format(self):
        self.assertEqual(parse_money('1.234,56'), 123456)
        self.assertEqual(parse_money('R$ 5,5'), 550)
        self.assertEqual(parse_money('10'), 1000)

    def test_parse_money_rejects_invalid_values(self):
        for value in ('', 'abc', '-1'):
            with self.subTest(value=value), self.assertRaises(BusinessError):
                parse_money(value)

    def test_money_formats_in_reais(self):
        self.assertEqual(money(123456), 'R$ 1.234,56')


class StockAndTabsTest(StoreTestCase):
    def test_tab_items_reserve_stock_until_payment(self):
        pid = self.product()
        self.store.open_cash('0')
        tab = self.store.create_tab('Fulano')
        self.store.add_to_tab(tab, pid, 3)
        self.assertEqual(self.store.products()[0]['available'], 17)
        self.store.pay_tab(tab, 'Pix')
        p = self.store.products()[0]
        self.assertEqual((p['stock'], p['available']), (17, 17))

    def test_cannot_reserve_more_than_free_stock(self):
        pid = self.product(stock_packs=1)
        tab = self.store.create_tab('Fulano')
        with self.assertRaises(BusinessError):
            self.store.add_to_tab(tab, pid, 11)

    def test_sale_requires_open_cash(self):
        pid = self.product()
        with self.assertRaises(BusinessError):
            self.store.direct_sale(pid, 1, 'Dinheiro')


class QuantityValidationTest(StoreTestCase):
    """Bug: texto não numérico chegava ao usuário como ValueError em inglês."""

    def test_non_numeric_quantities_raise_business_error_in_portuguese(self):
        pid = self.product()
        self.store.open_cash('0')
        tab = self.store.create_tab('Fulano')
        calls = [
            lambda: self.store.add_to_tab(tab, pid, 'abc'),
            lambda: self.store.direct_sale(pid, '1,5', 'Pix'),
            lambda: self.store.adjust_stock(pid, '', 'Unidade (entrada)', ''),
            lambda: self.store.add_product('Isqueiro', '3,00', 'dez'),
            lambda: self.store.update_product(pid, '5,00', 'x'),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(BusinessError) as ctx:
                call()
            self.assertNotIn('invalid literal', str(ctx.exception))

    def test_quantities_with_spaces_are_accepted(self):
        pid = self.product()
        self.store.open_cash('0')
        self.store.direct_sale(pid, ' 2 ', 'Pix')
        self.assertEqual(self.store.products()[0]['stock'], 18)


class CloseCashTest(StoreTestCase):
    def test_close_cash_writes_backup_and_records_its_path(self):
        self.store.open_cash('50')
        dest = self.store.close_cash('50', self.root / 'backups')
        self.assertTrue(dest.exists())
        session = self.store.one('SELECT * FROM cash_sessions')
        self.assertEqual(session['backup_path'], str(dest))
        self.assertIsNotNone(session['closed_at'])

    def test_failed_backup_does_not_record_a_backup_path(self):
        """Bug: o caminho do backup era gravado antes da cópia; se ela falhasse,
        o caixa ficava apontando para um arquivo inexistente."""
        self.store.open_cash('50')
        with mock.patch('core.sqlite3.connect', side_effect=sqlite3.OperationalError('disco cheio')):
            with self.assertRaises(BusinessError) as ctx:
                self.store.close_cash('50', self.root / 'backups')
        self.assertIn('BACKUP FALHOU', str(ctx.exception))
        session = self.store.one('SELECT * FROM cash_sessions')
        self.assertIsNotNone(session['closed_at'], 'o caixa continua fechado, como antes')
        self.assertIsNone(session['backup_path'])
        self.assertEqual(list((self.root / 'backups').glob('*.sqlite3')), [])


if __name__ == '__main__':
    unittest.main()
