import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from datetime import datetime
import os
import subprocess
import sys
from core import Store, BusinessError, money, parse_qty
from reports import export as export_xlsx
from finance import (backup_before_upgrade, migrate, add_expense, set_paid, set_product_cost, reopen_paid_tab,
                     month_summary, replenish, profitability, get_payment_rates,
                     get_setting, update_settings, CATEGORIES, PAYMENTS)

ROOT=Path.home()/'SalvaAiHeadshop'
# Aberto em main(); importar este módulo (ex.: nos testes) não toca no banco real.
STORE=None
PAYMENTS=('Dinheiro','Pix','Débito','Crédito')
NUMERIC_COLUMNS={'ID','Item ID','Comanda','Venda nº','COMANDA Nº','Caixa','Preço','Preço unit.','Estoque físico','Reservado',
    'Disponível','Un./caixa','Qtd.','Total','Subtotal','Vendas','Valor','Variação','CMV','Taxas','Contribuição',
    'Rateio fixos + DAS','Lucro estimado','Margem','Mínimo','Caixas sugeridas','Unidades','Custo estimado'}

# Tokens de design. Cores originais do protótipo, agora nomeadas por função (HIG > Color:
# não usar a mesma cor com significados diferentes). Todos os pares texto/fundo têm
# contraste >= 4,5:1 (WCAG AA, referência do HIG > Accessibility).
COLORS=dict(bg='#f3f6fa',surface='#ffffff',text='#182b42',secondary='#526984',brand='#195b9a',
    accent='#2269b6',accent_pressed='#15538f',accent_disabled='#a9bdd6',
    destructive='#b3261e',destructive_pressed='#8c1d18',success='#1e7a3c',
    tab='#e2eaf2',tab_selected='#165db1',heading='#e6eef7',heading_text='#213f61')

def setup_fonts(root):
    """Fonte do sistema em cada plataforma (HIG > Typography) e uma escala única de estilos.
    No Windows mantém Segoe UI 10, exatamente como no protótipo original."""
    from tkinter import font
    if sys.platform.startswith('win'): family,base='Segoe UI',10
    else: family,base=font.nametofont('TkDefaultFont').actual('family'),13 if sys.platform=='darwin' else 10
    styles={'body':(base,'normal'),'emphasis':(base,'bold'),'headline':(base+1,'bold'),
            'title':(base+3,'bold'),'large_title':(base+8,'bold')}
    return {name:font.Font(root,family=family,size=size,weight=weight) for name,(size,weight) in styles.items()}

def open_folder(folder):
    """Abre a pasta no gerenciador de arquivos do sistema (Windows, macOS ou Linux)."""
    if sys.platform.startswith('win'): os.startfile(str(folder))
    elif sys.platform=='darwin': subprocess.run(['open',str(folder)],check=True)
    else: subprocess.run(['xdg-open',str(folder)],check=True)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Salva ai headshop • Protótipo 0.3.4-beta (offline)')
        self.geometry('1180x780'); self.minsize(960,670)
        self.configure(bg=COLORS['bg'])
        self.fonts=f=setup_fonts(self); c=COLORS
        style=ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('.',font=f['body'],background=c['bg'],foreground=c['text'])
        style.configure('TFrame',background=c['bg'])
        style.configure('TLabel',background=c['bg'],foreground=c['text'])
        style.configure('Title.TLabel',font=f['title'])
        style.configure('Headline.TLabel',font=f['headline'])
        style.configure('Secondary.TLabel',foreground=c['secondary'])
        style.configure('Status.TLabel',foreground=c['secondary'],padding=(18,0))
        style.configure('TButton',padding=(13,10),font=f['emphasis'])
        style.map('TButton',foreground=[('disabled',c['secondary'])])
        style.configure('TNotebook',background=c['bg'],borderwidth=0)
        # No Windows mantém o espaçamento original; nas outras plataformas a fonte do sistema é maior,
        # então as 8 abas usam menos padding lateral para continuarem visíveis na largura padrão.
        style.configure('TNotebook.Tab',padding=(18 if sys.platform.startswith('win') else 10,11),font=f['emphasis'],background=c['tab'])
        style.map('TNotebook.Tab',background=[('selected',c['surface'])],foreground=[('selected',c['tab_selected'])])
        # Altura da linha acompanha a fonte, para não cortar texto em fontes maiores (macOS).
        style.configure('Treeview',font=f['body'],rowheight=f['body'].metrics('linespace')+12,background=c['surface'],fieldbackground=c['surface'])
        style.configure('Treeview.Heading',font=f['emphasis'],background=c['heading'],foreground=c['heading_text'])
        style.configure('TEntry',padding=5)
        style.configure('TCombobox',padding=5)
        # Botão principal (HIG > Buttons: no máximo 1–2 destacados por tela, com estado pressionado e desativado).
        style.configure('Accent.TButton',background=c['accent'],foreground='#ffffff',padding=(15,11))
        style.map('Accent.TButton',background=[('disabled',c['accent_disabled']),('pressed',c['accent_pressed']),('active',c['accent_pressed'])],
                  foreground=[('disabled','#ffffff')])
        # Ação destrutiva usa vermelho e nunca é o botão principal (HIG > Buttons > Role).
        style.configure('Destructive.TButton',foreground=c['destructive'])
        style.map('Destructive.TButton',foreground=[('pressed',c['destructive_pressed']),('active',c['destructive_pressed'])])
        header=ttk.Frame(self,padding=(18,12));header.pack(fill='x')
        ttk.Label(header,text='SALVA AI HEADSHOP',font=f['large_title'],foreground=c['brand']).pack(side='left')
        ttk.Label(header,text='  •  Gestão offline   |   Protótipo 0.3.4-beta',style='Secondary.TLabel').pack(side='left')
        # Situação do caixa sempre visível, em texto (não só cor) — HIG > Feedback.
        self.header_cash=ttk.Label(header,text='',font=f['emphasis']); self.header_cash.pack(side='right')
        # Status da última ação: confirma o que foi feito sem interromper com alertas (HIG > Feedback, Alerts).
        # Fica na linha do cabeçalho para não roubar altura das abas em telas pequenas.
        self.status_var=tk.StringVar(value='Pronto.')
        ttk.Label(header,textvariable=self.status_var,style='Status.TLabel',anchor='e').pack(side='right',fill='x',expand=True)
        self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=12,pady=12)
        self.p_products=ttk.Frame(self.tabs,padding=12); self.p_tabs=ttk.Frame(self.tabs,padding=12)
        self.p_direct=ttk.Frame(self.tabs,padding=12); self.p_cash=ttk.Frame(self.tabs,padding=12); self.p_history=ttk.Frame(self.tabs,padding=12); self.p_finance=ttk.Frame(self.tabs,padding=12); self.p_profit=ttk.Frame(self.tabs,padding=12); self.p_replenish=ttk.Frame(self.tabs,padding=12)
        for frame,label in [(self.p_tabs,'Comandas'),(self.p_direct,'Venda direta'),(self.p_products,'Produtos e estoque'),(self.p_cash,'Caixa'),(self.p_history,'Histórico'),(self.p_finance,'Financeiro mensal'),(self.p_profit,'Lucro por produto'),(self.p_replenish,'Previsão de compras')]: self.tabs.add(frame,text=label)
        self.build_products(); self.build_tabs(); self.build_direct(); self.build_cash(); self.build_history(); self.build_finance(); self.build_profit(); self.build_replenish()
        self.tabs.bind('<<NotebookTabChanged>>',lambda e:self.refresh())
        self.refresh()
        self.protocol('WM_DELETE_WINDOW',self.quit_app)
    def safe(self,fn,done=None):
        """Executa a ação; em caso de sucesso atualiza as telas e mostra `done` na barra de status."""
        try:
            result=fn(); self.refresh()
            if done: self.status(done(result) if callable(done) else done)
        except (BusinessError,ValueError) as e: messagebox.showerror('Não foi possível',str(e),parent=self)
        except Exception as e: messagebox.showerror('Erro inesperado',str(e),parent=self)
    def status(self,text):
        self.status_var.set(f"{datetime.now().strftime('%H:%M')}  {text}")
    def on_return(self,widgets,action):
        """Return executa a ação principal da linha (HIG > Buttons > Role: botão primário responde ao Return)."""
        for w in widgets: w.bind('<Return>',lambda e:action())
    def entry(self,parent,label,initial='',width=19):
        f=ttk.Frame(parent); f.pack(side='left',padx=6,pady=5)
        ttk.Label(f,text=label).pack(anchor='w'); e=ttk.Entry(f,width=width); e.insert(0,initial); e.pack(); return e
    def choose(self,parent,label,values,width=27):
        f=ttk.Frame(parent); f.pack(side='left',padx=6,pady=5)
        ttk.Label(f,text=label).pack(anchor='w'); c=ttk.Combobox(f,values=values,width=width,state='readonly');
        if values: c.current(0)
        c.pack(); return c
    def table(self,parent,cols,widths=None,height=11):
        outer=ttk.Frame(parent); outer.pack(fill='both',expand=True,pady=7)
        t=ttk.Treeview(outer,columns=cols,show='headings',height=height,selectmode='browse')
        for idx,c in enumerate(cols):
            # Números alinhados à direita facilitam comparar valores na coluna (HIG > Layout: alinhamento).
            anchor='e' if c in NUMERIC_COLUMNS else 'w'
            t.heading(c,text=c,anchor=anchor); t.column(c,width=(widths[idx] if widths else 120),anchor=anchor)
        sb=ttk.Scrollbar(outer,orient='vertical',command=t.yview);t.configure(yscrollcommand=sb.set)
        t.pack(side='left',fill='both',expand=True);sb.pack(side='right',fill='y');return t
    def fill(self,tree,rows):
        tree.delete(*tree.get_children())
        for key,values in rows: tree.insert('', 'end',iid=str(key),values=values)
    def pid(self,selector):
        label=selector.get()
        if not label: raise BusinessError('Selecione um produto.')
        return int(label.split(' | ',1)[0])
    def selected(self,tree,label):
        selection=tree.selection()
        if not selection: raise BusinessError('Selecione '+label+'.')
        return int(selection[0])
    def build_products(self):
        p=self.p_products
        ttk.Label(p,text='Cadastro (quantidades podem começar em zero)',style='Title.TLabel').pack(anchor='w')
        f=ttk.Frame(p);f.pack(fill='x'); self.newname=self.entry(f,'Produto','',25);self.newprice=self.entry(f,'Preço unitário (R$)','0,00');self.newpack=self.entry(f,'Unidades por caixa/fardo','1',15)
        ttk.Button(f,text='Cadastrar produto',command=self.add_product).pack(side='left',padx=6,pady=20)
        self.on_return([self.newname,self.newprice,self.newpack],self.add_product)
        ttk.Label(p,text='Custos e reposição (selecione um produto na tabela e salve)',style='Headline.TLabel').pack(anchor='w',pady=(7,0))
        f=ttk.Frame(p);f.pack(fill='x');self.productcost=self.entry(f,'Custo de compra / unidade (R$)','0,00');self.min_stock=self.entry(f,'Estoque mínimo (un.)','0',12)
        ttk.Button(f,style='Accent.TButton',text='Salvar custo e estoque mínimo',command=lambda:self.safe(lambda:set_product_cost(STORE,self.selected(self.products_tree,'um produto'),self.productcost.get(),self.min_stock.get()),'Custo e estoque mínimo salvos.')).pack(side='left',padx=6,pady=20)
        self.products_tree=self.table(p,['ID','Produto','Preço','Estoque físico','Reservado','Disponível','Un./caixa'],[45,235,100,110,100,110,100],5)
        ttk.Label(p,text='Movimentar estoque • caixa/fardo é convertida em unidades').pack(anchor='w')
        f=ttk.Frame(p);f.pack(fill='x');self.stockqty=self.entry(f,'Quantidade','1',10)
        self.movetype=self.choose(f,'Tipo de movimentação',['Caixa/Fardo (entrada)','Unidade (entrada)','Unidade (perda/ajuste)'],27)
        self.reason=self.entry(f,'Motivo (opcional)','',24)
        ttk.Button(f,text='Registrar no produto selecionado',command=self.adjust_stock).pack(side='left',padx=6,pady=20)
        self.on_return([self.stockqty,self.reason],self.adjust_stock)
        f=ttk.Frame(p);f.pack(fill='x'); self.editprice=self.entry(f,'Novo preço (R$)','0,00');self.editpack=self.entry(f,'Nova unidade/caixa','1')
        ttk.Button(f,text='Atualizar preço / embalagem',command=lambda:self.safe(lambda:STORE.update_product(self.selected(self.products_tree,'um produto'),self.editprice.get(),self.editpack.get()),'Preço e embalagem atualizados.')).pack(side='left',padx=6,pady=20)
        self.products_tree.bind('<<TreeviewSelect>>',self.selected_product)
    def add_product(self):
        def go():
            name=self.newname.get().strip()
            STORE.add_product(name,self.newprice.get(),self.newpack.get())
            self.newname.delete(0,'end'); self.newname.focus_set()
            return name
        self.safe(go,lambda name:f'Produto “{name}” cadastrado.')
    def adjust_stock(self):
        self.safe(lambda:STORE.adjust_stock(self.selected(self.products_tree,'um produto'),self.stockqty.get(),self.movetype.get(),self.reason.get()),
                  'Movimentação de estoque registrada.')
    def selected_product(self,e=None):
        try:
            p=STORE.product(self.selected(self.products_tree,'produto'))
            for entry,val in [(self.editprice,f"{p['price']/100:.2f}".replace('.',',')),(self.editpack,str(p['pack_size'])),(self.productcost,f"{p['cost']/100:.2f}".replace('.',',')),(self.min_stock,str(p['min_stock']))]: entry.delete(0,'end');entry.insert(0,val)
        except BusinessError: pass
    def build_tabs(self):
        p=self.p_tabs
        # The payment panel is packed first at the bottom; it cannot be pushed off-screen
        # by expanding Treeview widgets on smaller Windows displays.
        bottom=ttk.Frame(p)
        bottom.pack(side='bottom',fill='x',pady=(6,0))
        ttk.Separator(bottom,orient='horizontal').pack(fill='x',pady=(0,5))
        payrow=ttk.Frame(bottom);payrow.pack(fill='x')
        self.tabpayment=self.choose(payrow,'Forma de pagamento',PAYMENTS,13)
        ttk.Button(payrow,style='Accent.TButton',text='Receber e fechar comanda',command=self.confirm_pay).pack(side='left',padx=5,pady=5)
        ttk.Button(payrow,text='Remover item',command=lambda:self.safe(lambda:STORE.remove_tab_item(self.selected(self.tabs_tree,'uma comanda'),self.selected(self.items_tree,'um item')),'Item removido da comanda.')).pack(side='left',padx=5)
        ttk.Button(payrow,style='Destructive.TButton',text='Cancelar comanda',command=self.confirm_cancel).pack(side='left',padx=5)
        correction=ttk.Frame(bottom);correction.pack(fill='x',pady=(2,0))
        ttk.Label(correction,text='Comanda paga por engano? Localize pelo número no Histórico.').pack(side='left',padx=6)
        ttk.Button(correction,text='Ver comandas pagas',command=lambda:self.tabs.select(self.p_history)).pack(side='left',padx=8)
        ttk.Label(p,text='Comandas identificadas pelo nome do cliente',style='Title.TLabel').pack(anchor='w')
        top=ttk.Frame(p);top.pack(fill='x')
        self.customer=self.entry(top,'Nome do cliente','',28)
        ttk.Button(top,style='Accent.TButton',text='Abrir comanda',command=self.open_tab).pack(side='left',padx=6,pady=7)
        self.on_return([self.customer],self.open_tab)
        self.tabs_tree=self.table(p,['Comanda','Cliente','Aberta em','Total'],[80,245,170,140],3)
        self.tabs_tree.bind('<<TreeviewSelect>>',lambda e:self.refresh_tab_items())
        addrow=ttk.Frame(p);addrow.pack(fill='x')
        self.tabproduct=self.choose(addrow,'Produto',[])
        self.tabqty=self.entry(addrow,'Unidades','1',10)
        ttk.Button(addrow,text='Adicionar à comanda selecionada',command=self.add_to_tab).pack(side='left',padx=6,pady=7)
        self.on_return([self.tabqty],self.add_to_tab)
        ttk.Label(p,text='Itens da comanda selecionada (reservados até o pagamento)').pack(anchor='w')
        self.items_tree=self.table(p,['Item ID','Produto','Qtd.','Preço unit.','Subtotal'],[65,230,80,110,130],3)
    def open_tab(self):
        def go():
            tid=STORE.create_tab(self.customer.get())
            self.customer.delete(0,'end')
            return tid
        def done(tid):
            # Já deixa a comanda nova selecionada para adicionar itens em seguida.
            self.tabs_tree.selection_set(str(tid)); self.tabs_tree.see(str(tid)); self.refresh_tab_items()
            return f'Comanda nº {tid} aberta.'
        self.safe(go,done)
    def add_to_tab(self):
        self.safe(lambda:STORE.add_to_tab(self.selected(self.tabs_tree,'uma comanda'),self.pid(self.tabproduct),self.tabqty.get()),
                  'Item adicionado à comanda.')
    def confirm_pay(self):
        def go():
            tid=self.selected(self.tabs_tree,'uma comanda')
            if messagebox.askyesno('Confirmar pagamento',f'Fechar comanda de {money(STORE.tab_total(tid))} em {self.tabpayment.get()}?'):
                STORE.pay_tab(tid,self.tabpayment.get())
                return f'Comanda nº {tid} recebida em {self.tabpayment.get()}.'
        self.safe(go,lambda msg:msg)
    def confirm_cancel(self):
        def go():
            tid=self.selected(self.tabs_tree,'uma comanda')
            if messagebox.askyesno('Cancelar comanda','Cancelar a comanda? As reservas serão liberadas.'):
                STORE.cancel_tab(tid); return f'Comanda nº {tid} cancelada; reservas liberadas.'
        self.safe(go,lambda msg:msg)
    def reopen_selected_sale(self):
        """One-click flow from a clearly identified sale: no manual ID entry."""
        def go():
            sid=self.selected(self.sales_tree,'uma venda no Histórico')
            row=STORE.one("""SELECT s.*,t.customer,t.status tab_status,cs.closed_at cash_closed_at
                FROM sales s LEFT JOIN tabs t ON t.id=s.tab_id
                JOIN cash_sessions cs ON cs.id=s.session_id WHERE s.id=?""",(sid,))
            if not row: raise BusinessError('Venda não encontrada. Atualize o histórico.')
            if row['tab_id'] is None: raise BusinessError('Esta é uma venda direta, sem comanda para reabrir.')
            if row['voided_at']: raise BusinessError('Esta venda já foi estornada; não é possível reabri-la novamente.')
            if row['tab_status']!='PAID': raise BusinessError('A comanda nº '+str(row['tab_id'])+' não está na situação PAGA.')
            session=STORE.active_session()
            if not session or session['id']!=row['session_id'] or row['cash_closed_at']:
                raise BusinessError('A comanda nº '+str(row['tab_id'])+' é do caixa nº '+str(row['session_id'])+'. A reabertura só é permitida com o caixa original ainda aberto. Não alteramos caixas encerrados.')
            reason=simpledialog.askstring('Motivo da correção',f"Comanda nº {row['tab_id']} — {row['customer']} — Venda nº {sid} — {money(row['total'])}\n\nPor que deseja reabrir?",parent=self)
            if reason is None: return
            if len(reason.strip())<5: raise BusinessError('Informe um motivo com pelo menos 5 caracteres.')
            if not messagebox.askyesno('Confirmar reabertura',
                f"Reabrir COMANDA nº {row['tab_id']} (venda nº {sid})?\n\n"
                f"A venda interna de {money(row['total'])} será estornada e os itens ficarão reservados.\n"
                'Isto NÃO cancela nem devolve pagamentos Pix ou cartão.',parent=self): return
            reopen_paid_tab(STORE,row['tab_id'],reason)
            self.tabs.select(self.p_tabs)
            self.refresh()
            if self.tabs_tree.exists(str(row['tab_id'])):
                self.tabs_tree.selection_set(str(row['tab_id']))
                self.tabs_tree.focus(str(row['tab_id']))
                self.refresh_tab_items()
            messagebox.showinfo('Comanda reaberta',f"Comanda nº {row['tab_id']} reaberta. Confira os itens e eventual devolução externa do pagamento.",parent=self)
        self.safe(go)
    def refresh_tab_items(self):
        try: items=STORE.tab_items(self.selected(self.tabs_tree,'uma comanda'))
        except BusinessError: items=[]
        self.fill(self.items_tree,[(x['id'],(x['id'],x['name'],x['qty'],money(x['unit_price']),money(x['qty']*x['unit_price']))) for x in items])
    def build_direct(self):
        p=self.p_direct;ttk.Label(p,text='Venda direta • um produto por operação',style='Title.TLabel').pack(anchor='w',pady=8)
        ttk.Label(p,text='Para vender itens diferentes juntos, use uma comanda e feche-a no mesmo momento.').pack(anchor='w')
        f=ttk.Frame(p);f.pack(anchor='w',pady=15);self.directproduct=self.choose(f,'Produto',[],45);self.directqty=self.entry(f,'Unidades','1',12);self.directpayment=self.choose(f,'Pagamento',PAYMENTS,16)
        self.on_return([self.directqty],self.confirm_direct)
        ttk.Button(p,style='Accent.TButton',text='Registrar venda e baixar estoque',command=self.confirm_direct).pack(anchor='w',pady=12)
    def confirm_direct(self):
        def go():
            pid=self.pid(self.directproduct);qty=parse_qty(self.directqty.get());p=STORE.product(pid)
            if messagebox.askyesno('Confirmar venda',f"Vender {qty} × {p['name']} por {money(qty*p['price'])} em {self.directpayment.get()}?"):
                STORE.direct_sale(pid,qty,self.directpayment.get())
                return f"Venda registrada: {qty} × {p['name']} em {self.directpayment.get()}."
        self.safe(go,lambda msg:msg)
    def build_cash(self):
        p=self.p_cash;ttk.Label(p,text='Abertura e fechamento do caixa',style='Title.TLabel').pack(anchor='w',pady=8)
        self.cash_status=ttk.Label(p,text='');self.cash_status.pack(anchor='w',pady=10)
        f=ttk.Frame(p);f.pack(fill='x');self.opening=self.entry(f,'Troco inicial em dinheiro (R$)','0,00')
        self.open_cash_btn=ttk.Button(f,style='Accent.TButton',text='Abrir caixa',command=self.open_cash); self.open_cash_btn.pack(side='left',pady=20,padx=8)
        self.on_return([self.opening],self.open_cash)
        self.totals_tree=self.table(p,['Forma de pagamento','Vendas','Total'],[240,100,140],5)
        self.cash_total=ttk.Label(p,text='',style='Title.TLabel');self.cash_total.pack(anchor='w',pady=8)
        f=ttk.Frame(p);f.pack(fill='x');self.counted=self.entry(f,'Dinheiro contado ao fechar (R$)','0,00')
        self.close_cash_btn=ttk.Button(f,style='Accent.TButton',text='Fechar caixa + criar backup',command=self.confirm_close); self.close_cash_btn.pack(side='left',pady=20,padx=8)
        ttk.Label(p,text=f'Backups são criados em: {ROOT / "backups"}',wraplength=900).pack(anchor='w',pady=10)
        ttk.Label(p,text='Atenção: o backup fica no mesmo computador. Copie regularmente a pasta de backups para mídia externa.',wraplength=900).pack(anchor='w')
    def open_cash(self):
        if str(self.open_cash_btn['state'])=='disabled': return
        self.safe(lambda:STORE.open_cash(self.opening.get()),'Caixa aberto.')
    def confirm_close(self):
        def go():
            if STORE.open_tabs(): raise BusinessError('Existem comandas abertas. Feche ou cancele todas antes do fechamento do caixa.')
            if messagebox.askyesno('Confirmar fechamento','Fechar caixa e gerar o arquivo de backup?'):
                b=STORE.close_cash(self.counted.get(),ROOT/'backups')
                messagebox.showinfo('Caixa fechado',f'Backup gravado em:\n{b}')
                return 'Caixa fechado e backup gravado.'
        self.safe(go,lambda msg:msg)
    def build_history(self):
        p=self.p_history;ttk.Label(p,text='Relatórios e cópias para consulta',style='Title.TLabel').pack(anchor='w',pady=(0,8))
        controls=ttk.Frame(p);controls.pack(fill='x',pady=(0,10))
        ttk.Button(controls,style='Accent.TButton',text='Exportar Excel (.xlsx)…',command=self.export_report).pack(side='left',padx=(0,10))
        ttk.Button(controls,text='Abrir pasta de backups',command=self.show_backups).pack(side='left')
        ttk.Label(p,text='Para restaurar dados, feche o sistema e execute RESTAURAR_BACKUP.bat.').pack(anchor='w',pady=(0,10))
        ttk.Label(p,text='Últimas vendas — Nº DA COMANDA é diferente do nº da venda',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(p); row.pack(fill='x',pady=(3,4))
        ttk.Button(row,text='Reabrir comanda desta venda…',command=self.reopen_selected_sale).pack(side='left',padx=(0,10))
        ttk.Label(row,text='Selecione uma venda com COMANDA Nº e caixa ABERTO. Vendas diretas não têm comanda.').pack(side='left')
        self.sales_tree=self.table(p,['Venda nº','COMANDA Nº','Cliente / origem','Data','Caixa','Pagamento','Valor','Situação'],[70,100,185,147,65,95,100,176],7)
        self.sales_tree.bind('<Double-1>',lambda e:self.reopen_selected_sale())
        ttk.Label(p,text='Últimos movimentos de estoque',style='Title.TLabel').pack(anchor='w')
        self.history_tree=self.table(p,['Data','Produto','Variação','Motivo'],[175,250,100,230],9)
    def build_finance(self):
        p=self.p_finance
        ttk.Label(p,text='Despesas operacionais e controle mensal',style='Title.TLabel').pack(anchor='w',pady=(0,6))
        main=ttk.Frame(p);main.pack(fill='both',expand=True)
        # Fixed right-hand summary panel avoids hiding controls when a monthly calculation grows.
        aside=ttk.Frame(main,width=322,padding=(12,4));aside.pack(side='right',fill='y')
        aside.pack_propagate(False)
        ttk.Label(aside,text='Saúde financeira mensal',style='Title.TLabel').pack(anchor='w',pady=(0,6))
        f=ttk.Frame(aside);f.pack(fill='x')
        self.month=self.entry(f,'Mês (AAAA-MM)',datetime.now().strftime('%Y-%m'),15)
        ttk.Button(aside,style='Accent.TButton',text='Calcular resumo mensal',command=lambda:self.safe(self.show_month)).pack(anchor='w',pady=(5,9))
        self.month_label=ttk.Label(aside,text='Clique para calcular o resultado do mês.',justify='left',wraplength=286)
        self.month_label.pack(anchor='w',fill='x')
        ttk.Label(aside,text='Não é extrato bancário: Pix/cartão podem ser recebidos depois. Estimativas dependem de dados completos.',style='Secondary.TLabel',wraplength=282).pack(side='bottom',anchor='w',pady=(6,0))
        area=ttk.Frame(main);area.pack(side='left',fill='both',expand=True)
        ttk.Label(area,text='Lançar despesas e compras de estoque',style='Headline.TLabel').pack(anchor='w',pady=(0,3))
        f=ttk.Frame(area);f.pack(fill='x')
        self.expdesc=self.entry(f,'Descrição','',23)
        self.expcat=self.choose(f,'Categoria',CATEGORIES,15)
        self.expamount=self.entry(f,'Valor (R$)','0,00',12)
        today=datetime.now().strftime('%Y-%m-%d')
        f=ttk.Frame(area);f.pack(fill='x')
        self.expoccurred=self.entry(f,'Data do gasto',today,14)
        self.expdate=self.entry(f,'Vencimento',today,14)
        self.exppaiddate=self.entry(f,'Pago em',today,14)
        f=ttk.Frame(area);f.pack(fill='x',pady=(0,4))
        ttk.Button(f,text='Registrar a pagar',command=lambda:self.safe(lambda:self.save_expense(False),'Despesa registrada como pendente.')).pack(side='left',padx=4)
        ttk.Button(f,style='Accent.TButton',text='Registrar como pago',command=lambda:self.safe(lambda:self.save_expense(True),'Despesa registrada como paga.')).pack(side='left',padx=4)
        ttk.Button(f,text='Quitar selecionada',command=lambda:self.safe(lambda:set_paid(STORE,self.selected(self.exp_tree,'uma despesa'),self.exppaiddate.get()),'Despesa quitada.')).pack(side='left',padx=4)
        ttk.Label(area,text='Datas: AAAA-MM-DD. Compras de estoque são saídas financeiras, não custo duplicado no resultado.',style='Secondary.TLabel',wraplength=840).pack(anchor='w',pady=(0,4))
        self.exp_tree=self.table(area,['ID','Descrição','Categoria','Valor','Data gasto','Vencimento','Pago em','Situação'],
                                 [42,170,113,84,94,94,94,73],6)

    def save_expense(self,paid):
        add_expense(STORE,self.expdesc.get(),self.expcat.get(),self.expamount.get(),self.expdate.get(),
                    paid=paid,incurred_date=self.expoccurred.get(),payment_date=self.exppaiddate.get() if paid else None)
        for e in (self.expdesc,self.expamount): e.delete(0,'end')
        self.expamount.insert(0,'0,00')

    def show_month(self):
        d=month_summary(STORE,self.month.get())
        future=sum(r['estimated'] for r in replenish(STORE))
        warnings=[]
        if d['historical_cost_estimated']: warnings.append('Custo histórico incompleto.')
        if d['missing_fee_sales']: warnings.append('Taxas antigas desconhecidas.')
        if not d['das_configured']: warnings.append('DAS não configurado.')
        text=(f"Vendas válidas: {money(d['sales'])}\n"
              f"CMV: − {money(d['cmv'])}\n"
              f"Taxas dos pagamentos: − {money(d['fees'])}\n"
              f"Despesas do mês: − {money(d['operating'])}\n"
              f"DAS provisionado: − {money(d['das'])}\n"
              f"____________________________\n"
              f"RESULTADO ESTIMADO: {money(d['estimated_profit'])}\n\n"
              f"Compras lançadas: {money(d['purchases'])}\n"
              f"Pagamentos registrados: {money(d['paid_out'])}\n"
              f"Pendências com vencimento no mês: {money(d['pending_due'])}\n"
              f"Reposição sugerida atual: {money(future)}\n\n"
              +('AVISOS: '+' '.join(warnings) if warnings else 'Estimativa com os dados cadastrados.'))
        self.month_label.configure(text=text)

    def build_profit(self):
        p=self.p_profit
        bottom=ttk.Frame(p);bottom.pack(side='bottom',fill='x',pady=(2,0))
        ttk.Separator(bottom,orient='horizontal').pack(fill='x',pady=(0,6))
        ttk.Label(bottom,text='Taxas e DAS mensal (cadastrar somente valores reais confirmados)',style='Headline.TLabel').pack(anchor='w')
        rates=get_payment_rates(STORE)
        row=ttk.Frame(bottom);row.pack(fill='x')
        self.rate_inputs={}
        for label in PAYMENTS:
            self.rate_inputs[label]=self.entry(row,'Taxa '+label+' (%)',f'{rates[label]/100:.2f}'.replace('.',','),11)
        row=ttk.Frame(bottom);row.pack(fill='x')
        configured=get_setting(STORE,'mei_das_monthly')
        self.das_entry=self.entry(row,'DAS mensal (R$)','' if configured is None else f'{configured/100:.2f}'.replace('.',','),15)
        ttk.Button(row,style='Accent.TButton',text='Salvar taxas e DAS',command=lambda:self.safe(self.save_financial_settings)).pack(side='left',padx=7,pady=8)
        ttk.Label(bottom,text='Taxas só nas próximas vendas. DAS em branco = ainda não informado; não substitui a contabilidade.',style='Secondary.TLabel',wraplength=1000).pack(anchor='w')
        self.profit_result=ttk.Label(bottom,text='',style='Secondary.TLabel',wraplength=1000)
        self.profit_result.pack(anchor='w',pady=(4,0))
        ttk.Label(p,text='Lucratividade por produto • resultado gerencial com rateio das despesas',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(p);row.pack(fill='x')
        self.profit_month=self.entry(row,'Mês (AAAA-MM)',datetime.now().strftime('%Y-%m'),14)
        ttk.Button(row,style='Accent.TButton',text='Calcular margens',command=lambda:self.safe(self.show_profit)).pack(side='left',padx=8,pady=7)
        ttk.Label(p,text='Contribuição = venda − custo − taxa. Lucro estimado = contribuição − rateio de despesas e DAS.',wraplength=1050).pack(anchor='w')
        self.profit_tree=self.table(p,['Produto','Qtd.','Vendas','CMV','Taxas','Contribuição','Rateio fixos + DAS','Lucro estimado','Margem'],
                [175,55,90,90,85,102,143,108,75],5)

    def save_financial_settings(self):
        update_settings(STORE,{key:e.get() for key,e in self.rate_inputs.items()},self.das_entry.get())
        self.show_profit()
        messagebox.showinfo('Configuração salva','Novas taxas serão aplicadas somente às próximas vendas. DAS é uma provisão mensal.',parent=self)

    def show_profit(self):
        data,summary=profitability(STORE,self.profit_month.get())
        self.fill(self.profit_tree,[(r['id'],(r['name'],r['qty'],money(r['revenue']),money(r['cmv']),money(r['fee']),
            money(r['contribution']),money(r['allocated']),money(r['profit']),f"{r['margin']:.1f}%".replace('.',','))) for r in data])
        warnings=[]
        if summary['historical_cost_estimated']: warnings.append('custos antigos ausentes ou zerados')
        if summary['missing_fee_sales']: warnings.append('taxas antigas não registradas')
        if not summary['das_configured']: warnings.append('DAS sem confirmação')
        self.profit_result.configure(text=(f"RESULTADO MENSAL ESTIMADO: {money(summary['estimated_profit'])}. "
            'Despesas fixas e DAS rateados pelo faturamento de cada produto. '
            + ('ATENÇÃO: '+', '.join(warnings)+'.' if warnings else 'Não inclui valores não cadastrados.')))

    def build_replenish(self):
        p=self.p_replenish
        ttk.Label(p,text='Sugestão de reposição por estoque mínimo',style='Title.TLabel').pack(anchor='w',pady=10)
        ttk.Label(p,text='Defina o estoque mínimo e custo unitário na aba Produtos. A compra sugerida é arredondada para caixas/fardos inteiros.').pack(anchor='w',pady=8)
        self.replenish_tree=self.table(p,['Produto','Disponível','Mínimo','Un./caixa','Caixas sugeridas','Unidades','Custo estimado'],[250,100,100,100,145,95,150],15)
        self.replenish_total=ttk.Label(p,text='',style='Title.TLabel');self.replenish_total.pack(anchor='w',pady=15)
        ttk.Label(p,text='É uma projeção para decisão de compra, não uma despesa já realizada. Custos devem ser atualizados com valores reais.',wraplength=1000).pack(anchor='w')
    def export_report(self):
        dest=filedialog.asksaveasfilename(parent=self,title='Salvar relatório Excel',defaultextension='.xlsx',filetypes=[('Planilha Excel','*.xlsx')],initialfile='Salva_ai_headshop_relatorio.xlsx')
        if dest:
            try: export_xlsx(STORE,dest);self.status('Relatório Excel salvo em '+dest)
            except Exception as e: messagebox.showerror('Falha na exportação',str(e),parent=self)
    def show_backups(self):
        folder=ROOT/'backups';folder.mkdir(parents=True,exist_ok=True)
        try: open_folder(folder)
        except Exception as e: messagebox.showerror('Não foi possível abrir',str(e),parent=self)
    def refresh(self):
        products=STORE.products()
        self.fill(self.products_tree,[(p['id'],(p['id'],p['name'],money(p['price']),p['stock'],p['stock']-p['available'],p['available'],p['pack_size'])) for p in products])
        options=[f"{p['id']} | {p['name']} ({money(p['price'])}; livre {p['available']})" for p in products]
        for combo in (self.tabproduct,self.directproduct):
            previous=combo.get().split(' | ',1)[0]
            combo['values']=options
            match=next((x for x in options if x.startswith(previous+' | ')),None)
            combo.set(match or (options[0] if options else ''))
        selection=self.tabs_tree.selection();tab_id=selection[0] if selection else None
        self.fill(self.tabs_tree,[(t['id'],(t['id'],t['customer'],t['opened_at'],money(t['total']))) for t in STORE.open_tabs()])
        if tab_id and self.tabs_tree.exists(tab_id): self.tabs_tree.selection_set(tab_id)
        self.refresh_tab_items()
        session,totals=STORE.cash_summary()
        self.cash_status.configure(text=f"Caixa #{session['id']} aberto em {session['opened_at']} | Troco inicial: {money(session['opening_cash'])}" if session else 'CAIXA FECHADO — abra o caixa antes de registrar vendas.')
        self.header_cash.configure(text=f"● Caixa nº {session['id']} aberto" if session else '○ Caixa fechado',
                                   foreground=COLORS['success'] if session else COLORS['secondary'])
        self.open_cash_btn.state(['disabled'] if session else ['!disabled'])
        self.close_cash_btn.state(['!disabled'] if session else ['disabled'])
        lookup={t['payment']:t for t in totals}
        self.fill(self.totals_tree,[(idx,(pay,lookup[pay]['n'] if pay in lookup else 0,money(lookup[pay]['total'] if pay in lookup else 0))) for idx,pay in enumerate(PAYMENTS)])
        total=sum(t['total'] for t in totals)
        expected=(session['opening_cash']+lookup['Dinheiro']['total'] if 'Dinheiro' in lookup else session['opening_cash']) if session else 0
        self.cash_total.configure(text=f'Total de vendas: {money(total)}  |  Dinheiro esperado no caixa: {money(expected)}')
        if hasattr(self,'exp_tree'):
            expenses=STORE.fetch('SELECT * FROM expenses ORDER BY incurred_date DESC,id DESC LIMIT 150')
            self.fill(self.exp_tree,[(e['id'],(e['id'],e['description'],e['category'],money(e['amount']),e['incurred_date'],e['due_date'],e['paid_at'][:10] if e['paid_at'] else '—','PAGO' if e['paid_at'] else 'PENDENTE')) for e in expenses])
        if hasattr(self,'replenish_tree'):
            rows=replenish(STORE)
            self.fill(self.replenish_tree,[(r['id'],(r['name'],r['available'],r['min_stock'],r['pack_size'],r['packs'],r['units'],money(r['estimated']))) for r in rows])
            self.replenish_total.configure(text='Compra sugerida: '+money(sum(r['estimated'] for r in rows)))
        selected_sale=self.sales_tree.selection()
        sales=[]
        for s in STORE.day_sales():
            if s['voided_at']: status='ESTORNADA'
            elif s['tab_id'] is None: status='VENDA DIRETA'
            elif s['cash_closed_at']: status='CAIXA FECHADO'
            elif s['tab_status']=='PAID': status='PODE REABRIR'
            else: status='VERIFICAR'
            sales.append((s['id'],(s['id'],s['tab_id'] if s['tab_id'] is not None else '—',s['customer'],s['sold_at'],s['session_id'],s['payment'],money(s['total']),status)))
        self.fill(self.sales_tree,sales)
        if selected_sale and self.sales_tree.exists(selected_sale[0]): self.sales_tree.selection_set(selected_sale[0])
        self.fill(self.history_tree,[(h['id'],(h['movement_at'],h['name'],f"{h['delta']:+d}",h['reason'])) for h in STORE.history()])
    def quit_app(self): STORE.close();self.destroy()

def main():
    global STORE
    STORE=Store(ROOT/'dados'/'bar.sqlite3')
    backup_before_upgrade(STORE,ROOT/'backups')
    migrate(STORE)
    App().mainloop()

if __name__=='__main__': main()
