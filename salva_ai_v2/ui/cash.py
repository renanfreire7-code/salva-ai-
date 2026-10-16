from tkinter import ttk
from .shared import View, table,fill,ask_fields,command
from ..common.money import parse_money,money


class CashView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text="Caixa",style="Title.TLabel").pack(anchor="w")
        self.summary=ttk.Label(self,text="Caixa fechado",style="Title.TLabel")
        self.summary.pack(anchor="w",pady=10)
        row=ttk.Frame(self);row.pack(fill="x")
        for label,callback in (("Abrir caixa",self.open),("Reforço",lambda:self.move("REINFORCEMENT")),("Retirada",lambda:self.move("WITHDRAWAL"))):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side="left",padx=(0,8))
        self.actions=row
        self.tree=table(self,["Data","Movimento","Valor","Motivo"])

    def open(self):
        values=ask_fields(self,"Abrir caixa",[("opening","Troco inicial (R$)","0,00")])
        if values:
            self.s.cash.open(parse_money(values["opening"]),command())

    def move(self,kind):
        values=ask_fields(self,"Movimentar dinheiro",[("value","Valor (R$)",""),("reason","Motivo","")])
        if values:
            self.s.cash.move(kind,parse_money(values["value"]),values["reason"],self.grant("cash.withdraw" if kind=="WITHDRAWAL" else "cash.reinforce"),command())

    def refresh(self):
        session=self.s.cash.active()
        if session:
            self.summary.configure(text=f'Caixa #{session["id"]} • Esperado na gaveta: {money(self.s.cash.position(session["id"]).expected_cents)}')
            rows=self.s.cash.db.conn.execute("SELECT * FROM cash_entries WHERE session_id=? ORDER BY id DESC",(session["id"],)).fetchall()
            fill(self.tree,[(r["id"],(r["occurred_at"],r["kind"],money(r["delta_cents"]),r["reason"] or "")) for r in rows])
        else:
            self.summary.configure(text="Caixa fechado — abra antes de atender")
            fill(self.tree,[])

