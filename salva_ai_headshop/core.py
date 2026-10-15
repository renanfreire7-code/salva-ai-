"""Núcleo offline do Salva ai headshop. Somente biblioteca padrão Python."""
import sqlite3
from datetime import datetime
from pathlib import Path

class BusinessError(Exception): pass

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def money(cents): return f'R$ {cents/100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def parse_money(value):
    s=str(value).strip().replace('R$', '').replace(' ', '')
    if not s: raise BusinessError('Informe um valor.')
    if ',' in s: s=s.replace('.', '').replace(',', '.')
    try:
        from decimal import Decimal, ROUND_HALF_UP
        c=int((Decimal(s)*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except Exception: raise BusinessError('Valor inválido.')
    if c < 0: raise BusinessError('Valor não pode ser negativo.')
    return c
def parse_qty(value, label='Quantidade'):
    try: return int(str(value).strip())
    except ValueError: raise BusinessError(f'{label} inválida: use um número inteiro.')

class Store:
    def __init__(self, path):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db=sqlite3.connect(str(self.path)); self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON'); self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.schema()
    def schema(self):
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE, price INTEGER NOT NULL CHECK(price>=0), stock INTEGER NOT NULL DEFAULT 0 CHECK(stock>=0), pack_size INTEGER NOT NULL DEFAULT 1 CHECK(pack_size>=1), active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS tabs(id INTEGER PRIMARY KEY, customer TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', opened_at TEXT NOT NULL, closed_at TEXT);
        CREATE TABLE IF NOT EXISTS tab_items(id INTEGER PRIMARY KEY, tab_id INTEGER NOT NULL REFERENCES tabs(id), product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>0), unit_price INTEGER NOT NULL CHECK(unit_price>=0));
        CREATE TABLE IF NOT EXISTS cash_sessions(id INTEGER PRIMARY KEY, opened_at TEXT NOT NULL, closed_at TEXT, opening_cash INTEGER NOT NULL DEFAULT 0, counted_cash INTEGER, backup_path TEXT);
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES cash_sessions(id), tab_id INTEGER REFERENCES tabs(id), sold_at TEXT NOT NULL, payment TEXT NOT NULL CHECK(payment IN ('Dinheiro','Pix','Débito','Crédito')), total INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES sales(id), product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL CHECK(qty>0), unit_price INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), movement_at TEXT NOT NULL, delta INTEGER NOT NULL, reason TEXT NOT NULL, sale_id INTEGER REFERENCES sales(id));
        ''')
        self.db.commit()
    def fetch(self, sql, params=()): return self.db.execute(sql,params).fetchall()
    def one(self, sql, params=()): return self.db.execute(sql,params).fetchone()
    def products(self): return self.fetch('SELECT p.*,p.stock-COALESCE((SELECT SUM(i.qty) FROM tab_items i JOIN tabs t ON t.id=i.tab_id WHERE t.status="OPEN" AND i.product_id=p.id),0) available FROM products p WHERE active=1 ORDER BY name')
    def product(self,pid):
        x=self.one('SELECT * FROM products WHERE id=? AND active=1',(pid,))
        if not x: raise BusinessError('Produto não encontrado.')
        return x
    def reserved(self,pid): return self.one('SELECT COALESCE(SUM(i.qty),0) n FROM tab_items i JOIN tabs t ON t.id=i.tab_id WHERE t.status="OPEN" AND i.product_id=?',(pid,))['n']
    def add_product(self,name,price,pack_size):
        name=name.strip()
        if not name: raise BusinessError('Informe o nome do produto.')
        pack_size=parse_qty(pack_size,'Unidades por caixa/fardo')
        if pack_size<=0: raise BusinessError('Unidades por caixa/fardo deve ser maior que zero.')
        try:
            with self.db: self.db.execute('INSERT INTO products(name,price,pack_size) VALUES(?,?,?)',(name,parse_money(price),pack_size))
        except sqlite3.IntegrityError: raise BusinessError('Já existe produto com esse nome.')
    def update_product(self,pid,price,pack_size):
        self.product(pid); ps=parse_qty(pack_size,'Unidades por caixa/fardo')
        if ps<=0: raise BusinessError('Unidades por caixa/fardo inválido.')
        with self.db: self.db.execute('UPDATE products SET price=?,pack_size=? WHERE id=?',(parse_money(price),ps,pid))
    def adjust_stock(self,pid,quantity,kind,reason):
        p=self.product(pid); quantity=parse_qty(quantity)
        if quantity<=0: raise BusinessError('Quantidade deve ser positiva.')
        if kind=='Caixa/Fardo (entrada)': delta=quantity*p['pack_size']
        elif kind=='Unidade (entrada)': delta=quantity
        elif kind=='Unidade (perda/ajuste)': delta=-quantity
        else: raise BusinessError('Movimentação inválida.')
        with self.db:
            if p['stock']+delta<self.reserved(pid): raise BusinessError('Ajuste deixaria estoque abaixo do reservado em comandas.')
            self.db.execute('UPDATE products SET stock=stock+? WHERE id=?',(delta,pid))
            self.db.execute('INSERT INTO stock_movements(product_id,movement_at,delta,reason) VALUES(?,?,?,?)',(pid,now(),delta,reason.strip() or kind))
    def open_tabs(self): return self.fetch('SELECT t.*,COALESCE(SUM(i.qty*i.unit_price),0) total FROM tabs t LEFT JOIN tab_items i ON i.tab_id=t.id WHERE t.status="OPEN" GROUP BY t.id ORDER BY t.id DESC')
    def create_tab(self,name):
        name=name.strip()
        if not name: raise BusinessError('Informe o nome do cliente.')
        with self.db:
            x=self.db.execute('INSERT INTO tabs(customer,opened_at) VALUES(?,?)',(name,now()))
            return x.lastrowid
    def tab_items(self,tab_id): return self.fetch('SELECT i.*,p.name FROM tab_items i JOIN products p ON p.id=i.product_id WHERE i.tab_id=? ORDER BY i.id',(tab_id,))
    def tab_total(self,tab_id): return sum(x['qty']*x['unit_price'] for x in self.tab_items(tab_id))
    def require_tab(self,tid):
        t=self.one('SELECT * FROM tabs WHERE id=? AND status="OPEN"',(tid,))
        if not t: raise BusinessError('Comanda não está aberta.')
        return t
    def add_to_tab(self,tid,pid,qty):
        self.require_tab(tid); p=self.product(pid); qty=parse_qty(qty)
        if qty<=0: raise BusinessError('Quantidade inválida.')
        with self.db:
            if p['stock']-self.reserved(pid)<qty: raise BusinessError('Estoque livre insuficiente para reservar.')
            self.db.execute('INSERT INTO tab_items(tab_id,product_id,qty,unit_price) VALUES(?,?,?,?)',(tid,pid,qty,p['price']))
    def remove_tab_item(self,tid,itemid):
        self.require_tab(tid)
        with self.db: self.db.execute('DELETE FROM tab_items WHERE id=? AND tab_id=?',(itemid,tid))
    def cancel_tab(self,tid):
        self.require_tab(tid)
        with self.db: self.db.execute('UPDATE tabs SET status="CANCELLED",closed_at=? WHERE id=?',(now(),tid))
    def active_session(self): return self.one('SELECT * FROM cash_sessions WHERE closed_at IS NULL ORDER BY id DESC LIMIT 1')
    def open_cash(self,opening):
        if self.active_session(): raise BusinessError('Já existe caixa aberto.')
        with self.db: self.db.execute('INSERT INTO cash_sessions(opened_at,opening_cash) VALUES(?,?)',(now(),parse_money(opening)))
    def _make_sale(self,items,payment,tid=None):
        if payment not in ('Dinheiro','Pix','Débito','Crédito'): raise BusinessError('Pagamento inválido.')
        session=self.active_session()
        if not session: raise BusinessError('Abra o caixa antes de vender.')
        if not items: raise BusinessError('Não é possível concluir venda sem produtos.')
        total=sum(x['qty']*x['unit_price'] for x in items)
        # Salva a taxa vigente no momento da venda, sem reprecificar o histórico.
        from finance import get_payment_rates, payment_fee
        rate_bp=get_payment_rates(self)[payment]
        fee=payment_fee(total,rate_bp)
        cur=self.db.execute('INSERT INTO sales(session_id,tab_id,sold_at,payment,total,payment_fee,payment_rate_bp) VALUES(?,?,?,?,?,?,?)',
                            (session['id'],tid,now(),payment,total,fee,rate_bp))
        sid=cur.lastrowid
        for i in items:
            self.db.execute('INSERT INTO sale_items(sale_id,product_id,qty,unit_price,cost_at_sale) VALUES(?,?,?,?,?)',(sid,i['product_id'],i['qty'],i['unit_price'],self.product(i['product_id'])['cost']))
            self.db.execute('UPDATE products SET stock=stock-? WHERE id=?',(i['qty'],i['product_id']))
            self.db.execute('INSERT INTO stock_movements(product_id,movement_at,delta,reason,sale_id) VALUES(?,?,?,?,?)',(i['product_id'],now(),-i['qty'],'Venda',sid))
        return sid
    def pay_tab(self,tid,payment):
        self.require_tab(tid)
        with self.db:
            items=self.tab_items(tid)
            sid=self._make_sale(items,payment,tid)
            self.db.execute('UPDATE tabs SET status="PAID",closed_at=? WHERE id=?',(now(),tid))
            return sid
    def direct_sale(self,pid,qty,payment):
        p=self.product(pid); qty=parse_qty(qty)
        if qty<=0: raise BusinessError('Quantidade inválida.')
        with self.db:
            if p['stock']-self.reserved(pid)<qty: raise BusinessError('Estoque livre insuficiente.')
            return self._make_sale([{'product_id':pid,'qty':qty,'unit_price':p['price']}],payment)
    def cash_summary(self):
        s=self.active_session()
        if not s: return None,[]
        totals=self.fetch('SELECT payment,COUNT(*) n,SUM(total) total FROM sales WHERE session_id=? AND voided_at IS NULL GROUP BY payment',(s['id'],))
        return s,totals
    def close_cash(self,counted_cash,backup_dir):
        s=self.active_session()
        if not s: raise BusinessError('Não há caixa aberto.')
        counted=parse_money(counted_cash)
        # Fecha o caixa e depois copia o banco, para que o backup já contenha o fechamento.
        backup_dir=Path(backup_dir); backup_dir.mkdir(parents=True,exist_ok=True)
        filename=f"salva_ai_backup_caixa_{s['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
        dest=backup_dir/filename
        with self.db:
            self.db.execute('UPDATE cash_sessions SET closed_at=?,counted_cash=?,backup_path=? WHERE id=?',(now(),counted,str(dest),s['id']))
        try:
            out=sqlite3.connect(str(dest))
            try: self.db.backup(out)
            finally: out.close()
        except Exception as e:
            # Manter caixa fechado e sinalizar que backup falhou: não afirmar que backup existe.
            dest.unlink(missing_ok=True)
            with self.db: self.db.execute('UPDATE cash_sessions SET backup_path=NULL WHERE id=?',(s['id'],))
            raise BusinessError('Caixa fechado, mas BACKUP FALHOU: '+str(e))
        return dest
    def day_sales(self,limit=100):
        """History includes separate sale and tab identifiers, and shows whether the original cash session is open."""
        return self.fetch("""SELECT s.*,COALESCE(t.customer,'Venda direta') customer,
            cs.closed_at cash_closed_at, t.status tab_status
            FROM sales s
            LEFT JOIN tabs t ON t.id=s.tab_id
            JOIN cash_sessions cs ON cs.id=s.session_id
            ORDER BY s.id DESC LIMIT ?""",(limit,))
    def history(self,limit=100): return self.fetch('SELECT m.*,p.name FROM stock_movements m JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT ?', (limit,))
    def close(self): self.db.close()
