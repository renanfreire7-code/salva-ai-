from ..common.service import integer,valid_date
from ..common.errors import BusinessError


class PurchasesMixin:
    def purchases(self):
        return [dict(r) for r in self.db.conn.execute("SELECT b.*,o.id obligation_id,COALESCE((SELECT SUM(p.amount_cents) FROM obligation_payments p WHERE p.obligation_id=o.id AND p.corrected=0),0) paid_cents FROM purchases b JOIN obligations o ON o.source_type='PURCHASE' AND o.source_id=CAST(b.id AS TEXT) ORDER BY b.id DESC")]

    def purchase_lines(self,purchase_id):
        self.one('purchases',purchase_id)
        return [dict(r) for r in self.db.conn.execute('SELECT i.*,p.name FROM purchase_items i JOIN products p ON p.id=i.product_id WHERE purchase_id=? ORDER BY i.id',(purchase_id,))]

    def supplier_credits(self):
        return [dict(r) for r in self.db.conn.execute('SELECT *,amount_cents-received_cents pending_cents FROM supplier_credits ORDER BY id DESC')]

    def settle_supplier_credit(self,credit_id,amount_cents,mode,method,from_drawer,paid_on,grant,reason,command_id):
        integer(amount_cents,'Valor',1)
        paid_on=valid_date(paid_on)
        if paid_on>self.db.clock.today().isoformat():
            raise BusinessError('A confirmação não pode ter data futura.')
        if mode not in ('RECEIPT','OFFSET') or (mode=='OFFSET' and (method is not None or from_drawer)) or (mode=='RECEIPT' and (method not in ('MONEY','PIX','DEBIT','CREDIT') or (from_drawer and method!='MONEY'))):
            raise BusinessError('Confira a forma de recebimento ou abatimento do crédito.')
        def perform():
            self.protect(grant,'purchase.credit.settle',reason)
            credit=self.one('supplier_credits',credit_id)
            if amount_cents>credit['amount_cents']-credit['received_cents']:
                raise BusinessError('Valor acima do crédito pendente.')
            finance=getattr(self,'finance',None)
            if finance is None:
                raise BusinessError('Financeiro ainda não configurado.')
            payment=cash_entry=None
            if mode=='OFFSET':
                obligation=self.db.conn.execute("SELECT * FROM obligations WHERE source_type='PURCHASE' AND source_id=? AND deleted_at IS NULL",(str(credit['purchase_id']),)).fetchone()
                if not obligation or amount_cents>obligation['amount_cents']-finance.paid_cents(obligation['id']):
                    raise BusinessError('Abata somente o saldo pendente da compra de origem. Para compra revertida, confirme devolução de dinheiro.')
                payment=self.db.conn.execute("INSERT INTO obligation_payments(obligation_id,amount_cents,paid_on,method,from_drawer) VALUES(?,?,?,'SUPPLIER_CREDIT',0)",(obligation['id'],amount_cents,paid_on)).lastrowid
            elif from_drawer:
                cash_entry=finance.cash.entry(amount_cents,'SUPPLIER_REFUND','supplier-credit:'+command_id,reason)
            settlement=self.db.conn.execute('INSERT INTO supplier_credit_settlements(credit_id,amount_cents,mode,method,paid_on,payment_id,cash_entry_id) VALUES(?,?,?,?,?,?,?)',
                (credit_id,amount_cents,mode,method,paid_on,payment,cash_entry)).lastrowid
            self.db.conn.execute('UPDATE supplier_credits SET received_cents=received_cents+? WHERE id=?',(amount_cents,credit_id))
            return settlement
        return self.run(command_id,'purchase.credit_settled',dict(credit_id=credit_id,amount_cents=amount_cents,mode=mode,method=method,from_drawer=bool(from_drawer),paid_on=paid_on,reason=reason),perform)
