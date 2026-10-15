"""Relatórios locais em XLSX sem bibliotecas extras."""
from datetime import datetime
from pathlib import Path

def xlsx(path, sheets):
    """Gera um arquivo XLSX compatível usando XlsxWriter incluído no aplicativo."""
    import xlsxwriter
    book = xlsxwriter.Workbook(str(path), {'strings_to_urls': False})
    head = book.add_format({'bold': True, 'bg_color': '#E8F2FA', 'font_color': '#153E5C', 'border': 1})
    reais = book.add_format({'num_format': 'R$ #,##0.00'})
    try:
        for name, data in sheets:
            ws = book.add_worksheet(name[:31])
            ws.freeze_panes(1, 0)
            ws.set_column(0, max((len(row) for row in data), default=1)-1, 22)
            for r, values in enumerate(data):
                for c, value in enumerate(values):
                    if value is None: value = ''
                    if r == 0:
                        ws.write(r, c, str(value), head)
                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                        # Mantém valores numéricos como números para filtros e cálculos.
                        if isinstance(value, float) and ('R$' in str(data[0][c])):
                            ws.write_number(r, c, value, reais)
                        else:
                            ws.write_number(r, c, value)
                    else:
                        ws.write_string(r, c, str(value))
            if data:
                ws.autofilter(0, 0, max(0,len(data)-1), max(0,len(data[0])-1))
    finally:
        book.close()
    return Path(path)

def export(store, path):
    money=lambda n: n/100
    products=[['Código','Produto','Preço (R$)','Custo unitário atual (R$)','Estoque mínimo','Estoque físico','Reservado','Disponível','Unidades por caixa']]
    for p in store.products(): products.append([p['id'],p['name'],money(p['price']),money(p['cost']),p['min_stock'],p['stock'],p['stock']-p['available'],p['available'],p['pack_size']])
    sales=[['Venda nº','COMANDA Nº','Data','Cliente','Pagamento','Total (R$)','Taxa (R$)','Taxa (%)','Caixa','Situação']]
    for v in store.fetch('SELECT s.*, COALESCE(t.customer,"Venda direta") cliente FROM sales s LEFT JOIN tabs t ON t.id=s.tab_id ORDER BY s.id'):
        sales.append([v['id'],v['tab_id'] if v['tab_id'] is not None else 'Venda direta',v['sold_at'],v['cliente'],v['payment'],money(v['total']),money(v['payment_fee']) if v['payment_fee'] is not None else 'Não registrada', v['payment_rate_bp']/100 if v['payment_rate_bp'] is not None else 'Não registrada',v['session_id'],'ESTORNADA' if v['voided_at'] else 'VÁLIDA'])
    items=[['Venda nº','COMANDA Nº','Produto','Quantidade','Preço unitário (R$)','Custo histórico unitário (R$)','Subtotal (R$)']]
    for v in store.fetch('SELECT i.*,p.name,s.tab_id FROM sale_items i JOIN products p ON p.id=i.product_id JOIN sales s ON s.id=i.sale_id ORDER BY i.id'):
        items.append([v['sale_id'],v['tab_id'] if v['tab_id'] is not None else 'Venda direta',v['name'],v['qty'],money(v['unit_price']),money(v['cost_at_sale']) if v['cost_at_sale'] is not None else 'Não registrado',money(v['qty']*v['unit_price'])])
    movements=[['Data','Produto','Variação (unidades)','Motivo','Venda']]
    for m in store.fetch('SELECT m.*,p.name FROM stock_movements m JOIN products p ON p.id=m.product_id ORDER BY m.id'):
        movements.append([m['movement_at'],m['name'],m['delta'],m['reason'],m['sale_id'] or ''])
    cash=[['Caixa','Abertura','Fechamento','Troco inicial (R$)','Dinheiro contado (R$)','Backup']]
    for s in store.fetch('SELECT * FROM cash_sessions ORDER BY id'):
        cash.append([s['id'],s['opened_at'],s['closed_at'] or 'ABERTO',money(s['opening_cash']),money(s['counted_cash']) if s['counted_cash'] is not None else '',s['backup_path'] or ''])
    expenses=[['ID','Descrição','Categoria','Valor (R$)','Data do gasto','Vencimento','Pago em']]
    for e in store.fetch('SELECT * FROM expenses ORDER BY id'): expenses.append([e['id'],e['description'],e['category'],money(e['amount']),e['incurred_date'],e['due_date'],e['paid_at'][:10] if e['paid_at'] else 'PENDENTE'])
    forecast=[['Produto','Disponível','Mínimo','Unidades por caixa','Caixas sugeridas','Unidades sugeridas','Custo estimado (R$)']]
    from finance import replenish
    for r in replenish(store): forecast.append([r['name'],r['available'],r['min_stock'],r['pack_size'],r['packs'],r['units'],money(r['estimated'])])
    events=[['Data','Evento','ID','Motivo']]
    for e in store.fetch('SELECT * FROM finance_events ORDER BY id'): events.append([e['event_at'],e['kind'],e['object_id'],e['description']])
    tabs=[['COMANDA Nº','Cliente','Situação','Abertura','Fechamento','Última venda nº','Caixa nº']]
    for t in store.fetch("""SELECT t.*, (SELECT MAX(s.id) FROM sales s WHERE s.tab_id=t.id) sale_id,
           (SELECT s.session_id FROM sales s WHERE s.tab_id=t.id ORDER BY s.id DESC LIMIT 1) cash_id
           FROM tabs t ORDER BY t.id"""):
        tabs.append([t['id'],t['customer'],t['status'],t['opened_at'],t['closed_at'] or '',t['sale_id'] or '',t['cash_id'] or ''])
    from finance import profitability, get_payment_rates, get_setting
    month=datetime.today().strftime('%Y-%m')
    data,summary=profitability(store,month)
    profit=[['Produto','Qtd.','Faturamento (R$)','CMV (R$)','Taxas (R$)','Contribuição (R$)','Rateio despesas + DAS (R$)','Lucro estimado (R$)','Margem (%)']]
    for r in data:
        profit.append([r['name'],r['qty'],money(r['revenue']),money(r['cmv']),money(r['fee']),
                       money(r['contribution']),money(r['allocated']),money(r['profit']),round(r['margin'],2)])
    profit.append(['RESULTADO MENSAL','','','','','','',money(summary['estimated_profit']),''])
    profit.append(['Atenção: indicadores gerenciais; impostos, custos e repasses dependem dos dados informados.','','','','','','','',''])
    settings=[['Parâmetro','Valor'],['Mês analisado',month],['DAS mensal configurado (R$)',money(get_setting(store,'mei_das_monthly')) if get_setting(store,'mei_das_monthly') is not None else 'Não configurado']]
    for key,val in get_payment_rates(store).items(): settings.append(['Taxa '+key+' (%)',val/100])
    return xlsx(path,[('Produtos',products),('Comandas',tabs),('Vendas',sales),('Itens vendidos',items),('Estoque',movements),('Caixas',cash),('Despesas',expenses),('Lucro por produto',profit),('Configurações',settings),('Reposição prevista',forecast),('Auditoria',events)])

# A exportação de histórico acima mantém o esquema original para compatibilidade.
