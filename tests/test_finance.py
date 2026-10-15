import unittest

from core import BusinessError
from finance import (add_expense, backup_before_upgrade, month_summary, parse_percent,
                     payment_fee, profitability, reopen_paid_tab, set_paid,
                     set_product_cost, update_settings)
from tests.helpers import StoreTestCase


class PercentAndFeeTest(unittest.TestCase):
    def test_parse_percent_returns_basis_points(self):
        self.assertEqual(parse_percent('3,5'), 350)
        self.assertEqual(parse_percent('0,99%'), 99)

    def test_parse_percent_rejects_out_of_range(self):
        for value in ('-1', '101', 'abc', '1,234'):
            with self.subTest(value=value), self.assertRaises(BusinessError):
                parse_percent(value)

    def test_payment_fee_rounds_half_up(self):
        self.assertEqual(payment_fee(1500, 350), 53)  # 52,5 centavos


class FinanceFlowTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.pid = self.product(price='5,00')
        set_product_cost(self.store, self.pid, '2,00', 0)
        update_settings(self.store, {'Dinheiro': '0', 'Pix': '0', 'Débito': '1,5', 'Crédito': '3,5'}, '')
        self.store.open_cash('0')

    def test_fee_is_snapshotted_at_sale_time(self):
        self.store.direct_sale(self.pid, 2, 'Crédito')
        update_settings(self.store, {'Dinheiro': '0', 'Pix': '0', 'Débito': '1,5', 'Crédito': '10'}, '')
        sale = self.store.one('SELECT * FROM sales')
        self.assertEqual((sale['payment_rate_bp'], sale['payment_fee']), (350, 35))

    def test_month_summary_and_profitability_agree(self):
        self.store.direct_sale(self.pid, 4, 'Crédito')  # 20,00 venda, 8,00 CMV, 0,70 taxa
        month = self.store.one('SELECT substr(sold_at,1,7) m FROM sales')['m']
        add_expense(self.store, 'Luz', 'Energia', '5,00', month + '-10')
        summary = month_summary(self.store, month)
        self.assertEqual(summary['estimated_profit'], 2000 - 800 - 70 - 500)
        rows, _ = profitability(self.store, month)
        self.assertEqual(sum(r['profit'] for r in rows), summary['estimated_profit'])

    def test_stock_purchases_are_not_deducted_from_profit(self):
        self.store.direct_sale(self.pid, 1, 'Dinheiro')
        month = self.store.one('SELECT substr(sold_at,1,7) m FROM sales')['m']
        add_expense(self.store, 'Fardo', 'Compra de estoque', '100', month + '-01')
        summary = month_summary(self.store, month)
        self.assertEqual(summary['estimated_profit'], 500 - 200)
        self.assertEqual(summary['purchases'], 10000)

    def test_set_paid_only_once(self):
        add_expense(self.store, 'Aluguel', 'Aluguel', '1000', '2026-10-05')
        eid = self.store.one('SELECT id FROM expenses')['id']
        set_paid(self.store, eid, '2026-10-06')
        with self.assertRaises(BusinessError):
            set_paid(self.store, eid, '2026-10-07')

    def test_reopen_paid_tab_voids_sale_and_restores_reservation(self):
        tab = self.store.create_tab('Fulano')
        self.store.add_to_tab(tab, self.pid, 2)
        self.store.pay_tab(tab, 'Pix')
        reopen_paid_tab(self.store, tab, 'Cobrado errado')
        self.assertIsNotNone(self.store.one('SELECT voided_at FROM sales')['voided_at'])
        p = self.store.products()[0]
        self.assertEqual((p['stock'], p['available']), (20, 18))


class BackupBeforeUpgradeTest(StoreTestCase):
    def test_fresh_install_does_not_create_upgrade_backup(self):
        """Bug: todo banco novo (vazio) gerava um backup 'antes_atualizacao_034_'."""
        fresh = self._fresh_store()
        try:
            self.assertIsNone(backup_before_upgrade(fresh, self.root / 'backups'))
        finally:
            fresh.close()
        self.assertEqual(list((self.root / 'backups').glob('*')), [])

    def test_legacy_database_with_data_is_backed_up_before_migration(self):
        fresh = self._fresh_store()
        try:
            fresh.add_product('Seda', '5,00', 10)
            path = backup_before_upgrade(fresh, self.root / 'backups')
        finally:
            fresh.close()
        self.assertTrue(path.name.startswith('antes_atualizacao_034_'))
        self.assertTrue(path.exists())

    def test_already_migrated_database_is_not_backed_up_again(self):
        self.product()
        self.assertIsNone(backup_before_upgrade(self.store, self.root / 'backups'))

    def _fresh_store(self):
        from core import Store
        return Store(self.root / 'legado' / 'bar.sqlite3')


if __name__ == '__main__':
    unittest.main()
