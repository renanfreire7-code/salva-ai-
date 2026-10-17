import tkinter as tk
from tkinter import ttk,messagebox
from .shared import View,table,fill,ask_fields,command
from .finance import date_input
from ..finance.queries import month_range
from ..reporting.models import HistoryFilter
from ..sales.models import Payment


class HistoryView(View):
    def __init__(self,parent,services):
        super().__init__(parent,services)
        ttk.Label(self,text='Histórico e correções',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(self);row.pack(fill='x',pady=8)
        start,end=month_range(self.s.clock.today().strftime('%Y-%m'))
        self.start=tk.StringVar(value=start.strftime('%d/%m/%Y'));self.end=tk.StringVar(value=end.strftime('%d/%m/%Y'))
        self.object_id=tk.StringVar()
        for label,var in (('De',self.start),('Até',self.end),('ID do registro',self.object_id)):
            ttk.Label(row,text=label).pack(side='left');ttk.Entry(row,textvariable=var,width=12).pack(side='left',padx=6)
        ttk.Button(row,text='Consultar',command=lambda:self.act(self.refresh)).pack(side='left',padx=6)
        row=ttk.Frame(self);row.pack(fill='x',pady=(0,6))
        ttk.Button(row,text='Corrigir venda / reabrir comanda',command=lambda:self.act(self.reverse)).pack(side='left',padx=6)
        ttk.Button(row,text='Concluir reembolso',command=lambda:self.act(self.finish_refund)).pack(side='left',padx=6)
        self.actions=row
        ttk.Button(row,text='Backups',command=lambda:self.act(self.backup_center)).pack(side='left',padx=6)
        self.tree=table(self,['Data','Operação','Registro','Detalhes / motivo'])
        self.tree.column('Detalhes / motivo',width=550,anchor='w')

    def refresh(self):
        filters=HistoryFilter(date_input(self.start.get()),date_input(self.end.get()),self.object_id.get().strip() or None)
        fill(self.tree,[(r.id,(r.occurred_at.strftime('%d/%m/%Y %H:%M'),r.kind,r.object_id,r.description)) for r in self.s.reports.history(filters)])

    def reverse(self):
        from ..common.money import parse_money
        values=ask_fields(self,'Corrigir venda',[('sale','Número da venda',''),('returned','Mercadoria retornou? sim/não','não'),('refund','Reembolso confirmado? sim/não','não'),('method','Dinheiro / Pix / Débito / Crédito','Dinheiro'),('amount','Valor devolvido em dinheiro (R$)','0,00'),('reopen','Reabrir comanda? sim/não','não')])
        if values:
            methods={'dinheiro':'MONEY','pix':'PIX','débito':'DEBIT','debito':'DEBIT','crédito':'CREDIT','credito':'CREDIT'}
            method=methods.get(values['method'].casefold())
            refund=Payment(method,parse_money(values['amount']) if method=='MONEY' else None) if values['refund'].casefold()=='sim' else None
            self.s.sales.reverse_sale(int(values['sale']),values['returned'].casefold()=='sim',refund,values['reopen'].casefold()=='sim',self.grant('sale.reverse'),self.reason(),command())

    def backup_center(self):
        from tkinter import filedialog
        from pathlib import Path
        window=tk.Toplevel(self);window.title('Backups e recuperação');window.geometry('880x480')
        root=View(window,self.s);root.pack(fill='both',expand=True)
        ttk.Label(root,text='Restauração substitui os dados atuais. Uma cópia do banco atual será preservada. Backups podem conter um PIN anterior.',wraplength=800).pack(anchor='w',pady=8)
        tree=table(root,['Arquivo','Integridade'],height=10)
        paths={}
        def refresh():
            paths.clear()
            paths.update({i:p for i,p in enumerate(self.s.backups.list_backups())})
            fill(tree,[(i,(p.name,'Não verificada nesta consulta')) for i,p in paths.items()])
        def manual():
            info=self.s.backups.create('manual',command())
            self.s.application.notify('Backup local verificado.'+(' Cópia externa indisponível.' if info.external_copy_ok is False else ''))
            refresh()
        def verify():
            id=root.selected(tree);info=self.s.backups.verify(paths[id])
            tree.item(str(id),values=(info.path.name,'Integridade OK'))
        def external():
            path=filedialog.askdirectory(parent=window,title='Pasta adicional para backups')
            if path:
                self.s.backups.set_external_dir(Path(path),self.grant('backup.configure'),command())
                self.s.application.notify('Destino externo configurado. A próxima cópia informará o resultado.')
        def restore():
            path=filedialog.askopenfilename(parent=window,title='Escolher backup para restaurar',filetypes=[('Backup SQLite','*.sqlite3')])
            if not path:
                return
            preview=self.s.restore.prepare(Path(path),self.grant('backup.restore'))
            confirmed=messagebox.askyesno('Confirmar substituição',f'Backup: {preview.source.name}\nVersão de estrutura: {preview.schema_version}\n\nSubstituir os dados atuais?\nO aplicativo será fechado após a restauração.',parent=window)
            self.s.restore.apply(preview,confirmed)
            if confirmed:
                messagebox.showinfo('Restauração concluída','A cópia anterior foi preservada. Abra o aplicativo novamente. O PIN será o existente no backup.',parent=window)
                self.s.application.close()
        row=ttk.Frame(root);row.pack(fill='x',pady=6)
        for label,callback in (('Criar backup',manual),('Verificar selecionado',verify),('Pasta adicional',external),('Restaurar arquivo',restore),('Recuperar PIN',self.s.application.admin.recover)):
            ttk.Button(row,text=label,command=lambda f=callback:root.act(f)).pack(side='left',padx=4)
        refresh()

    def finish_refund(self):
        from ..common.money import parse_money
        values=ask_fields(self,'Confirmar reembolso realizado',[('sale','Número da venda',''),('method','Dinheiro / Pix / Débito / Crédito','Dinheiro'),('amount','Valor devolvido em dinheiro (R$)','0,00')])
        if values:
            methods={'dinheiro':'MONEY','pix':'PIX','débito':'DEBIT','debito':'DEBIT','crédito':'CREDIT','credito':'CREDIT'}
            method=methods.get(values['method'].casefold())
            self.s.sales.confirm_refund(int(values['sale']),Payment(method,parse_money(values['amount']) if method=='MONEY' else None),self.grant('sale.refund'),self.reason(),command())
