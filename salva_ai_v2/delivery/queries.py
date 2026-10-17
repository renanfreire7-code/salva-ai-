from ..common.errors import BusinessError
from ..pricing.models import PriceCondition
from ..pricing.service import PricingService
from .payment_plan import expected_change


class DeliveryQueries:
    def __init__(self,db):
        self.db=db

    def detail(self,order_id):
        row=self.db.conn.execute('SELECT o.*,d.* FROM orders o JOIN delivery_orders d ON d.order_id=o.id WHERE o.id=?',(order_id,)).fetchone()
        if not row:
            raise BusinessError('Pedido de delivery não encontrado.')
        order=dict(row)
        items=[]
        for line in self.db.conn.execute('SELECT * FROM order_items WHERE order_id=? AND qty>0 ORDER BY product_id',(order_id,)):
            item=dict(line);item['name']=item['name_snapshot']
            item['total_cents']=PricingService.quote(PriceCondition(item['unit_cents'],item['group_qty'],item['group_cents']),item['qty']).total_cents
            items.append(item)
        order['subtotal_cents']=sum(item['total_cents'] for item in items)
        order['total_cents']=order['subtotal_cents']+order['delivery_fee_cents']
        collections=[dict(r) for r in self.db.conn.execute('SELECT * FROM collections WHERE order_id=? ORDER BY id',(order_id,))]
        custody=sum(r['amount_cents']-r['settled_cents']-r['courier_refunded_cents'] for r in collections if r['method']=='MONEY' and r['custodian']=='COURIER')
        trips=[]
        for row in self.db.conn.execute("SELECT t.*,o.id obligation_id FROM trips t LEFT JOIN obligations o ON o.source_type='TRIP' AND o.source_id=CAST(t.id AS TEXT) WHERE t.order_id=? ORDER BY t.id",(order_id,)):
            trip=dict(row)
            paid=self.db.conn.execute('SELECT COALESCE(SUM(amount_cents),0) FROM obligation_payments WHERE obligation_id=? AND corrected=0',(trip['obligation_id'],)).fetchone()[0]
            trip.update(paid_cents=paid,pending_cents=trip['fee_cents']-paid)
            trips.append(trip)
        plan={key:order[key] for key in ('payment_timing','payment_channel','method','change_for_cents','link_reference')}
        plan['expected_change_cents']=None if order['payment_timing']=='UNSPECIFIED' else expected_change(order['total_cents'],order['change_for_cents'])
        settlement_ids=set()
        for kind,ids in (('TRIP',[r['id'] for r in trips]),('COLLECTION',[r['id'] for r in collections])):
            for id in ids:
                settlement_ids.update(r[0] for r in self.db.conn.execute('SELECT settlement_id FROM settlement_items WHERE source_type=? AND source_id=?',(kind,id)))
        return dict(order=order,items=items,payment_plan=plan,collections=collections,trips=trips,
            returns=[dict(r) for r in self.db.conn.execute('SELECT * FROM delivery_returns WHERE order_id=? ORDER BY id',(order_id,))],
            refunds=[dict(r) for r in self.db.conn.execute('SELECT * FROM refunds WHERE order_id=? ORDER BY id',(order_id,))],
            settlements=[self.settlement_detail(id) for id in sorted(settlement_ids)],custody_pending_cents=custody)

    def settlement_orders(self,pending_only=True):
        result=[]
        for row in self.db.conn.execute('SELECT order_id FROM delivery_orders ORDER BY order_id DESC'):
            detail=self.detail(row['order_id'])
            if not detail['trips'] and not detail['collections']:
                continue
            due=sum(r['pending_cents'] for r in detail['trips'])
            if pending_only and not (detail['custody_pending_cents'] or due):
                continue
            result.append(dict(order_id=row['order_id'],customer=detail['order']['name'],state=detail['order']['state'],
                total_cents=detail['order']['total_cents'],custody_pending_cents=detail['custody_pending_cents'],trip_pending_cents=due,
                collection_ids=[r['id'] for r in detail['collections'] if r['method']=='MONEY' and r['custodian']=='COURIER' and r['amount_cents']>r['settled_cents']+r['courier_refunded_cents']],
                trip_ids=[r['id'] for r in detail['trips'] if r['pending_cents']>0],detail=detail))
        return result

    def settlements(self):
        return [dict(r) for r in self.db.conn.execute('SELECT * FROM settlements ORDER BY id DESC')]

    def settlement_detail(self,settlement_id):
        row=self.db.conn.execute('SELECT * FROM settlements WHERE id=?',(settlement_id,)).fetchone()
        if not row:
            raise BusinessError('Acerto não encontrado.')
        result=dict(row);items=[]
        for row in self.db.conn.execute('SELECT * FROM settlement_items WHERE settlement_id=? ORDER BY id',(settlement_id,)):
            item=dict(row)
            table='collections' if item['source_type']=='COLLECTION' else 'trips'
            owner=self.db.conn.execute(f'SELECT order_id FROM {table} WHERE id=?',(item['source_id'],)).fetchone()
            item['order_id']=owner[0] if owner else None
            items.append(item)
        result['items']=items
        return result
