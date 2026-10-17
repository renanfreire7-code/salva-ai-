from dataclasses import dataclass
from datetime import date,datetime,timedelta
import tkinter as tk
from tkinter import ttk
from ..common.errors import BusinessError
from ..finance.queries import month_range


def parse_date(value):
    try:
        return datetime.strptime(value,'%d/%m/%Y').date()
    except ValueError:
        try:return date.fromisoformat(value)
        except ValueError:raise BusinessError('Data inválida. Use DD/MM/AAAA.') from None


@dataclass(frozen=True)
class PeriodSelection:
    start: date
    end: date


PRESETS={'TODAY':'Hoje','LAST_7_DAYS':'Últimos 7 dias','THIS_MONTH':'Este mês','CUSTOM':'Personalizado'}


class PeriodFilter(ttk.Frame):
    def __init__(self,parent,clock,default_preset,on_apply,on_clear=None):
        super().__init__(parent)
        self.clock=clock;self.default_preset=default_preset;self.on_apply=on_apply;self.on_clear=on_clear
        self.start=tk.StringVar();self.end=tk.StringVar();self.preset=tk.StringVar(value=PRESETS[default_preset])
        self.error=tk.StringVar();self.description=tk.StringVar()
        row=ttk.Frame(self);row.pack(fill='x',pady=4)
        combo=ttk.Combobox(row,textvariable=self.preset,values=tuple(PRESETS.values()),state='readonly',width=17)
        combo.pack(side='left',padx=(0,8));combo.bind('<<ComboboxSelected>>',lambda event:self.choose_preset())
        for label,var in (('De',self.start),('Até',self.end)):
            ttk.Label(row,text=label).pack(side='left');ttk.Entry(row,textvariable=var,width=11).pack(side='left',padx=6)
        ttk.Button(row,text='Filtrar',command=self.apply).pack(side='left',padx=6)
        ttk.Button(row,text='Limpar filtros',command=self.clear).pack(side='left')
        ttk.Label(self,textvariable=self.description,style='Muted.TLabel').pack(anchor='w')
        ttk.Label(self,textvariable=self.error,foreground='#a52525',wraplength=900).pack(anchor='w')
        self.choose_preset();self.applied=self.selection();self.describe()

    def choose_preset(self):
        today=self.clock.today();choice=self.preset.get()
        if choice=='Personalizado':return
        start,end=(today,today) if choice=='Hoje' else (today-timedelta(days=6),today) if choice=='Últimos 7 dias' else month_range(today.strftime('%Y-%m'))
        self.start.set(start.strftime('%d/%m/%Y'));self.end.set(end.strftime('%d/%m/%Y'))

    def selection(self):
        start,end=parse_date(self.start.get()),parse_date(self.end.get())
        if start>end:raise BusinessError('O início deve ser anterior ao fim do período.')
        return PeriodSelection(start,end)

    def describe(self):
        self.description.set(f"Período aplicado: {self.applied.start.strftime('%d/%m/%Y')} a {self.applied.end.strftime('%d/%m/%Y')}")

    def apply(self):
        try:
            selection=self.selection()
            self.on_apply(selection)
        except (BusinessError,ValueError) as error:
            self.error.set(str(error));return False
        self.applied=selection;self.error.set('');self.describe();return True

    def clear(self):
        self.preset.set(PRESETS[self.default_preset]);self.choose_preset()
        if self.on_clear:self.on_clear()
        return self.apply()


class MonthSelector(ttk.Frame):
    def __init__(self,parent,clock,on_apply):
        super().__init__(parent);self.on_apply=on_apply
        self.applied=clock.today().strftime('%Y-%m');self.value=tk.StringVar(value=self.applied)
        self.error=tk.StringVar();self.description=tk.StringVar(value='Mês aplicado: '+self.applied)
        row=ttk.Frame(self);row.pack(fill='x',pady=6)
        ttk.Label(row,text='Mês (AAAA-MM)').pack(side='left',padx=(0,8))
        today=clock.today();values=[f'{year:04d}-{month:02d}' for year in range(today.year-2,today.year+2) for month in range(1,13)]
        ttk.Combobox(row,textvariable=self.value,values=values,width=10).pack(side='left',padx=(0,8))
        ttk.Button(row,text='Consultar',command=self.apply).pack(side='left')
        ttk.Label(row,textvariable=self.description,style='Muted.TLabel').pack(side='left',padx=16)
        ttk.Label(self,textvariable=self.error,foreground='#a52525').pack(anchor='w')

    def apply(self):
        try:
            value=self.value.get();month_range(value);self.on_apply(value)
        except (BusinessError,ValueError) as error:
            self.error.set(str(error));return False
        self.applied=value;self.error.set('');self.description.set('Mês aplicado: '+value);return True
