from datetime import date,datetime
from decimal import Decimal
from .models import MonthlyResult,ProductResult,PurchaseSuggestion,HistoryRow,HistoryFilter,CashReport,ReportBundle
from ..finance.queries import month_range
from ..common.money import allocate,round_half_up
from ..common.service import valid_date
from ..common.errors import BusinessError


class ReportingQueries:
    def __init__(self,db):
        self.db=db

    def _data(self,month):
        month_range(month)
        products={r["id"]:dict(r) for r in self.db.conn.execute("SELECT id,name FROM products")}
        data={id:dict(qty=0,revenue=0,cost=0,fees=0) for id in products}
        delivery_revenue=delivery_fees=0
        warnings=[]
        def lines(sale_id):
            return self.db.conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY product_id",(sale_id,)).fetchall()
        for sale in self.db.conn.execute("SELECT s.*,o.kind FROM sales s JOIN orders o ON o.id=s.order_id WHERE substr(s.sold_at,1,7)=?",(month,)):
            rows=lines(sale["id"])
            if sale["kind"]!="DELIVERY":
                fees=allocate(sale["fee_cents"],{r["product_id"]:r["total_cents"] for r in rows})
                if sale["rate_bp"] is None:
                    warnings.append("Há vendas com taxa ainda não configurada.")
            else:
                fees={}
            for r in rows:
                d=data[r["product_id"]];d["qty"]+=r["qty"];d["revenue"]+=r["total_cents"];d["cost"]+=r["cogs_cents"]
                d["fees"]+=fees.get(r["product_id"],0)
            delivery_revenue+=sale["delivery_fee_cents"]
        for correction in self.db.conn.execute("SELECT c.*,s.delivery_fee_cents FROM sale_corrections c JOIN sales s ON s.id=c.sale_id WHERE substr(c.occurred_at,1,7)=?",(month,)):
            for r in lines(correction["sale_id"]):
                d=data[r["product_id"]];d["qty"]-=r["qty"];d["revenue"]-=r["total_cents"]
                if correction["returned"]:
                    d["cost"]-=r["cogs_cents"]
            delivery_revenue-=correction["delivery_fee_cents"]
        for r in self.db.conn.execute("SELECT product_id,SUM(cogs_cents) cost FROM delivery_returns WHERE substr(returned_at,1,7)=? GROUP BY product_id",(month,)):
            data[r["product_id"]]["cost"]-=r["cost"]
        for r in self.db.conn.execute("SELECT product_id, -SUM(value_cents) cost FROM stock_movements WHERE kind='LOSS' AND substr(moved_at,1,7)=? GROUP BY product_id",(month,)):
            data[r["product_id"]]["cost"]+=r["cost"]
        for collection in self.db.conn.execute("SELECT * FROM collections WHERE substr(collected_at,1,7)=?",(month,)):
            order_lines=self.db.conn.execute("SELECT * FROM order_items WHERE order_id=?",(collection["order_id"],)).fetchall()
            from ..pricing.service import PricingService
            from ..pricing.models import PriceCondition
            weights={r["product_id"]:PricingService.quote(PriceCondition(r["unit_cents"],r["group_qty"],r["group_cents"]),r["qty"]).total_cents for r in order_lines}
            detail=self.db.conn.execute("SELECT delivery_fee_cents FROM delivery_orders WHERE order_id=?",(collection["order_id"],)).fetchone()
            weights[0]=detail[0]
            fees=allocate(collection["fee_cents"],weights)
            delivery_fees+=fees.pop(0,0)
            for pid,fee in fees.items():
                data[pid]["fees"]+=fee
            if collection["rate_bp"] is None:
                warnings.append("Há recebimentos de delivery com taxa desconhecida.")
        obligations=self.db.conn.execute("SELECT * FROM obligations WHERE deleted_at IS NULL AND substr(incurred_on,1,7)=?",(month,)).fetchall()
        operating=sum(r["amount_cents"] for r in obligations if r["source_type"]=="EXPENSE" and r["category"] not in ("DAS MEI","Compra de estoque"))
        das_rows=[r["amount_cents"] for r in obligations if r["category"]=="DAS MEI" and r["source_type"]=="EXPENSE"]
        configured=self.db.conn.execute("SELECT value_cents FROM financial_settings WHERE key='DAS'").fetchone()
        das=sum(das_rows) if das_rows else (configured[0] or 0) if configured else 0
        if not das_rows and (not configured or configured[0] is None):
            warnings.append("DAS ainda não confirmado; resultado incompleto.")
        delivery_cost=self.db.conn.execute("SELECT COALESCE(SUM(fee_cents),0) FROM trips WHERE substr(dispatched_at,1,7)=?",(month,)).fetchone()[0]
        return products,data,operating,das,delivery_revenue,delivery_fees,delivery_cost,sorted(set(warnings))

    def monthly(self,month):
        _,data,operating,das,delivery_rev,delivery_fees,delivery_cost,warnings=self._data(month)
        revenue=sum(r["revenue"] for r in data.values())
        cogs=sum(r["cost"] for r in data.values())
        fees=sum(r["fees"] for r in data.values())
        product=revenue-cogs-fees-operating-das
        return MonthlyResult(revenue,cogs,fees+delivery_fees,operating,das,product,delivery_rev,delivery_cost,product+delivery_rev-delivery_cost-delivery_fees,warnings)

    def profitability(self,month):
        products,data,operating,das,*_=self._data(month)
        data={id:r for id,r in data.items() if any(r.values())}
        weights={id:max(0,r["revenue"]) for id,r in data.items()}
        overhead=allocate(operating+das,weights) if sum(weights.values()) else {id:0 for id in data}
        rows=[]
        for id,r in data.items():
            contribution=r["revenue"]-r["cost"]-r["fees"]
            profit=contribution-overhead[id]
            margin=Decimal(round_half_up(profit*10000,r["revenue"]))/100 if r["revenue"]>0 else None
            rows.append(ProductResult(id,products[id]["name"],r["qty"],r["revenue"],r["cost"],r["fees"],contribution,overhead[id],profit,margin))
        return rows

    def replenishment(self):
        result=[]
        for row in self.db.conn.execute("SELECT p.*,p.stock-COALESCE((SELECT SUM(qty) FROM reservations WHERE product_id=p.id),0) available FROM products p WHERE active=1 ORDER BY name"):
            needed=max(0,row["min_stock"]-row["available"])
            if not needed:
                continue
            packs=(needed+row["pack_size"]-1)//row["pack_size"]
            if row["stock"]:
                cost=round_half_up(row["value_cents"]*packs*row["pack_size"],row["stock"])
            else:
                last=self.db.conn.execute("SELECT total_cents,qty FROM purchase_items WHERE product_id=? ORDER BY id DESC LIMIT 1",(row["id"],)).fetchone()
                cost=round_half_up(last["total_cents"]*packs*row["pack_size"],last["qty"]) if last else 0
            result.append(PurchaseSuggestion(row["id"],row["name"],row["available"],needed,packs,cost))
        return result

    def history(self,filters):
        start,end=valid_date(filters.start),valid_date(filters.end)
        if start>end:
            raise BusinessError("Período inválido.")
        sql="SELECT * FROM audit_events WHERE substr(occurred_at,1,10) BETWEEN ? AND ?"
        args=[start,end]
        if filters.object_id:
            sql+=" AND object_id=?";args.append(str(filters.object_id))
        if not filters.include_deleted:
            sql+=" AND kind NOT LIKE '%deleted%'"
        rows=self.db.conn.execute(sql+" ORDER BY occurred_at DESC,id DESC",args).fetchall()
        result=[]
        for r in rows:
            description=r['reason'] or ''
            if r['kind'] in ('sale.confirmed','delivery.sale'):
                sale=self.db.conn.execute('SELECT * FROM sales WHERE id=?',(r['object_id'],)).fetchone()
                if sale:
                    from ..common.money import money
                    names=[f"{i['qty']} × {i['name']}" for i in self.db.conn.execute('SELECT i.qty,i.name_snapshot name FROM sale_items i WHERE sale_id=?',(sale['id'],))]
                    description=f"Venda #{sale['id']} • {money(sale['total_cents'])} • {sale['method']} • "+', '.join(names)
            result.append(HistoryRow(r['id'],datetime.fromisoformat(r['occurred_at']),r['kind'],r['object_id'],description))
        return result

    def cash_report(self,session_id):
        row=self.db.conn.execute("SELECT * FROM cash_sessions WHERE id=?",(session_id,)).fetchone()
        if row is None:
            raise BusinessError("Caixa não encontrado.")
        facts=self.db.conn.execute('SELECT method,SUM(CASE WHEN delta_cents>0 THEN delta_cents ELSE 0 END) receipts,-SUM(CASE WHEN delta_cents<0 THEN delta_cents ELSE 0 END) refunds,SUM(delta_cents) net FROM receipt_events WHERE session_id=? GROUP BY method',(session_id,)).fetchall()
        payments={r['method']:r['net'] for r in facts}
        receipts={r['method']:r['receipts'] for r in facts}
        refunds={r['method']:r['refunds'] for r in facts}
        entries=[dict(r) for r in self.db.conn.execute("SELECT * FROM cash_entries WHERE session_id=? ORDER BY id",(session_id,))]
        expected=row["expected_cents"] if row["expected_cents"] is not None else row["opening_cents"]+sum(r["delta_cents"] for r in entries)
        return CashReport(session_id,row["opening_cents"],expected,row["counted_cents"] or 0,row["variance_cents"] or 0,row["reason"],payments,entries,receipts,refunds)

    def bundle(self,month):
        start,end=month_range(month);summary=self.monthly(month)
        reais=lambda cents: Decimal(cents)/100
        rows=[["Produto","Quantidade","Faturamento (R$)","CMV (R$)","Taxas (R$)","Contribuição (R$)","Rateio (R$)","Resultado (R$)"]]
        rows += [[r.name,r.qty,*[reais(v) for v in (r.revenue_cents,r.cogs_cents,r.fees_cents,r.contribution_cents,r.allocated_cents,r.profit_cents)]] for r in self.profitability(month)]
        from ..finance.models import ExpenseFilter
        from ..finance.service import FinanceService
        expenses=FinanceService(self.db,None,None).list_expenses(ExpenseFilter(start,end,"incurred",include_deleted=True))
        expense_rows=[["ID","Descrição","Categoria","Valor (R$)","Gasto","Vencimento","Pago (R$)","Excluída"]]
        expense_rows += [[r.id,r.draft.description,r.draft.category,reais(r.draft.amount_cents),r.draft.incurred_on.isoformat(),r.due_on.isoformat(),reais(r.paid_cents),"Sim" if r.deleted_at else "Não"] for r in expenses]
        history=self.history(HistoryFilter(start,end))
        events=[["Data","Evento","ID","Motivo"]]+[[r.occurred_at.isoformat(),r.kind,r.object_id,r.description] for r in history]
        indicators=[("Faturamento de produtos",summary.revenue_cents),("Custo dos produtos",summary.cogs_cents),("Taxas",summary.fees_cents),("Despesas operacionais",summary.operating_cents),("DAS",summary.das_cents),("Resultado dos produtos",summary.product_result_cents),("Taxas de entrega cobradas",summary.delivery_revenue_cents),("Custo das corridas",summary.delivery_cost_cents),("Resultado gerencial total",summary.total_result_cents)]
        result=[["Indicador","Valor (R$)"]]+[[label,reais(value)] for label,value in indicators]
        return ReportBundle(start,end,{"competência":month}, {"Resumo":result,"Lucro por produto":rows,"Despesas":expense_rows,"Auditoria":events},summary.warnings)
