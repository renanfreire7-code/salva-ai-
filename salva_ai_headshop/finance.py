"""Finanças gerenciais offline. Valores em centavos; taxas em pontos-base (0,01%).
Não substitui apuração tributária nem conciliação de pagamentos externos.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from core import BusinessError, now, parse_money

CATEGORIES=('Aluguel','Energia','Água','Internet','Manutenção','Pessoal','Impostos','DAS MEI','Outras despesas','Compra de estoque')
PAYMENTS=('Dinheiro','Pix','Débito','Crédito')

def valid_date(value):
    try: return date.fromisoformat(str(value).strip()).isoformat()
    except (TypeError, ValueError): raise BusinessError('Data inválida: utilize AAAA-MM-DD.')

def valid_month(value):
    try:
        if len(value)!=7: raise ValueError()
        date.fromisoformat(value+'-01')
    except (TypeError,ValueError): raise BusinessError('Mês inválido. Utilize AAAA-MM.')
    return value

def migrate(store):
    db=store.db
    with db:
        db.execute('''CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY, description TEXT NOT NULL, category TEXT NOT NULL,
           amount INTEGER NOT NULL CHECK(amount>0), due_date TEXT NOT NULL, paid_at TEXT, created_at TEXT NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS finance_events(id INTEGER PRIMARY KEY, event_at TEXT NOT NULL, kind TEXT NOT NULL,
           object_id INTEGER, description TEXT NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY, value INTEGER NOT NULL CHECK(value>=0))''')
        cols={r[1] for r in db.execute('PRAGMA table_info(sales)')}
        if 'voided_at' not in cols: db.execute('ALTER TABLE sales ADD COLUMN voided_at TEXT')
        if 'void_reason' not in cols: db.execute('ALTER TABLE sales ADD COLUMN void_reason TEXT')
        if 'payment_fee' not in cols: db.execute('ALTER TABLE sales ADD COLUMN payment_fee INTEGER')
        if 'payment_rate_bp' not in cols: db.execute('ALTER TABLE sales ADD COLUMN payment_rate_bp INTEGER')
        cols={r[1] for r in db.execute('PRAGMA table_info(products)')}
        if 'cost' not in cols: db.execute('ALTER TABLE products ADD COLUMN cost INTEGER NOT NULL DEFAULT 0')
        if 'min_stock' not in cols: db.execute('ALTER TABLE products ADD COLUMN min_stock INTEGER NOT NULL DEFAULT 0')
        cols={r[1] for r in db.execute('PRAGMA table_info(sale_items)')}
        if 'cost_at_sale' not in cols: db.execute('ALTER TABLE sale_items ADD COLUMN cost_at_sale INTEGER')
        cols={r[1] for r in db.execute('PRAGMA table_info(expenses)')}
        if 'incurred_date' not in cols: db.execute('ALTER TABLE expenses ADD COLUMN incurred_date TEXT')
        # Legacy rows get their original due date as an explicitly approximate competence date.
        db.execute('UPDATE expenses SET incurred_date=due_date WHERE incurred_date IS NULL')

def parse_percent(value):
    text=str(value).strip().replace('%','').replace(' ','').replace(',','.')
    try: x=Decimal(text)
    except (InvalidOperation,ValueError): raise BusinessError('Taxa inválida. Exemplo: 2,50.')
    if not x.is_finite() or x<0 or x>100: raise BusinessError('A taxa deve estar entre 0% e 100%.')
    if x.as_tuple().exponent<-2 and x!=x.quantize(Decimal('.01')): raise BusinessError('Use no máximo duas casas decimais na taxa.')
    return int((x*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def payment_fee(total_cents, rate_bp):
    return int((Decimal(total_cents)*Decimal(rate_bp)/Decimal(10000)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def get_setting(store,key,default=None):
    row=store.one('SELECT value FROM app_settings WHERE key=?',(key,))
    return row['value'] if row else default

def get_payment_rates(store):
    return {pay:get_setting(store,'payment_'+pay,0) for pay in PAYMENTS}

def update_settings(store,rates,das_monthly):
    if any(pay not in rates for pay in PAYMENTS): raise BusinessError('Informe as quatro formas de pagamento.')
    parsed={pay:parse_percent(rates[pay]) for pay in PAYMENTS}
    if parsed['Dinheiro']!=0: raise BusinessError('Dinheiro deve ter taxa de processamento 0%.')
    if das_monthly is None or str(das_monthly).strip()=='':
        das=None  # Em branco = valor ainda não confirmado.
    elif isinstance(das_monthly,int):
        das=das_monthly
        if das<0: raise BusinessError('DAS inválido.')
    else: das=parse_money(das_monthly)
    with store.db:
        for pay,bp in parsed.items():
            store.db.execute('INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)',('payment_'+pay,bp))
        if das is None:
            store.db.execute('DELETE FROM app_settings WHERE key=?',('mei_das_monthly',))
        else:
            store.db.execute('INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)',('mei_das_monthly',das))
        store.db.execute('INSERT INTO finance_events(event_at,kind,description) VALUES(?,?,?)',(now(),'CONFIG_FINANCEIRA','Taxas de pagamento e provisão de DAS atualizadas'))

def add_expense(store,description,category,amount,due_date,paid=False,incurred_date=None,payment_date=None):
    description=description.strip()
    if not description: raise BusinessError('Informe uma descrição da despesa.')
    if category not in CATEGORIES: raise BusinessError('Categoria não reconhecida.')
    due=valid_date(due_date); incurred=valid_date(incurred_date or due)
    cents=parse_money(amount)
    if cents<=0: raise BusinessError('Valor deve ser positivo.')
    payment=valid_date(payment_date or date.today().isoformat())+' 12:00:00' if paid else None
    with store.db:
        store.db.execute('''INSERT INTO expenses(description,category,amount,due_date,paid_at,created_at,incurred_date)
             VALUES(?,?,?,?,?,?,?)''',(description,category,cents,due,payment,now(),incurred))

def set_paid(store,expense_id,payment_date=None):
    paid=valid_date(payment_date or date.today().isoformat())+' 12:00:00'
    with store.db:
        cur=store.db.execute('UPDATE expenses SET paid_at=? WHERE id=? AND paid_at IS NULL',(paid,expense_id))
        if cur.rowcount!=1: raise BusinessError('Despesa não encontrada ou já paga.')
        store.db.execute('INSERT INTO finance_events(event_at,kind,object_id,description) VALUES(?,?,?,?)',(now(),'PAGAMENTO_DESPESA',expense_id,paid[:10]))

def set_product_cost(store,pid,cost,min_stock):
    store.product(pid)
    try: minimum=int(min_stock)
    except (TypeError,ValueError): raise BusinessError('Estoque mínimo inválido.')
    if minimum<0: raise BusinessError('Estoque mínimo não pode ser negativo.')
    with store.db: store.db.execute('UPDATE products SET cost=?,min_stock=? WHERE id=?',(parse_money(cost),minimum,pid))

def reopen_paid_tab(store,tab_id,reason):
    reason=reason.strip()
    if len(reason)<5: raise BusinessError('Descreva o motivo da reabertura (mínimo 5 caracteres).')
    with store.db:
        tab=store.one('SELECT * FROM tabs WHERE id=?',(tab_id,))
        if not tab or tab['status']!='PAID': raise BusinessError('Esta comanda não está fechada e paga.')
        sale=store.one('SELECT * FROM sales WHERE tab_id=? AND voided_at IS NULL ORDER BY id DESC LIMIT 1',(tab_id,))
        if not sale: raise BusinessError('Venda original não encontrada.')
        cash=store.active_session()
        if not cash or cash['id']!=sale['session_id']:
            raise BusinessError('A reabertura só é permitida enquanto o mesmo caixa da venda estiver aberto. Não altere caixas encerrados.')
        for item in store.tab_items(tab_id):
            store.db.execute('UPDATE products SET stock=stock+? WHERE id=?',(item['qty'],item['product_id']))
            store.db.execute('INSERT INTO stock_movements(product_id,movement_at,delta,reason,sale_id) VALUES(?,?,?,?,?)',
                             (item['product_id'],now(),item['qty'],'Estorno da venda para reabrir comanda',sale['id']))
        store.db.execute('UPDATE sales SET voided_at=?,void_reason=? WHERE id=?',(now(),reason,sale['id']))
        store.db.execute('UPDATE tabs SET status="OPEN",closed_at=NULL WHERE id=?',(tab_id,))
        store.db.execute('INSERT INTO finance_events(event_at,kind,object_id,description) VALUES(?,?,?,?)',(now(),'REABERTURA_COMANDA',tab_id,reason))

def month_summary(store,month):
    month=valid_month(month)
    sales=store.one('''SELECT COALESCE(SUM(total),0) revenue,
        COALESCE(SUM(payment_fee),0) fees,
        SUM(CASE WHEN payment_fee IS NULL THEN 1 ELSE 0 END) missing_fee,
        SUM(CASE WHEN payment IN ('Crédito','Débito') THEN total ELSE 0 END) card_gross
        FROM sales WHERE substr(sold_at,1,7)=? AND voided_at IS NULL''',(month,))
    cost=store.one('''SELECT COALESCE(SUM(i.qty*COALESCE(i.cost_at_sale,p.cost)),0) cmv,
        COALESCE(SUM(CASE WHEN i.cost_at_sale IS NULL OR COALESCE(i.cost_at_sale,p.cost)=0 THEN 1 ELSE 0 END),0) n_unknown
        FROM sale_items i JOIN sales s ON s.id=i.sale_id JOIN products p ON p.id=i.product_id
        WHERE substr(s.sold_at,1,7)=? AND s.voided_at IS NULL''',(month,))
    expenses=store.fetch('SELECT * FROM expenses WHERE substr(incurred_date,1,7)=?',(month,))
    operating=sum(e['amount'] for e in expenses if e['category'] not in ('Compra de estoque','DAS MEI'))
    purchases=sum(e['amount'] for e in expenses if e['category']=='Compra de estoque')
    das_exp=sum(e['amount'] for e in expenses if e['category']=='DAS MEI')
    configured_das=get_setting(store,'mei_das_monthly')
    das=configured_das if configured_das is not None else das_exp
    paid=store.one('SELECT COALESCE(SUM(amount),0) amount FROM expenses WHERE paid_at IS NOT NULL AND substr(paid_at,1,7)=?',(month,))['amount']
    due_unpaid=store.one('SELECT COALESCE(SUM(amount),0) amount FROM expenses WHERE paid_at IS NULL AND substr(due_date,1,7)=?',(month,))['amount']
    revenue=sales['revenue']; fee=sales['fees']
    profit=revenue-cost['cmv']-fee-operating-das
    return dict(sales=revenue,cmv=cost['cmv'],fees=fee,operating=operating,purchases=purchases,das=das,
        das_configured=configured_das is not None, das_expense_recorded=das_exp,
        paid_out=paid,pending_due=due_unpaid,estimated_profit=profit,
        cash_in_recorded=revenue,cash_flow_simplified=revenue-paid,
        historical_cost_estimated=cost['n_unknown']>0,unknown_cost_items=cost['n_unknown'],
        missing_fee_sales=sales['missing_fee'] or 0,
        # compatibility for prior screens/tests
        margin_before_fees_taxes=revenue-cost['cmv']-operating)

def profitability(store,month):
    """Rateio gerencial de custos fixos/despesas por peso de faturamento de cada produto.
    NOT an official accounting net profit; legacy fees/costs may be unknown.
    """
    summary=month_summary(store,month)
    rows=store.fetch('''SELECT p.id,p.name,COALESCE(SUM(i.qty),0) qty,
       COALESCE(SUM(i.qty*i.unit_price),0) revenue,
       COALESCE(SUM(i.qty*COALESCE(i.cost_at_sale,p.cost)),0) cost,
       COALESCE(SUM(CASE WHEN i.cost_at_sale IS NULL OR COALESCE(i.cost_at_sale,p.cost)=0 THEN 1 ELSE 0 END),0) uncertain
       FROM products p JOIN sale_items i ON i.product_id=p.id JOIN sales s ON s.id=i.sale_id
       WHERE substr(s.sold_at,1,7)=? AND s.voided_at IS NULL
       GROUP BY p.id,p.name ORDER BY revenue DESC,p.name''',(month,))
    feealloc={r['id']:0 for r in rows}
    # Allocate the snapshotted fee of each sale to its item lines based on price-weighted subtotals.
    sale_ids=store.fetch('SELECT id,payment_fee,total FROM sales WHERE substr(sold_at,1,7)=? AND voided_at IS NULL ORDER BY id',(month,))
    for s in sale_ids:
        items=store.fetch('SELECT product_id,qty,unit_price FROM sale_items WHERE sale_id=? ORDER BY id',(s['id'],))
        total=sum(i['qty']*i['unit_price'] for i in items)
        allocated=0
        for index,i in enumerate(items):
            fraction=((s['payment_fee'] or 0)*i['qty']*i['unit_price']//total) if total and index<len(items)-1 else (s['payment_fee'] or 0)-allocated
            feealloc[i['product_id']]=feealloc.get(i['product_id'],0)+fraction
            allocated+=fraction
    overhead=summary['operating']+summary['das']
    report=[]; cumulative=0
    for idx,r in enumerate(rows):
        share=(overhead*r['revenue']//summary['sales']) if summary['sales'] and idx<len(rows)-1 else overhead-cumulative
        cumulative+=share
        fee=feealloc[r['id']]; contribution=r['revenue']-r['cost']-fee
        result=contribution-share
        report.append(dict(id=r['id'],name=r['name'],qty=r['qty'],revenue=r['revenue'],cmv=r['cost'],
            fee=fee,contribution=contribution,allocated=share,profit=result,
            margin=(result/r['revenue']*100 if r['revenue'] else 0.0),unknown_cost=bool(r['uncertain'])))
    return report,summary

def replenish(store):
    out=[]
    for p in store.products():
        missing=max(0,p['min_stock']-p['available'])
        packs=(missing+p['pack_size']-1)//p['pack_size'] if missing else 0
        out.append({'id':p['id'],'name':p['name'],'available':p['available'],'min_stock':p['min_stock'],
                    'pack_size':p['pack_size'],'packs':packs,'units':packs*p['pack_size'],
                    'estimated':packs*p['pack_size']*p['cost']})
    return out
