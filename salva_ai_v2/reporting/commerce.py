from datetime import datetime
from .commerce_models import CommerceRow,CommerceItem
from ..common.service import valid_date
from ..common.errors import BusinessError
from ..inventory.queries import normalize
from ..delivery.queries import DeliveryQueries


class CommerceQueries:
    def __init__(self,db):
        self.db=db
        self.delivery=DeliveryQueries(db)

    def _sale_row(self,sale):
        refunded=self.db.conn.execute('SELECT COALESCE(SUM(refunded_cents),0) FROM refunds WHERE sale_id=?',(sale['id'],)).fetchone()[0]
        return CommerceRow(f"sale:{sale['id']}",sale['kind'],sale['order_id'],sale['id'],sale['customer'],
            datetime.fromisoformat(sale['sold_at']),sale['total_cents'],'REVERSED' if sale['reversed'] else 'PAID',sale['total_cents']-refunded)

    def _delivery_row(self,detail):
        order=detail['order']
        paid=sum(r['amount_cents']-r['refunded_cents'] for r in detail['collections'])
        sale=self.db.conn.execute('SELECT id FROM sales WHERE order_id=? ORDER BY id DESC LIMIT 1',(order['id'],)).fetchone()
        return CommerceRow(f"delivery:{order['id']}",'DELIVERY',order['id'],sale[0] if sale else None,order['name'],
            datetime.fromisoformat(order['created_at']),order['total_cents'],order['state'],paid)

    def list(self,filters):
        start,end=valid_date(filters.start),valid_date(filters.end)
        if start>end:
            raise BusinessError('O início deve ser anterior ao fim do período.')
        if filters.kind not in (None,'CART','TAB','DELIVERY'):
            raise BusinessError('Escolha balcão, comanda ou delivery.')
        result=[]
        for sale in self.db.conn.execute("SELECT s.*,o.kind,o.name customer FROM sales s JOIN orders o ON o.id=s.order_id WHERE o.kind<>'DELIVERY' AND substr(s.sold_at,1,10) BETWEEN ? AND ?",(start,end)):
            result.append(self._sale_row(sale))
        for order in self.db.conn.execute('SELECT order_id FROM delivery_orders d JOIN orders o ON o.id=d.order_id WHERE substr(o.created_at,1,10) BETWEEN ? AND ?',(start,end)):
            result.append(self._delivery_row(self.delivery.detail(order['order_id'])))
        filtered=[];text=normalize(filters.text)
        for row in result:
            if filters.kind and row.kind!=filters.kind or filters.state and row.state!=filters.state:
                continue
            if text:
                names=' '.join(i.name for i in self.detail(row.key)['items'])
                if text not in normalize(row.customer+' '+names) and text not in (str(row.order_id),str(row.sale_id),row.key):
                    continue
            filtered.append(row)
        return sorted(filtered,key=lambda r:(r.occurred_at,r.key),reverse=True)

    def detail(self,key):
        kind,separator,id=str(key).partition(':')
        if not separator or not id.isdigit():
            raise BusinessError('Identificação de venda inválida.')
        if kind=='delivery':
            delivery=self.delivery.detail(int(id))
            items=[CommerceItem(r['product_id'],r['name'],r['qty'],r['unit_cents'],r['group_qty'],r['group_cents'],r['total_cents']) for r in delivery['items']]
            return dict(row=self._delivery_row(delivery),items=items,delivery=delivery,refunds=delivery['refunds'])
        if kind!='sale':
            raise BusinessError('Tipo de venda inválido.')
        sale=self.db.conn.execute("SELECT s.*,o.kind,o.name customer FROM sales s JOIN orders o ON o.id=s.order_id WHERE s.id=? AND o.kind<>'DELIVERY'",(int(id),)).fetchone()
        if not sale:
            raise BusinessError('Venda não encontrada.')
        items=[CommerceItem(r['product_id'],r['name_snapshot'],r['qty'],r['unit_cents'],r['group_qty'],r['group_cents'],r['total_cents']) for r in self.db.conn.execute('SELECT * FROM sale_items WHERE sale_id=? ORDER BY product_id',(int(id),))]
        refunds=[dict(r) for r in self.db.conn.execute('SELECT * FROM refunds WHERE sale_id=?',(int(id),))]
        return dict(row=self._sale_row(sale),items=items,delivery=None,refunds=refunds)
