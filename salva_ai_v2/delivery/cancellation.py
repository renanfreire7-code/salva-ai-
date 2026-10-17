from dataclasses import asdict
from .models import DeliveryDraft
from ..inventory.models import CartLine
from ..common.money import round_half_up
from ..common.service import integer
from ..common.errors import BusinessError
from ..cash.receipts import record_receipt


class CancellationMixin:
    def cancel(self,order_id,grant,reason,command_id):
        def perform():
            session=self.cash.require_open()
            self.protect(grant,"delivery.cancel",reason)
            order=self.order(order_id)
            if order.state=="CANCELED":
                raise BusinessError("Pedido já cancelado.")
            sale=self.db.conn.execute("SELECT * FROM sales WHERE order_id=? AND reversed=0",(order_id,)).fetchone()
            if sale:
                self.db.conn.execute("UPDATE sales SET reversed=1 WHERE id=?", (sale["id"],))
                self.db.conn.execute("INSERT INTO sale_corrections(sale_id,occurred_at,session_id,returned,reason) VALUES(?,?,?,?,?)",
                    (sale["id"],self.clock.now().isoformat(),session["id"],0,reason))
            else:
                self.db.conn.execute("DELETE FROM reservations WHERE owner_type='DELIVERY' AND owner_id=?", (order_id,))
            if order.paid_cents:
                self.db.conn.execute("INSERT INTO refunds(sale_id,order_id,pending_cents) VALUES(?,?,?)",
                    (sale["id"] if sale else None,order_id,order.paid_cents))
            self.db.conn.execute("UPDATE orders SET state='CANCELED' WHERE id=?", (order_id,))
            return order_id
        return self.run(command_id,"delivery.canceled",dict(order_id=order_id,reason=reason),perform)

    def confirm_return(self,order_id,returned,grant,reason,command_id):
        if not returned or len({r.product_id for r in returned})!=len(returned):
            raise BusinessError("Informe os produtos conferidos sem repetir linhas.")
        for row in returned:
            integer(row.qty,"Quantidade",1)
        def perform():
            self.cash.require_open()
            self.protect(grant,"delivery.return",reason)
            if self.order(order_id).state!="CANCELED":
                raise BusinessError("Confira a devolução de um pedido cancelado.")
            sale=self.db.conn.execute("SELECT * FROM sales WHERE order_id=?",(order_id,)).fetchone()
            if not sale:
                raise BusinessError("Pedido não saiu; não há baixa para devolver.")
            for item in returned:
                line=self.db.conn.execute("SELECT * FROM sale_items WHERE sale_id=? AND product_id=?",(sale["id"],item.product_id)).fetchone()
                old=self.db.conn.execute("SELECT COALESCE(SUM(qty),0),COALESCE(SUM(cogs_cents),0) FROM delivery_returns WHERE order_id=? AND product_id=?",(order_id,item.product_id)).fetchone()
                if not line or item.qty>line["qty"]-old[0]:
                    raise BusinessError("Devolução acima da quantidade que saiu.")
                cost=round_half_up((line["cogs_cents"]-old[1])*item.qty,line["qty"]-old[0])
                self.inventory._movement(item.product_id,item.qty,cost,"DELIVERY_RETURN",order_id,reason)
                self.db.conn.execute("INSERT INTO delivery_returns(order_id,product_id,qty,cogs_cents,returned_at) VALUES(?,?,?,?,?)",(order_id,item.product_id,item.qty,cost,self.clock.now().isoformat()))
            return order_id
        return self.run(command_id,"delivery.returned",dict(order_id=order_id,returned=[asdict(r) for r in returned],reason=reason),perform)

    def refund(self,order_id,method,amount_cents,from_drawer,grant,reason,command_id):
        integer(amount_cents,"Reembolso",1)
        def perform():
            session=self.cash.require_open()
            self.protect(grant,"delivery.refund",reason)
            row=self.db.conn.execute("SELECT * FROM refunds WHERE order_id=? AND pending_cents>0",(order_id,)).fetchone()
            collection=self.db.conn.execute("SELECT * FROM collections WHERE order_id=?",(order_id,)).fetchone()
            if row is None or not collection or method!=collection["method"] or amount_cents>row["pending_cents"]:
                raise BusinessError("Confira pedido, forma e valor pendente de reembolso.")
            if method=="MONEY":
                if from_drawer:
                    self.cash.entry(-amount_cents,"DELIVERY_REFUND","delivery-refund:"+command_id,reason)
                else:
                    available=collection["amount_cents"]-collection["settled_cents"]-collection["courier_refunded_cents"]
                    if collection["custodian"]!="COURIER" or amount_cents>available:
                        raise BusinessError("O entregador não tem esse valor do pedido. Use a gaveta se devolvido pelo bar.")
                    self.db.conn.execute("INSERT INTO custody_entries(occurred_at,delta_cents,kind,source) VALUES(?,?,?,?)",
                        (self.clock.now().isoformat(),-amount_cents,"REFUND","delivery-refund:"+command_id))
                    self.db.conn.execute("UPDATE collections SET courier_refunded_cents=courier_refunded_cents+? WHERE id=?", (amount_cents,collection["id"]))
            elif from_drawer:
                raise BusinessError("Reembolso digital não movimenta dinheiro na gaveta.")
            record_receipt(self.db,session['id'],method,-amount_cents,'delivery-refund:'+command_id,'COURIER' if method=='MONEY' and not from_drawer else 'BAR')
            self.db.conn.execute("UPDATE collections SET refunded_cents=refunded_cents+? WHERE id=?", (amount_cents,collection["id"]))
            self.db.conn.execute("UPDATE refunds SET pending_cents=pending_cents-?,refunded_cents=refunded_cents+? WHERE id=?", (amount_cents,amount_cents,row["id"]))
            return row["id"]
        return self.run(command_id,"delivery.refunded",dict(order_id=order_id,method=method,amount_cents=amount_cents,from_drawer=bool(from_drawer),reason=reason),perform)

    def redeliver(self,order_id,grant,reason,command_id):
        def perform():
            self.protect(grant,"delivery.redeliver",reason)
            old=self.order(order_id)
            if old.state!="CANCELED" or old.paid_cents:
                raise BusinessError("Resolva cancelamento e reembolso antes de reexpedir.")
            if self.db.conn.execute("SELECT 1 FROM delivery_orders WHERE previous_order_id=?", (order_id,)).fetchone():
                raise BusinessError("Já existe uma nova tentativa vinculada.")
            items=self.sales.lines(order_id)
            sale=self.db.conn.execute("SELECT id FROM sales WHERE order_id=?", (order_id,)).fetchone()
            if sale:
                for item in items:
                    returned=self.db.conn.execute("SELECT COALESCE(SUM(qty),0) FROM delivery_returns WHERE order_id=? AND product_id=?",(order_id,item["product_id"])).fetchone()[0]
                    if returned!=item["qty"]:
                        raise BusinessError("Confira o retorno de todos os produtos antes de reexpedir.")
            row=self.db.conn.execute("SELECT d.*,o.name FROM delivery_orders d JOIN orders o ON o.id=d.order_id WHERE order_id=?",(order_id,)).fetchone()
            draft=DeliveryDraft(row["name"],row["phone"],row["address"],row["reference"],[CartLine(i["product_id"],i["qty"]) for i in items],row["method"],row["collection"])
            new=self.confirm(draft,command_id+":new")
            self.db.conn.execute("UPDATE delivery_orders SET previous_order_id=? WHERE order_id=?",(order_id,new.id))
            return self.dispatch(new.id,command_id+":dispatch")
        return self.run(command_id,"delivery.redelivered",dict(order_id=order_id,reason=reason),perform)
