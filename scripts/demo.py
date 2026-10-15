"""Abre o aplicativo com dados FICTÍCIOS em uma pasta temporária (não toca em ~/SalvaAiHeadshop).

Uso: python3 scripts/demo.py
"""
import os
import sys
import tempfile
from pathlib import Path

home = Path(tempfile.mkdtemp(prefix='salva_ai_demo_'))
os.environ['HOME'] = str(home)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'salva_ai_headshop'))

import app  # noqa: E402
import finance  # noqa: E402
from core import Store  # noqa: E402

app.ROOT = home / 'SalvaAiHeadshop'
app.STORE = store = Store(app.ROOT / 'dados' / 'bar.sqlite3')
finance.migrate(store)

for name, price, pack in [('Seda King Size', '5,00', 25), ('Isqueiro', '12,00', 24),
                          ('Piteira de vidro', '35,00', 1), ('Dichavador metal', '49,90', 1)]:
    store.add_product(name, price, pack)
for p in store.products():
    store.adjust_stock(p['id'], 2, 'Caixa/Fardo (entrada)', 'Compra inicial (demo)')
    finance.set_product_cost(store, p['id'], f"{p['price'] / 200:.2f}".replace('.', ','), 10)
finance.update_settings(store, {'Dinheiro': '0', 'Pix': '0', 'Débito': '1,5', 'Crédito': '3,5'}, '')
store.open_cash('100,00')
ids = [p['id'] for p in store.products()]
tab = store.create_tab('Cliente teste A')
store.add_to_tab(tab, ids[0], 2)
store.add_to_tab(tab, ids[2], 1)
paid = store.create_tab('Cliente teste B')
store.add_to_tab(paid, ids[1], 1)
store.pay_tab(paid, 'Pix')
store.direct_sale(ids[3], 1, 'Crédito')
today = finance.date.today()
finance.add_expense(store, 'Aluguel (demo)', 'Aluguel', '1.500,00', today.isoformat(), paid=True)
finance.add_expense(store, 'Energia (demo)', 'Energia', '230,00', today.isoformat())

print('Dados de demonstração em', home)
app.App().mainloop()
