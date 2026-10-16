from ..sales.models import Payment
from ..common.service import integer
from ..common.errors import BusinessError


class ReceiptsMixin:
    def record_payment(self,order_id,method,amount_cents,custodian,tendered_cents,command_id):
        integer(amount_cents,"Valor recebido",1)
        if custodian not in ("BAR","COURIER") or method not in ("MONEY","PIX","DEBIT","CREDIT"):
            raise BusinessError("Recebimento inválido.")
        if method!="MONEY" and custodian!="BAR":
            raise BusinessError("Confirme o recebimento digital na conta ou maquininha do bar.")
        def perform():
            self.cash.require_open()
            order=self.order(order_id)
            details=self.db.conn.execute("SELECT * FROM delivery_orders WHERE order_id=?", (order_id,)).fetchone()
            if order.state not in ("PREPARING","OUT","DELIVERED") or order.paid_cents:
                raise BusinessError("Pedido cancelado ou pagamento já registrado.")
            if amount_cents!=order.total_cents or method!=details["method"]:
                raise BusinessError("Confirme o total e a modalidade combinada no pedido.")
            change=self.sales._payment(Payment(method,tendered_cents),amount_cents)
            if custodian=="COURIER":
                available=self.db.conn.execute("SELECT COALESCE(SUM(delta_cents),0) FROM custody_entries").fetchone()[0]
                if change>available:
                    raise BusinessError("O entregador não possui troco registrado suficiente.")
            payment=self.db.conn.execute("INSERT INTO collections(order_id,amount_cents,method,custodian,tendered_cents,change_cents,collected_at) VALUES(?,?,?,?,?,?,?)",
                (order_id,amount_cents,method,custodian,tendered_cents,change,self.clock.now().isoformat())).lastrowid
            if method=="MONEY":
                if custodian=="BAR":
                    self.cash.entry(amount_cents,"DELIVERY_RECEIPT","collection:"+str(payment))
                else:
                    self.db.conn.execute("INSERT INTO custody_entries(occurred_at,delta_cents,kind,source) VALUES(?,?,?,?)",
                        (self.clock.now().isoformat(),amount_cents,"COLLECTION","collection:"+str(payment)))
            return payment
        return self.run(command_id,"delivery.payment",dict(order_id=order_id,method=method,amount_cents=amount_cents,custodian=custodian,tendered_cents=tendered_cents),perform)

    def mark_delivered(self,order_id,command_id):
        def perform():
            self.cash.require_open()
            if self.order(order_id).state!="OUT":
                raise BusinessError("Somente pedido que saiu pode ser entregue.")
            self.db.conn.execute("UPDATE orders SET state='DELIVERED' WHERE id=?", (order_id,))
            return order_id
        return self.run(command_id,"delivery.delivered",dict(order_id=order_id),perform)

