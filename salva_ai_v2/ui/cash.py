from tkinter import ttk
from .shared import View, table,fill,ask_fields,command,FieldSpec
from ..common.money import parse_money,money


class CashView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Caixa",style="Title.TLabel").pack(anchor="w")
        self.summary=ttk.Label(self,text="Caixa fechado",style="Title.TLabel")
        self.summary.pack(anchor="w",pady=10)
        self.payment_summary=ttk.Label(self,text='',wraplength=950)
        self.payment_summary.pack(anchor='w',pady=(0,8))
        self.custody_summary=ttk.Label(self,text='',wraplength=950)
        self.custody_summary.pack(anchor='w',pady=(0,8))
        row=ttk.Frame(self);row.pack(fill="x")
        for label,callback in (("Abrir caixa",self.open),("Reforço",lambda:self.move("REINFORCEMENT")),("Retirada",lambda:self.move("WITHDRAWAL"))):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,8))
        self.actions=row
        for label,callback in (("Fechar caixa",self.close_session),("Retomar fechamento",self.resume_close),("Último relatório",self.last_report)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side='left',padx=(0,8))
        self.tree=table(self,["Data","Movimento","Valor","Motivo"])

    def open(self):
        cmd=command()
        return ask_fields(self,'Abrir caixa',[FieldSpec('opening','Troco inicial (R$)','0,00',validator=parse_money)],on_submit=lambda values:self.s.cash.open(parse_money(values['opening']),cmd))

    def move(self,kind):
        cmd=command()
        return ask_fields(self,'Retirar dinheiro' if kind=='WITHDRAWAL' else 'Reforçar troco',[
            FieldSpec('value','Valor (R$)',required=True,validator=parse_money),FieldSpec('reason','Motivo',required=True)],
            on_submit=lambda values:self.s.cash.move(kind,parse_money(values['value']),values['reason'],self.grant('cash.withdraw' if kind=='WITHDRAWAL' else 'cash.reinforce'),cmd))

    def refresh(self):
        session=self.s.cash.active()
        if session:
            report=self.s.reports.cash_report(session['id'])
            self.payment_summary.configure(text='Recebido / reembolsado / líquido por modalidade\n'+ '\n'.join(f'{label}: {money(report.receipts.get(method,0))} / {money(report.refunds.get(method,0))} / {money(report.payments.get(method,0))}' for method,label in (('MONEY','Dinheiro'),('PIX','Pix'),('DEBIT','Débito'),('CREDIT','Crédito'))))
            self.custody_summary.configure(text='Dinheiro ainda com entregador: '+money(self.s.settlements.pending_custody_cents())+' · Fundo de troco a devolver: '+money(sum(r['amount_cents']-r['returned_cents'] for r in self.s.settlements.floats_pending())))
            self.summary.configure(text=f'Caixa #{session["id"]} | Esperado na gaveta: {money(self.s.cash.position(session["id"]).expected_cents)}')
            rows=self.s.cash.db.conn.execute("SELECT * FROM cash_entries WHERE session_id=? ORDER BY id DESC",(session["id"],)).fetchall()
            fill(self.tree,[(r["id"],(r["occurred_at"],r["kind"],money(r["delta_cents"]),r["reason"] or "")) for r in rows])
        else:
            self.custody_summary.configure(text='')
            self.payment_summary.configure(text='')
            self.summary.configure(text="Caixa fechado — abra antes de atender")
            fill(self.tree,[])
        if hasattr(self.s,'closing') and self.s.closing.pending():
            self.summary.configure(text='Fechamento pendente — retome antes de abrir ou atender')

    def close_session(self):
        session=self.s.cash.require_open()
        cmd=command();authorization=[None,None]
        def submit(values):
            counted=parse_money(values['counted'])
            different=counted!=self.s.cash.position(session['id']).expected_cents
            if different and authorization[0] is None:authorization[:]=[self.grant('cash.close'),self.reason()]
            result=self.s.closing.begin(counted,authorization[0],authorization[1],cmd)
            self.s.application.notify('Caixa fechado com relatório e backup verificado.' + (' Cópia externa indisponível.' if result.external_copy_ok is False else ''))
            return result
        return ask_fields(self,'Conferir fechamento',[FieldSpec('counted','Dinheiro contado na gaveta (R$)',required=True,validator=parse_money)],on_submit=submit)

    def resume_close(self):
        for id in self.s.closing.pending():
            self.s.closing.resume(id)
        self.s.application.notify('Recuperação do fechamento concluída.')

    def last_report(self):
        import webbrowser
        paths=sorted(self.s.closing.report_dir.glob('caixa_*.html'),key=lambda p:p.stat().st_mtime,reverse=True)
        if not paths:
            from ..common.errors import BusinessError
            raise BusinessError('Nenhum relatório de fechamento foi gerado.')
        webbrowser.open(paths[0].resolve().as_uri())
