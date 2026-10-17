from ..common.service import Service,integer
from ..common.errors import BusinessError


class FinancialSettings(Service):
    def das(self):
        row=self.db.conn.execute("SELECT value_cents FROM financial_settings WHERE key='DAS'").fetchone()
        return row[0] if row else None

    def configure(self,rates,das_cents,grant,reason,command_id):
        if set(rates)!={'MONEY','PIX','DEBIT','CREDIT'} or rates['MONEY']!=0:
            raise BusinessError('Informe as quatro taxas; dinheiro deve ter taxa zero.')
        for value in rates.values():
            if value is not None:
                integer(value,'Taxa em pontos-base')
                if value>10000:
                    raise BusinessError('Taxa acima de 100%.')
        if das_cents is not None:
            integer(das_cents,'DAS')
        def perform():
            self.protect(grant,'settings.finance',reason)
            for method,rate in rates.items():
                self.db.conn.execute('UPDATE payment_settings SET rate_bp=? WHERE method=?',(rate,method))
            self.db.conn.execute("INSERT INTO financial_settings VALUES('DAS',?) ON CONFLICT(key) DO UPDATE SET value_cents=excluded.value_cents",(das_cents,))
            return 1
        return self.run(command_id,'settings.configured',dict(rates=rates,das_cents=das_cents,reason=reason),perform)

    def set_das(self,amount_cents,grant,reason,command_id):
        if amount_cents is not None:
            integer(amount_cents,"DAS")
        def perform():
            self.protect(grant,"settings.finance",reason)
            self.db.conn.execute("INSERT INTO financial_settings VALUES('DAS',?) ON CONFLICT(key) DO UPDATE SET value_cents=excluded.value_cents",(amount_cents,))
            return 1
        return self.run(command_id,"settings.das",dict(amount_cents=amount_cents,reason=reason),perform)

    def rates(self):
        return dict(self.db.conn.execute("SELECT method,rate_bp FROM payment_settings"))

    def set_rates(self,rates,grant,reason,command_id):
        if set(rates)!={"MONEY","PIX","DEBIT","CREDIT"} or rates["MONEY"]!=0:
            raise BusinessError("Informe as quatro taxas; dinheiro deve ter taxa zero.")
        for value in rates.values():
            if value is not None:
                integer(value,"Taxa em pontos-base")
                if value>10000:
                    raise BusinessError("Taxa acima de 100%.")
        def perform():
            self.protect(grant,"settings.finance",reason)
            for method,rate in rates.items():
                self.db.conn.execute("UPDATE payment_settings SET rate_bp=? WHERE method=?",(rate,method))
            return 1
        return self.run(command_id,"settings.rates",dict(rates=rates,reason=reason),perform)
