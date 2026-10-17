import tkinter as tk
from tkinter import ttk
from .shared import View,table,fill
from ..common.money import money


class MonthlyView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Resultado do mês',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(self);row.pack(fill='x',pady=10)
        ttk.Label(row,text='Mês (AAAA-MM)').pack(side='left')
        self.month=tk.StringVar(value=self.s.clock.today().strftime('%Y-%m'))
        ttk.Entry(row,textvariable=self.month,width=9).pack(side='left',padx=8)
        ttk.Button(row,text='Consultar',command=lambda:self.act(self.refresh)).pack(side='left')
        ttk.Label(self,text='Estimativa gerencial do resultado. Não representa o dinheiro disponível na gaveta ou no banco.',wraplength=850).pack(anchor='w')
        self.tree=table(self,['Indicador','Valor'])
        self.tree.column('Indicador',width=500,anchor='w')
        self.warnings=ttk.Label(self,text='',wraplength=900);self.warnings.pack(anchor='w',pady=6)

    def refresh(self):
        result=self.s.reports.monthly(self.month.get())
        fields=(('Faturamento de produtos',result.revenue_cents),('Custo dos produtos vendidos',-result.cogs_cents),('Taxas de pagamentos',-result.fees_cents),('Despesas operacionais',-result.operating_cents),('DAS',-result.das_cents),('Resultado dos produtos',result.product_result_cents),('Taxas de entrega cobradas',result.delivery_revenue_cents),('Custo das corridas',-result.delivery_cost_cents),('Resultado gerencial total',result.total_result_cents))
        fill(self.tree,[(i,(label,money(value))) for i,(label,value) in enumerate(fields)])
        self.warnings.configure(text=' '.join(result.warnings))
