from dataclasses import asdict
from .models import StockPosition, PurchaseLine
from ..common.service import Service, integer, valid_date
from ..common.money import allocate, round_half_up
from ..common.errors import BusinessError


class InventoryService(Service):
    def receive_and_pay_purchase(self, lines, freight_cents, incurred_on, due_on, payment, grant, command_id):
        payload = dict(lines=[asdict(line) for line in lines], freight=freight_cents,
                       incurred=valid_date(incurred_on), due=valid_date(due_on),
                       payment=asdict(payment) if payment else None)
        def perform():
            purchase = self.receive_purchase(lines, freight_cents, incurred_on, due_on, command_id + ':receive')
            if payment:
                obligation = self.db.conn.execute("SELECT id,amount_cents FROM obligations WHERE source_type='PURCHASE' AND source_id=?", (str(purchase),)).fetchone()
                finance = getattr(self, 'finance', None)
                if finance is None:
                    raise BusinessError('Pagamento de compras ainda não foi configurado.')
                finance.pay_obligation(obligation['id'], obligation['amount_cents'], self.db.clock.today(), payment.method,
                                       payment.method == 'MONEY', grant, command_id + ':pay')
            return purchase
        return self.run(command_id, 'purchase.received_and_paid', payload, perform)

    def assign_shortcut(self, key, product_id, command_id):
        integer(key, 'Tecla', 1)
        if key > 12:
            raise BusinessError('Escolha uma tecla de F1 a F12.')
        def perform():
            self.one('products', product_id)
            self.db.conn.execute('INSERT INTO product_shortcuts VALUES(?,?) ON CONFLICT(key) DO UPDATE SET product_id=excluded.product_id', (key, product_id))
            return key
        return self.run(command_id, 'shortcut.assigned', dict(key=key, product_id=product_id), perform)

    def shortcut(self, key):
        return self.db.conn.execute('SELECT p.* FROM product_shortcuts s JOIN products p ON p.id=s.product_id WHERE s.key=? AND p.active=1', (key,)).fetchone()

    def create_product(self, name, price_cents, pack_size, min_stock, command_id):
        name = str(name).strip()
        if not name:
            raise BusinessError("Informe o nome do produto.")
        integer(price_cents, "Preço", 1)
        integer(pack_size, "Unidades por caixa", 1)
        integer(min_stock, "Estoque mínimo")
        def perform():
            return self.db.conn.execute("INSERT INTO products(name,price_cents,pack_size,min_stock) VALUES(?,?,?,?)",
                (name, price_cents, pack_size, min_stock)).lastrowid
        return self.run(command_id, "product.created", dict(name=name, price=price_cents, pack=pack_size, minimum=min_stock), perform)

    def products(self, include_inactive=False):
        return [dict(r) for r in self.db.conn.execute(
            "SELECT * FROM products WHERE active=1 OR ? ORDER BY name", (include_inactive,))]

    def position(self, product_id):
        p = self.one("products", product_id)
        reserved = self.db.conn.execute("SELECT COALESCE(SUM(qty),0) FROM reservations WHERE product_id=?", (product_id,)).fetchone()[0]
        return StockPosition(product_id, p["stock"], reserved, p["stock"] - reserved, p["value_cents"])

    def _movement(self, pid, qty, value, kind, source_id=None, reason=None):
        if not self.db.conn.in_transaction:
            raise RuntimeError("Movimento exige transação")
        self.db.conn.execute("UPDATE products SET stock=stock+?,value_cents=value_cents+? WHERE id=?", (qty, value, pid))
        self.db.conn.execute("INSERT INTO stock_movements(product_id,moved_at,qty,value_cents,kind,source_id,reason) VALUES(?,?,?,?,?,?,?)",
            (pid, self.db.clock.now().isoformat(), qty, value, kind, source_id, reason))

    def receive_purchase(self, lines, freight_cents, incurred_on, due_on, command_id):
        integer(freight_cents, "Frete")
        incurred, due = valid_date(incurred_on), valid_date(due_on)
        if not lines:
            raise BusinessError("Adicione produtos à compra.")
        if len({line.product_id for line in lines}) != len(lines):
            raise BusinessError("Agrupe o mesmo produto em uma linha da compra.")
        for line in lines:
            integer(line.qty, "Quantidade", 1)
            integer(line.total_cents, "Custo total", 1)
        payload = dict(lines=[asdict(line) for line in lines], freight=freight_cents, incurred=incurred, due=due)
        def perform():
            costs = {line.product_id: line.total_cents for line in lines}
            freight = allocate(freight_cents, costs)
            total = sum(costs.values()) + freight_cents
            purchase = self.db.conn.execute("INSERT INTO purchases(incurred_on,total_cents) VALUES(?,?)", (incurred,total)).lastrowid
            for line in lines:
                if not self.one("products", line.product_id)["active"]:
                    raise BusinessError("Produto desativado.")
                cost = line.total_cents + freight[line.product_id]
                self.db.conn.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,total_cents) VALUES(?,?,?,?)",
                    (purchase,line.product_id,line.qty,cost))
                self._movement(line.product_id, line.qty, cost, "PURCHASE", purchase)
            self.db.conn.execute("INSERT INTO obligations(source_type,source_id,description,category,amount_cents,incurred_on,due_on,created_at) VALUES('PURCHASE',?,?,?,?,?,?,?)",
                (str(purchase), f"Compra #{purchase}", "Compra de estoque", total, incurred, due, self.db.clock.now().isoformat()))
            return purchase
        return self.run(command_id, "purchase.received", payload, perform)

    def reserve(self, product_id, owner_type, owner_id, qty):
        integer(qty, "Quantidade", 1)
        if not self.db.conn.in_transaction:
            raise RuntimeError("Reserva exige transação")
        if not self.one("products", product_id)["active"]:
            raise BusinessError("Produto desativado.")
        pos = self.position(product_id)
        existing = self.db.conn.execute("SELECT qty FROM reservations WHERE product_id=? AND owner_type=? AND owner_id=?", (product_id,owner_type,owner_id)).fetchone()
        if qty > pos.available + (existing[0] if existing else 0):
            raise BusinessError("Estoque disponível insuficiente.")
        self.db.conn.execute("INSERT INTO reservations VALUES(?,?,?,?) ON CONFLICT(product_id,owner_type,owner_id) DO UPDATE SET qty=excluded.qty",
            (product_id,owner_type,owner_id,qty))

    def release(self, product_id, owner_type, owner_id, qty=None):
        if not self.db.conn.in_transaction:
            raise RuntimeError("Liberação exige transação")
        self.db.conn.execute("DELETE FROM reservations WHERE product_id=? AND owner_type=? AND owner_id=?", (product_id,owner_type,owner_id))

    def consume(self, product_id, qty, kind="CONSUMPTION", source_id=None, reason=None):
        integer(qty, "Quantidade", 1)
        pos = self.position(product_id)
        if qty > pos.available:
            raise BusinessError("Estoque disponível insuficiente.")
        cost = pos.value_cents if qty == pos.physical else round_half_up(pos.value_cents * qty, pos.physical)
        self._movement(product_id, -qty, -cost, kind, source_id, reason)
        return cost

    def adjust(self, product_id, delta, reason, grant, command_id):
        if type(delta) is not int or not delta:
            raise BusinessError("Informe uma quantidade inteira diferente de zero.")
        def perform():
            self.protect(grant, "stock.adjust", reason)
            pos = self.position(product_id)
            if delta < 0:
                cost = self.consume(product_id, -delta, "LOSS", reason=reason)
            else:
                if not pos.physical:
                    raise BusinessError("Registre uma compra com custo para iniciar este estoque.")
                cost = round_half_up(pos.value_cents * delta, pos.physical)
                self._movement(product_id, delta, cost, "ADJUSTMENT", reason=reason)
            return product_id
        return self.run(command_id, "stock.adjusted", dict(product_id=product_id, delta=delta,reason=reason), perform)

    def deactivate(self, product_id, grant, reason, command_id):
        def perform():
            self.protect(grant, "product.deactivate", reason)
            self.one("products",product_id)
            self.db.conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
            return product_id
        return self.run(command_id,"product.deactivated",dict(product_id=product_id,reason=reason),perform)

    def return_to_supplier(self, purchase_id, lines, grant, reason, command_id):
        if not lines or len({line.product_id for line in lines}) != len(lines):
            raise BusinessError("Informe os produtos da devolução sem repetir linhas.")
        for line in lines:
            integer(line.qty, "Quantidade", 1)
        def perform():
            self.protect(grant, "purchase.return", reason)
            if self.one("purchases",purchase_id)["reversed"]:
                raise BusinessError("Compra já revertida.")
            credit = 0
            for line in lines:
                row = self.db.conn.execute("SELECT * FROM purchase_items WHERE purchase_id=? AND product_id=?", (purchase_id,line.product_id)).fetchone()
                if row is None or line.qty > row["qty"] - row["returned_qty"]:
                    raise BusinessError("Quantidade acima da compra disponível para devolução.")
                self.consume(line.product_id,line.qty,"SUPPLIER_RETURN",purchase_id,reason)
                credit += round_half_up(row["total_cents"] * line.qty, row["qty"])
                self.db.conn.execute("UPDATE purchase_items SET returned_qty=returned_qty+? WHERE id=?", (line.qty,row["id"]))
            return self.db.conn.execute("INSERT INTO supplier_credits(purchase_id,amount_cents,reason) VALUES(?,?,?)",(purchase_id,credit,reason)).lastrowid
        return self.run(command_id,"purchase.returned",dict(purchase_id=purchase_id,lines=[asdict(l) for l in lines],reason=reason),perform)

    def reverse_purchase(self, purchase_id, grant, reason, command_id):
        def perform():
            self.protect(grant, "purchase.reverse", reason)
            purchase = self.one("purchases",purchase_id)
            if purchase["reversed"]:
                raise BusinessError("Compra já revertida.")
            items = self.db.conn.execute("SELECT * FROM purchase_items WHERE purchase_id=?", (purchase_id,)).fetchall()
            for item in items:
                entry = self.db.conn.execute("SELECT id FROM stock_movements WHERE kind='PURCHASE' AND source_id=? AND product_id=?", (purchase_id,item["product_id"])).fetchone()
                later = self.db.conn.execute("SELECT 1 FROM stock_movements WHERE product_id=? AND id>? AND qty<0", (item["product_id"],entry["id"])).fetchone()
                if later or item["returned_qty"] or self.position(item["product_id"]).available < item["qty"]:
                    raise BusinessError("Compra já movimentada. Use uma correção auditada.")
                self._movement(item["product_id"],-item["qty"],-item["total_cents"],"PURCHASE_REVERSED",purchase_id,reason)
            self.db.conn.execute("UPDATE purchases SET reversed=1 WHERE id=?", (purchase_id,))
            self.db.conn.execute("UPDATE obligations SET deleted_at=? WHERE source_type='PURCHASE' AND source_id=?", (self.db.clock.now().isoformat(),str(purchase_id)))
            return purchase_id
        return self.run(command_id,"purchase.reversed",dict(purchase_id=purchase_id,reason=reason),perform)

