from dataclasses import asdict
from .models import Payment, SaleResult
from ..pricing.models import PriceCondition
from ..common.service import Service, integer
from ..common.money import round_half_up
from ..common.errors import BusinessError


class SalesService(Service):
    def record_delivery_sale(self, order_id, command_id):
        def perform():
            order=self.one('orders',order_id)
            if order['kind']!='DELIVERY' or order['state']!='PREPARING':
                raise BusinessError('Pedido não está em preparação.')
            details=self.db.conn.execute('SELECT * FROM delivery_orders WHERE order_id=?',(order_id,)).fetchone()
            return self._record_sale(order_id,Payment(details['method']),collect=False,delivery_fee_cents=details['delivery_fee_cents'])
        return SaleResult(**self.run(command_id,'delivery.sale',dict(order_id=order_id),perform))

    def __init__(self, db, inventory, pricing, cash, security):
        super().__init__(db, security)
        self.inventory, self.pricing, self.cash = inventory, pricing, cash

    def _new(self, kind, name, command_id):
        def perform():
            session = self.cash.require_open()
            return self.db.conn.execute("INSERT INTO orders(kind,name,session_id,created_at) VALUES(?,?,?,?)",
                (kind,name,session["id"],self.db.clock.now().isoformat())).lastrowid
        return self.run(command_id,"order.created",dict(kind=kind,name=name),perform)

    def create_cart(self, command_id):
        return self._new("CART","Venda direta",command_id)

    def create_tab(self, name, command_id):
        name = str(name).strip()
        if not name:
            raise BusinessError("Informe o nome do cliente.")
        return self._new("TAB",name,command_id)

    def lines(self, order_id):
        return [dict(r) for r in self.db.conn.execute("SELECT i.*,p.name FROM order_items i JOIN products p ON p.id=i.product_id WHERE order_id=? ORDER BY product_id", (order_id,))]

    def total(self, order_id):
        return sum(self.pricing.quote(PriceCondition(row["unit_cents"],row["group_qty"],row["group_cents"]),row["qty"]).total_cents for row in self.lines(order_id))

    def open_tabs(self):
        return [dict(r) for r in self.db.conn.execute("SELECT * FROM orders WHERE kind='TAB' AND state='OPEN' ORDER BY id DESC")]

    def _set_qty(self, order_id, product_id, qty, kind, grant, reason, command_id):
        integer(qty,"Quantidade")
        def perform():
            self.cash.require_open()
            order = self.one("orders",order_id)
            if order["kind"] != kind or order["state"] != "OPEN":
                raise BusinessError("Este atendimento não está aberto.")
            row = self.db.conn.execute("SELECT * FROM order_items WHERE order_id=? AND product_id=?", (order_id,product_id)).fetchone()
            old = row["qty"] if row else 0
            product = self.one("products",product_id)
            if qty > old and not product["active"]:
                raise BusinessError("Produto desativado.")
            if kind=="TAB" and qty < old:
                self.protect(grant,"tab.reduce",reason)
            if kind=="TAB":
                self.inventory.release(product_id,kind,order_id)
                if qty:
                    if product["active"]:
                        self.inventory.reserve(product_id,kind,order_id,qty)
                    else:
                        if qty > old:
                            raise BusinessError("Produto desativado.")
                        self.db.conn.execute("INSERT INTO reservations VALUES(?,?,?,?)",(product_id,kind,order_id,qty))
            elif qty > self.inventory.position(product_id).available:
                raise BusinessError("Estoque disponível insuficiente.")
            condition = PriceCondition(row["unit_cents"],row["group_qty"],row["group_cents"]) if row else self.pricing.snapshot(product_id)
            self.db.conn.execute("INSERT INTO order_items VALUES(?,?,?,?,?,?) ON CONFLICT(order_id,product_id) DO UPDATE SET qty=excluded.qty",
                (order_id,product_id,qty,condition.unit_cents,condition.group_qty,condition.group_cents))
            return order_id
        return self.run(command_id,"order.quantity",dict(order_id=order_id,product_id=product_id,qty=qty,kind=kind,reason=reason),perform)

    def set_cart_qty(self, cart_id, product_id, qty, command_id):
        return self._set_qty(cart_id,product_id,qty,"CART",None,None,command_id)

    def set_tab_qty(self, tab_id, product_id, qty, grant, reason, command_id):
        return self._set_qty(tab_id,product_id,qty,"TAB",grant,reason,command_id)

    def _payment(self, payment, total):
        if not isinstance(payment,Payment) or payment.method not in ("MONEY","PIX","DEBIT","CREDIT"):
            raise BusinessError("Forma de pagamento inválida.")
        if payment.method=="MONEY":
            integer(payment.tendered_cents,"Valor recebido")
            if payment.tendered_cents < total:
                raise BusinessError("O valor recebido é menor que o total.")
            return payment.tendered_cents - total
        if payment.tendered_cents is not None:
            raise BusinessError("Informe valor recebido apenas em dinheiro.")
        return 0

    def _record_sale(self, order_id, payment, collect=True, delivery_fee_cents=0):
        session = self.cash.require_open()
        order = self.one("orders",order_id)
        items = [r for r in self.lines(order_id) if r["qty"]]
        if not items:
            raise BusinessError("Adicione pelo menos um produto.")
        total = self.total(order_id) + delivery_fee_cents
        change = self._payment(payment,total) if collect else 0
        if payment.method not in ("MONEY","PIX","DEBIT","CREDIT"):
            raise BusinessError("Forma de pagamento inválida.")
        rate = self.db.conn.execute("SELECT rate_bp FROM payment_settings WHERE method=?", (payment.method,)).fetchone()[0]
        fee = round_half_up(total*(rate or 0),10000)
        sale_id = self.db.conn.execute("INSERT INTO sales(order_id,session_id,sold_at,method,total_cents,fee_cents,rate_bp,tendered_cents,change_cents,delivery_fee_cents) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (order_id,session["id"],self.db.clock.now().isoformat(),payment.method,total,fee,rate,payment.tendered_cents,change,delivery_fee_cents)).lastrowid
        for row in items:
            self.inventory.release(row["product_id"],order["kind"],order_id)
            cost = self.inventory.consume(row["product_id"],row["qty"])
            price = self.pricing.quote(PriceCondition(row["unit_cents"],row["group_qty"],row["group_cents"]),row["qty"]).total_cents
            self.db.conn.execute("INSERT INTO sale_items(sale_id,product_id,qty,total_cents,cogs_cents,unit_cents,group_qty,group_cents) VALUES(?,?,?,?,?,?,?,?)",
                (sale_id,row["product_id"],row["qty"],price,cost,row["unit_cents"],row["group_qty"],row["group_cents"]))
        if collect and payment.method=="MONEY":
            self.cash.entry(total,"SALE","sale:"+str(sale_id))
        self.db.conn.execute("UPDATE orders SET state='PAID' WHERE id=?", (order_id,))
        return dict(id=sale_id,total_cents=total,change_cents=change)

    def _pay(self, order_id, payment, kind, command_id):
        def perform():
            order = self.one("orders",order_id)
            if order["kind"] != kind or order["state"] != "OPEN":
                raise BusinessError("Este atendimento já foi concluído.")
            return self._record_sale(order_id,payment)
        result = self.run(command_id,"sale.confirmed",dict(order_id=order_id,payment=asdict(payment),kind=kind),perform)
        return SaleResult(**result)

    def sell(self, cart_id, payment, command_id):
        return self._pay(cart_id,payment,"CART",command_id)

    def pay_tab(self, tab_id, payment, command_id):
        return self._pay(tab_id,payment,"TAB",command_id)

    def cancel_tab(self, tab_id, grant, reason, command_id):
        def perform():
            self.cash.require_open()
            self.protect(grant,"tab.cancel",reason)
            order = self.one("orders",tab_id)
            if order["kind"]!="TAB" or order["state"]!="OPEN":
                raise BusinessError("Comanda não está aberta.")
            self.db.conn.execute("DELETE FROM reservations WHERE owner_type='TAB' AND owner_id=?", (tab_id,))
            self.db.conn.execute("UPDATE orders SET state='CANCELED' WHERE id=?", (tab_id,))
            return tab_id
        return self.run(command_id,"tab.canceled",dict(tab_id=tab_id,reason=reason),perform)

    def reverse_sale(self, sale_id, return_items, refund, reopen_tab, grant, reason, command_id):
        def perform():
            self.protect(grant,"sale.reverse",reason)
            session = self.cash.require_open()
            sale = self.one("sales",sale_id)
            order = self.one("orders",sale["order_id"])
            if sale["reversed"]:
                raise BusinessError("Venda já estornada.")
            if reopen_tab and (order["kind"]!="TAB" or session["id"]!=sale["session_id"] or not return_items):
                raise BusinessError("Reabra a comanda somente no caixa original e com devolução ao estoque.")
            items = self.db.conn.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
            if return_items:
                for item in items:
                    self.inventory._movement(item["product_id"],item["qty"],item["cogs_cents"],"SALE_RETURN",sale_id,reason)
            if refund is not None:
                if refund.method != sale["method"]:
                    raise BusinessError("Confirme o reembolso no meio de pagamento original.")
                if refund.method=="MONEY":
                    integer(refund.tendered_cents,"Valor devolvido")
                    if refund.tendered_cents!=sale["total_cents"]:
                        raise BusinessError("Informe o valor total do reembolso.")
                    self.cash.entry(-sale["total_cents"],"REFUND","refund:"+str(sale_id),reason)
            self.db.conn.execute("INSERT INTO refunds(sale_id,order_id,pending_cents,refunded_cents) VALUES(?,?,?,?)",
                (sale_id,order["id"],sale["total_cents"] if refund is None else 0,0 if refund is None else sale["total_cents"]))
            self.db.conn.execute("UPDATE sales SET reversed=1 WHERE id=?", (sale_id,))
            correction = self.db.conn.execute("INSERT INTO sale_corrections(sale_id,occurred_at,session_id,returned,reason) VALUES(?,?,?,?,?)",
                (sale_id,self.db.clock.now().isoformat(),session["id"],bool(return_items),reason)).lastrowid
            self.db.conn.execute("UPDATE orders SET state=? WHERE id=?", ("OPEN" if reopen_tab else "REVERSED",order["id"]))
            if reopen_tab:
                for item in items:
                    self.db.conn.execute("INSERT INTO reservations VALUES(?,?,?,?)",
                        (item["product_id"],"TAB",order["id"],item["qty"]))
            return correction
        return self.run(command_id,"sale.reversed",dict(sale_id=sale_id,return_items=bool(return_items),refund=asdict(refund) if refund else None,reopen_tab=bool(reopen_tab),reason=reason),perform)

