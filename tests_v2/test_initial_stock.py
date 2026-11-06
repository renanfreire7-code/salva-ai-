from tests_v2.support import DatabaseCase
from salva_ai_v2.common.errors import BusinessError


class InitialStockTest(DatabaseCase):
    def setUp(self):
        super().setUp()
        from salva_ai_v2.inventory.service import InventoryService
        from salva_ai_v2.security.service import SecurityService
        self.security=SecurityService(self.db);self.security.setup('681')
        self.inventory=InventoryService(self.db,self.security)
        self.pid=self.inventory.create_product('Lata',500,12,6,'p1')

    def grant(self,action):
        return self.security.authorize('681',action)

    def receive(self,qty,cost):
        from salva_ai_v2.inventory.models import PurchaseLine
        return self.inventory.receive_purchase([PurchaseLine(self.pid,qty,cost)],0,self.clock.today(),self.clock.today(),'buy')

    def initialize(self, qty=24, cost=450, cmd='initial'):
        return self.inventory.initialize_stock(self.pid,qty,cost,self.grant('stock.adjust'),cmd)

    def test_initial_stock_is_valued_and_does_not_create_financial_entries(self):
        self.initialize()
        p=self.inventory.position(self.pid)
        self.assertEqual((p.physical,p.available,p.value_cents),(24,24,10800))
        for table in ('purchases','obligations','cash_entries'):
            self.assertEqual(self.scalar(f'SELECT count(*) FROM {table}'),0)
        row=self.db.conn.execute('SELECT qty,value_cents,kind FROM stock_movements').fetchone()
        self.assertEqual(tuple(row),(24,10800,'INITIAL_STOCK'))
        self.assertEqual(self.scalar("SELECT count(*) FROM audit_events WHERE kind='stock.initialized'"),1)

    def test_retry_is_idempotent_but_another_initial_entry_is_rejected(self):
        self.initialize();self.initialize()
        with self.assertRaises(BusinessError):self.initialize(cmd='again')
        self.assertEqual(self.inventory.position(self.pid).physical,24)
        self.assertEqual(self.scalar('SELECT count(*) FROM stock_movements'),1)

    def test_initial_entry_rejects_invalid_inputs_without_changes(self):
        for qty,cost in [(0,100),(-1,100),(True,100),(1.5,100),(1,0),(1,-1),(1,True),(1,1.2),(10**19,100)]:
            with self.subTest(qty=qty,cost=cost),self.assertRaises(BusinessError):self.initialize(qty,cost,str((qty,cost)))
        self.assertEqual(self.inventory.position(self.pid).physical,0)
        self.assertEqual(self.scalar('SELECT count(*) FROM stock_movements'),0)

    def test_no_authorization_or_existing_history_or_inactive_is_rejected(self):
        with self.assertRaises(BusinessError):self.inventory.initialize_stock(self.pid,1,100,None,'unauthorized')
        self.receive(1,200)
        with self.db.transaction():self.inventory.consume(self.pid,1)
        with self.assertRaises(BusinessError):self.initialize()
        other=self.inventory.create_product('Inativo',100,1,0,'inactive')
        self.inventory.deactivate(other,self.grant('product.deactivate'),'Produto desativado','off')
        with self.assertRaises(BusinessError):self.inventory.initialize_stock(other,1,100,self.grant('stock.adjust'),'initial-off')
        self.assertEqual(self.inventory.position(self.pid).physical,0)

    def test_new_product_creation_rolls_back_when_initial_stock_is_not_authorized(self):
        before=self.scalar('SELECT count(*) FROM products')
        with self.assertRaises(BusinessError):
            self.inventory.create_product_with_initial_stock('Não salvar',500,1,0,2,100,None,'new')
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),before)
        grant=self.grant('stock.adjust')
        product=self.inventory.create_product_with_initial_stock('Água',300,1,0,30,120,grant,'new')
        self.assertEqual(self.inventory.position(product).value_cents,3600)
        self.assertEqual(self.inventory.create_product_with_initial_stock('Água',300,1,0,30,120,grant,'new'),product)
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),before+1)

    def test_cost_and_totals_follow_consumption_and_later_weighted_purchase(self):
        self.initialize()
        with self.db.transaction():self.assertEqual(self.inventory.consume(self.pid,4),1800)
        self.assertEqual(self.inventory.stock_totals(),dict(initial_value_cents=10800,current_value_cents=9000))
        self.receive(10,6000)
        p=self.inventory.position(self.pid)
        self.assertEqual((p.physical,p.value_cents),(30,15000))
        self.assertEqual(self.inventory.stock_totals(),dict(initial_value_cents=10800,current_value_cents=15000))

    def test_sale_records_cost_from_initial_stock_without_creating_purchase(self):
        from salva_ai_v2.cash.service import CashService
        from salva_ai_v2.pricing.service import PricingService
        from salva_ai_v2.sales.service import SalesService
        from salva_ai_v2.sales.models import Payment
        self.initialize()
        cash=CashService(self.db,self.security);cash.open(0,'cash')
        sales=SalesService(self.db,self.inventory,PricingService(self.db),cash,self.security)
        cart=sales.create_cart('cart');sales.set_cart_qty(cart,self.pid,3,'qty');sale=sales.sell(cart,Payment('PIX'),'sale')
        self.assertEqual(self.scalar('SELECT cogs_cents FROM sale_items WHERE sale_id=?',(sale.id,)),1350)
        self.assertEqual(self.scalar('SELECT count(*) FROM purchases'),0)
        self.assertEqual(self.inventory.stock_totals(),dict(initial_value_cents=10800,current_value_cents=9450))
