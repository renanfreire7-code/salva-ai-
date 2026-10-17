from ..common.service import integer, valid_date
from ..common.errors import BusinessError


class PaymentsMixin:
    def payment_history(self, obligation_id):
        self.one('obligations',obligation_id)
        return [dict(r) for r in self.db.conn.execute('SELECT * FROM obligation_payments WHERE obligation_id=? ORDER BY id',(obligation_id,))]

    def edit_payment_details(self, payment_id, paid_on, method, grant, reason, command_id):
        paid_on=valid_date(paid_on)
        if paid_on>self.clock.today().isoformat() or method not in ('MONEY','PIX','DEBIT','CREDIT'):
            raise BusinessError('Confira a data e a modalidade do pagamento.')
        def perform():
            self.protect(grant,'payment.edit',reason)
            old=self.one('obligation_payments',payment_id)
            obligation=self.one('obligations',old['obligation_id'])
            credit=self.db.conn.execute('SELECT 1 FROM supplier_credit_settlements WHERE payment_id=?',(payment_id,)).fetchone()
            if old['corrected'] or obligation['source_type']=='TRIP' or credit or (obligation['source_type']=='PURCHASE' and obligation['deleted_at']):
                raise BusinessError('Pagamento corrigido ou vinculado a acerto, crédito ou compra revertida. Consulte o processo de origem.')
            if old['from_drawer'] and method!=old['method']:
                raise BusinessError('Corrija primeiro a saída física antes de trocar a modalidade.')
            self.db.conn.execute('UPDATE obligation_payments SET paid_on=?,method=? WHERE id=?',(paid_on,method,payment_id))
            self.audit.record('payment.details_changed',payment_id,dict(old),dict(self.one('obligation_payments',payment_id)),reason)
            return payment_id
        return self.run(command_id,'payment.edit',dict(payment_id=payment_id,paid_on=paid_on,method=method,reason=reason),perform)

    def pay_obligation(self, obligation_id, amount_cents, paid_on, method, from_drawer, grant, command_id):
        integer(amount_cents, 'Valor pago', 1)
        paid_on = valid_date(paid_on)
        if paid_on > self.clock.today().isoformat():
            raise BusinessError('Pagamento não pode ter data futura.')
        if method not in ('MONEY', 'PIX', 'DEBIT', 'CREDIT') or (from_drawer and method != 'MONEY'):
            raise BusinessError('Forma de pagamento incompatível com a gaveta.')
        def perform():
            row = self.one('obligations', obligation_id)
            if row['deleted_at']:
                raise BusinessError('Esta obrigação foi excluída.')
            if amount_cents > row['amount_cents'] - self.paid_cents(obligation_id):
                raise BusinessError('Pagamento acima do valor pendente.')
            entry = None
            if from_drawer:
                reason = f'Pagamento da obrigação #{obligation_id}'
                self.protect(grant, 'cash.withdraw', reason)
                entry = self.cash.entry(-amount_cents, 'OBLIGATION', 'obligation:' + command_id, reason)
            return self.db.conn.execute('INSERT INTO obligation_payments(obligation_id,amount_cents,paid_on,method,from_drawer,cash_entry_id) VALUES(?,?,?,?,?,?)',
                (obligation_id, amount_cents, paid_on, method, bool(from_drawer), entry)).lastrowid
        return self.run(command_id, 'obligation.paid', dict(obligation_id=obligation_id, amount=amount_cents, paid_on=paid_on, method=method, from_drawer=bool(from_drawer)), perform)

    def correct_payment(self, payment_id, action, physical_return_cents, grant, reason, command_id):
        integer(physical_return_cents, 'Devolução física')
        if action != 'VOID':
            raise BusinessError('Correção de pagamento inválida.')
        def perform():
            self.protect(grant, 'payment.correct', reason)
            payment = self.one('obligation_payments', payment_id)
            obligation=self.one('obligations',payment['obligation_id'])
            credit=self.db.conn.execute('SELECT 1 FROM supplier_credit_settlements WHERE payment_id=?',(payment_id,)).fetchone()
            if obligation['source_type']=='TRIP' or credit or (obligation['source_type']=='PURCHASE' and obligation['deleted_at']):
                raise BusinessError('Pagamento vinculado a acerto, crédito ou compra revertida. Consulte o processo de origem.')
            if payment['corrected']:
                raise BusinessError('Pagamento já corrigido.')
            if physical_return_cents > payment['amount_cents'] or (physical_return_cents and not payment['from_drawer']):
                raise BusinessError('Confira o valor efetivamente devolvido à gaveta.')
            if physical_return_cents:
                self.cash.entry(physical_return_cents, 'PAYMENT_RETURN', 'payment-return:' + str(payment_id), reason)
            self.db.conn.execute('UPDATE obligation_payments SET corrected=1 WHERE id=?', (payment_id,))
            self.audit.record('payment.changed', payment_id, dict(payment), {'corrected': True, 'physical_return_cents': physical_return_cents}, reason)
            return self.db.conn.execute('INSERT INTO payment_corrections(payment_id,action,physical_return_cents,reason,occurred_at) VALUES(?,?,?,?,?)',
                (payment_id, action, physical_return_cents, reason, self.clock.now().isoformat())).lastrowid
        return self.run(command_id, 'payment.corrected', dict(payment_id=payment_id, action=action, physical_return_cents=physical_return_cents, reason=reason), perform)
