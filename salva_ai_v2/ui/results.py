import tkinter as tk
from tkinter import ttk,filedialog
from decimal import Decimal
from .shared import View,table,fill,ask_fields,command
from ..common.money import money,parse_money
from ..common.errors import BusinessError
from .period import MonthSelector


class ResultsView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Lucro por produto',style='Title.TLabel').pack(anchor='w')
        self.selector=MonthSelector(self,self.s.clock,lambda month:self.refresh(month));self.selector.pack(fill='x',pady=4)
        self.month=self.selector.value
        row=ttk.Frame(self);row.pack(fill='x',pady=8)
        for label,callback in (('Exportar Excel',self.export),('Taxas e DAS',self.configure)):
            ttk.Button(row,text=label,command=lambda f=callback:self.act(f)).pack(side='left',padx=4)
        self.summary=ttk.Label(self,text='',wraplength=1060,justify='left');self.summary.pack(anchor='w',pady=8)
        ttk.Label(self,text='Margem de contribuição = venda - custo - taxas. Resultado por produto inclui rateio das despesas e DAS. Não é saldo bancário.',wraplength=1050).pack(anchor='w')
        self.tree=table(self,['Produto','Quantidade','Faturamento','CMV','Taxas','Contribuição','Rateio','Resultado','Margem'])

    def refresh(self,month=None):
        month=month or self.selector.applied
        summary=self.s.reports.monthly(month)
        self.summary.configure(text=f'Produtos: {money(summary.revenue_cents)} - custos {money(summary.cogs_cents)} - taxas e despesas = resultado {money(summary.product_result_cents)}\n'
            f'Entregas: receita {money(summary.delivery_revenue_cents)} • custo de corridas {money(summary.delivery_cost_cents)}\n'
            f'Resultado gerencial total: {money(summary.total_result_cents)}\n'+' '.join(summary.warnings))
        fill(self.tree,[(r.product_id,(r.name,r.qty,money(r.revenue_cents),money(r.cogs_cents),money(r.fees_cents),money(r.contribution_cents),money(r.allocated_cents),money(r.profit_cents),f'{r.margin}%' if r.margin is not None else '—')) for r in self.s.reports.profitability(month)])

    def export(self):
        from ..reporting.xlsx import export_xlsx
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.xlsx',initialfile='Bar_Simples_'+self.selector.applied+'.xlsx',filetypes=[('Excel','*.xlsx')])
        if path:
            export_xlsx(path,self.s.reports.bundle(self.selector.applied))
            self.s.application.notify('Relatório Excel salvo.')

    def configure(self):
        rates=self.s.settings.rates()
        das=self.s.settings.das()
        cmd=command()
        def submit(values):
            parsed={'MONEY':0}
            for key in ('PIX','DEBIT','CREDIT'):
                if not values[key]:
                    parsed[key]=None
                else:
                    amount=Decimal(values[key].replace(',','.'))*100
                    if not amount.is_finite() or amount!=amount.to_integral_value() or not 0<=amount<=10000:
                        raise BusinessError('Taxa inválida; use até duas casas decimais e valor entre 0 e 100%.')
                    parsed[key]=int(amount)
            reason=self.reason()
            return self.s.settings.configure(parsed,parse_money(values['das']) if values['das'] else None,self.grant('settings.finance'),reason,cmd)
        return ask_fields(self,'Taxas confirmadas e provisão de DAS',[(key,label,'' if rates[key] is None else str(Decimal(rates[key])/100).replace('.',',')) for key,label in (('PIX','Taxa Pix (%)'),('DEBIT','Taxa débito (%)'),('CREDIT','Taxa crédito à vista (%)'))]+[('das','DAS mensal (R$); vazio se desconhecido',money(das).replace('R$ ','') if das is not None else '')],on_submit=submit)



class ReplenishmentView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Previsão de compras',style='Title.TLabel').pack(anchor='w')
        ttk.Label(self,text='Sugestão pelo disponível e estoque mínimo. Não registra compra nem pagamento. Custo estimado; confirme com o fornecedor.',wraplength=1050).pack(anchor='w',pady=8)
        self.tree=table(self,['Produto','Disponível','Faltam unidades','Caixas/fardos','Custo estimado'])

    def refresh(self):
        fill(self.tree,[(r.product_id,(r.name,r.available,r.needed_units,r.packs,money(r.estimated_cents) if r.estimated_cents else 'Custo não informado')) for r in self.s.reports.replenishment()])
