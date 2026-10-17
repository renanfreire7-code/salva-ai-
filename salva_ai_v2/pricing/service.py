from .models import PriceCondition, PriceQuote
from ..common.service import Service, integer
from ..common.errors import BusinessError


class PricingService(Service):
    def set_promotion(self, product_id, group_qty, group_cents, active, command_id):
        integer(group_qty, "Quantidade promocional", 2)
        integer(group_cents, "Preço do grupo", 1)
        def perform():
            product = self.one("products",product_id)
            if group_cents >= product["price_cents"] * group_qty:
                raise BusinessError("A promoção deve oferecer economia.")
            self.db.conn.execute("INSERT INTO promotions VALUES(?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET group_qty=excluded.group_qty,group_cents=excluded.group_cents,active=excluded.active",
                (product_id,group_qty,group_cents,bool(active)))
            return product_id
        return self.run(command_id,"promotion.updated",dict(product_id=product_id,qty=group_qty,price=group_cents,active=bool(active)),perform)

    def snapshot(self, product_id):
        p = self.one("products",product_id)
        promo = self.db.conn.execute("SELECT * FROM promotions WHERE product_id=? AND active=1", (product_id,)).fetchone()
        return PriceCondition(p["price_cents"],promo["group_qty"] if promo else None,promo["group_cents"] if promo else None)

    @staticmethod
    def quote(condition, qty):
        integer(qty, "Quantidade")
        if condition.group_qty:
            groups, remainder = divmod(qty, condition.group_qty)
            total = groups * condition.group_cents + remainder * condition.unit_cents
        else:
            total = condition.unit_cents * qty
        return PriceQuote(total,condition.unit_cents * qty - total)
