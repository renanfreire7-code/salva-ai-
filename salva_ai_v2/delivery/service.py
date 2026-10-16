from dataclasses import asdict
from .models import DeliveryOrder,DeliveryDraft
from ..sales.models import Payment
from ..common.service import Service,integer
from ..common.errors import BusinessError


class DeliveryService(Service):
    def __init__(self,db,inventory,pricing,sales,cash,finance,security,clock=None):
        super().__init__(db,security)
        self.inventory,self.pricing,self.sales=inventory,pricing,sales
        self.cash,self.finance,self.clock=cash,finance,clock or db.clock

    def configure_fees(self,customer_fee_cents,courier_fee_cents,command_id):
        integer(customer_fee_cents,"Taxa do cliente")
        integer(courier_fee_cents,"Valor do entregador")
        def perform():
            self.db.conn.execute("UPDATE delivery_settings SET customer_fee_cents=?,courier_fee_cents=? WHERE id=1",(customer_fee_cents,courier_fee_cents))
            return 1
        return self.run(command_id,"delivery.fees",dict(customer_fee_cents=customer_fee_cents,courier_fee_cents=courier_fee_cents),perform)

    def settings(self):
        return dict(self.db.conn.execute("SELECT * FROM delivery_settings WHERE id=1").fetchone())

    def list_orders(self):
        return [dict(r) for r in self.db.conn.execute("SELECT o.*,d.* FROM orders o JOIN delivery_orders d ON d.order_id=o.id ORDER BY o.id DESC")]

    def confirm(self,draft,command_id):
        if not draft.customer.strip() or not draft.phone.strip() or not draft.address.strip() or not draft.lines:
            raise BusinessError("Informe cliente, telefone, endereço e produtos.")
        if draft.payment_method not in ("MONEY","PIX","DEBIT","CREDIT") or draft.collection not in ("BAR","COURIER"):
            raise BusinessError("Escolha recebimento válido.")
        if len({line.product_id for line in draft.lines})!=len(draft.lines):
            raise BusinessError("Agrupe o mesmo produto em uma linha.")
        for line in draft.lines:
            integer(line.qty,"Quantidade",1)
        def perform():
            self.cash.require_open()
            id=self.sales._new("DELIVERY",draft.customer.strip(),command_id+":order")
            fees=self.settings()
            self.db.conn.execute("INSERT INTO delivery_orders(order_id,phone,address,reference,method,collection,delivery_fee_cents,courier_fee_cents) VALUES(?,?,?,?,?,?,?,?)",
                (id,draft.phone,draft.address,draft.reference,draft.payment_method,draft.collection,fees["customer_fee_cents"],fees["courier_fee_cents"]))
            for line in draft.lines:
                condition=self.pricing.snapshot(line.product_id)
                self.inventory.reserve(line.product_id,"DELIVERY",id,line.qty)
                self.db.conn.execute("INSERT INTO order_items VALUES(?,?,?,?,?,?)",(id,line.product_id,line.qty,condition.unit_cents,condition.group_qty,condition.group_cents))
            self.db.conn.execute("UPDATE orders SET state='PREPARING' WHERE id=?", (id,))
            return asdict(self.order(id))
        return DeliveryOrder(**self.run(command_id,"delivery.confirmed",dict(draft=asdict(draft)),perform))

    def order(self,order_id):
        order=self.one("orders",order_id)
        row=self.db.conn.execute("SELECT * FROM delivery_orders WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            raise BusinessError("Pedido de delivery não encontrado.")
        paid=self.db.conn.execute("SELECT COALESCE(SUM(amount_cents-refunded_cents),0) FROM collections WHERE order_id=?", (order_id,)).fetchone()[0]
        return DeliveryOrder(order_id,order["state"],self.sales.total(order_id)+row["delivery_fee_cents"],row["delivery_fee_cents"],row["courier_fee_cents"],paid)

    def dispatch(self,order_id,command_id):
        def perform():
            self.cash.require_open()
            order=self.order(order_id)
            if order.state!="PREPARING":
                raise BusinessError("Este pedido não está em preparação.")
            self.sales.record_delivery_sale(order_id,command_id+":sale")
            trip=self.db.conn.execute("INSERT INTO trips(order_id,dispatched_at,fee_cents) VALUES(?,?,?)",
                (order_id,self.clock.now().isoformat(),order.courier_fee_cents)).lastrowid
            if order.courier_fee_cents:
                today=self.clock.today().isoformat()
                self.db.conn.execute("INSERT INTO obligations(source_type,source_id,description,category,amount_cents,incurred_on,due_on,created_at) VALUES('TRIP',?,?,'Delivery',?,?,?,?)",
                    (str(trip),f"Corrida #{trip}",order.courier_fee_cents,today,today,self.clock.now().isoformat()))
            self.db.conn.execute("UPDATE orders SET state='OUT' WHERE id=?", (order_id,))
            return trip
        return self.run(command_id,"delivery.dispatched",dict(order_id=order_id),perform)

