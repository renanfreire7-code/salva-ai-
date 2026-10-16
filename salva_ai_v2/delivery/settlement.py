from .models import Settlement
from ..common.service import Service,integer
from ..common.errors import BusinessError


class SettlementService(Service):
    def __init__(self,db,cash,finance,security):
        super().__init__(db,security)
        self.cash,self.finance=cash,finance

    def pending_custody_cents(self):
        return self.db.conn.execute("SELECT COALESCE(SUM(delta_cents),0) FROM custody_entries").fetchone()[0]

    def collections_pending(self):
        return [dict(r) for r in self.db.conn.execute("SELECT * FROM collections WHERE custodian='COURIER' AND method='MONEY' AND amount_cents>settled_cents+courier_refunded_cents")]

    def trips_pending(self):
        return [dict(r) for r in self.db.conn.execute("SELECT t.*,o.id obligation_id,o.amount_cents-COALESCE((SELECT SUM(p.amount_cents) FROM obligation_payments p WHERE p.obligation_id=o.id AND corrected=0),0) pending_cents FROM trips t JOIN obligations o ON o.source_type='TRIP' AND o.source_id=CAST(t.id AS TEXT) WHERE o.deleted_at IS NULL") if r["pending_cents"]>0]

    def _custody(self,delta,kind,source):
        if self.pending_custody_cents()+delta<0:
            raise BusinessError("Valor acima do dinheiro em posse do entregador.")
        self.db.conn.execute("INSERT INTO custody_entries(occurred_at,delta_cents,kind,source) VALUES(?,?,?,?)",
            (self.db.clock.now().isoformat(),delta,kind,source))

    def fund_courier(self,amount_cents,grant,reason,command_id):
        integer(amount_cents,"Troco",1)
        def perform():
            self.protect(grant,"delivery.float",reason)
            transfer=self.db.conn.execute("INSERT INTO courier_floats(amount_cents) VALUES(?)",(amount_cents,)).lastrowid
            self.cash.entry(-amount_cents,"COURIER_FLOAT","float:"+str(transfer),reason)
            self._custody(amount_cents,"FLOAT","float:"+str(transfer))
            return transfer
        return self.run(command_id,"delivery.float",dict(amount_cents=amount_cents,reason=reason),perform)

    def return_float(self,transfer_id,amount_cents,command_id):
        integer(amount_cents,"Troco devolvido",1)
        def perform():
            row=self.one("courier_floats",transfer_id)
            if amount_cents>row["amount_cents"]-row["returned_cents"]:
                raise BusinessError("Troco já devolvido ou valor acima da transferência.")
            self._custody(-amount_cents,"FLOAT_RETURN","float-return:"+command_id)
            self.cash.entry(amount_cents,"FLOAT_RETURN","float-return:"+command_id)
            self.db.conn.execute("UPDATE courier_floats SET returned_cents=returned_cents+? WHERE id=?", (amount_cents,transfer_id))
            return transfer_id
        return self.run(command_id,"delivery.float_returned",dict(transfer_id=transfer_id,amount_cents=amount_cents),perform)

    def settle(self,collection_ids,trip_ids,handed_in_cents,paid_out_cents,offset_cents,grant,command_id):
        for value in (handed_in_cents,paid_out_cents,offset_cents):
            integer(value,"Valor do acerto")
        if not any((handed_in_cents,paid_out_cents,offset_cents)):
            raise BusinessError("Informe os valores do acerto.")
        if len(set(collection_ids))!=len(collection_ids) or len(set(trip_ids))!=len(trip_ids):
            raise BusinessError("Seleção repetida no acerto.")
        def perform():
            self.cash.require_open()
            self.protect(grant,"delivery.settle","Acerto de entregas")
            collections=[]
            for id in collection_ids:
                row=self.one("collections",id)
                if row["method"]!="MONEY" or row["custodian"]!="COURIER":
                    raise BusinessError("Recebimento não está sob custódia do entregador.")
                collections.append(row)
            trips={r["id"]:r for r in self.trips_pending()}
            if any(id not in trips for id in trip_ids):
                raise BusinessError("Corrida já paga ou inválida.")
            available=sum(r["amount_cents"]-r["settled_cents"]-r["courier_refunded_cents"] for r in collections)
            due=sum(trips[id]["pending_cents"] for id in trip_ids)
            if handed_in_cents+offset_cents>available or paid_out_cents+offset_cents>due:
                raise BusinessError("O acerto excede recebimentos ou corridas pendentes.")
            id=self.db.conn.execute("INSERT INTO settlements(occurred_at,handed_in_cents,paid_out_cents,offset_cents) VALUES(?,?,?,?)",
                (self.db.clock.now().isoformat(),handed_in_cents,paid_out_cents,offset_cents)).lastrowid
            self._custody(-handed_in_cents-offset_cents,"SETTLEMENT","settlement:"+str(id))
            if handed_in_cents:
                self.cash.entry(handed_in_cents,"COURIER_HAND_IN","settlement-in:"+str(id))
            cash_entry=self.cash.entry(-paid_out_cents,"COURIER_PAYMENT","settlement-out:"+str(id)) if paid_out_cents else None
            remaining=handed_in_cents+offset_cents
            for row in collections:
                amount=min(remaining,row["amount_cents"]-row["settled_cents"]-row["courier_refunded_cents"])
                if amount:
                    self.db.conn.execute("UPDATE collections SET settled_cents=settled_cents+? WHERE id=?", (amount,row["id"]))
                    self.db.conn.execute("INSERT INTO settlement_items(settlement_id,source_type,source_id,amount_cents) VALUES(?,?,?,?)",(id,"COLLECTION",row["id"],amount))
                    remaining-=amount
            offset_left=offset_cents
            paid_left=paid_out_cents
            for trip_id in trip_ids:
                row=trips[trip_id]
                offset=min(offset_left,row["pending_cents"])
                payout=min(paid_left,row["pending_cents"]-offset)
                for amount,from_drawer in ((offset,False),(payout,True)):
                    if amount:
                        self.db.conn.execute("INSERT INTO obligation_payments(obligation_id,amount_cents,paid_on,method,from_drawer,cash_entry_id) VALUES(?,?,?,'MONEY',?,?)",
                            (row["obligation_id"],amount,self.db.clock.today().isoformat(),from_drawer,cash_entry if from_drawer else None))
                if offset+payout:
                    self.db.conn.execute("INSERT INTO settlement_items(settlement_id,source_type,source_id,amount_cents) VALUES(?,?,?,?)",(id,"TRIP",trip_id,offset+payout))
                offset_left-=offset;paid_left-=payout
            return dict(id=id,handed_in_cents=handed_in_cents,paid_out_cents=paid_out_cents,offset_cents=offset_cents)
        return Settlement(**self.run(command_id,"delivery.settled",dict(collection_ids=collection_ids,trip_ids=trip_ids,handed_in_cents=handed_in_cents,paid_out_cents=paid_out_cents,offset_cents=offset_cents),perform))

