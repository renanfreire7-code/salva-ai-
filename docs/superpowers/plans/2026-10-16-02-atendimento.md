# Estoque e atendimento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Executar compra, venda direta e comanda com custo médio, promoções, reserva e caixa.

**Architecture:** Serviços de inventário e preço alimentam atendimento e caixa. Obrigações de compras nascem em tabela comum; o plano 03 acrescenta edição/pagamento sem repetir a criação.

**Tech Stack:** Python 3, Tkinter/ttk, SQLite, unittest e XlsxWriter já incluído no projeto.

**Spec:** [Especificação aprovada](../specs/2026-10-16-salva-ai-novo-design.md). Ler também o [plano geral](2026-10-16-salva-ai-plano-geral.md).

## Global Constraints

- Python 3, Tkinter/ttk e SQLite; Windows prioritário; funcionamento offline.
- Um dispositivo, um operador e aproximadamente 20 produtos.
- Venda em unidades inteiras de produtos fechados; sem receitas, doses ou ingredientes.
- Dinheiro, Pix, débito e crédito apenas à vista; um meio por venda.
- Sem fiado, descontos manuais ou pagamentos divididos.
- Promoções por quantidade são a exceção de preço explicitamente autorizada.
- Sem servidor, dependência de internet para vender ou serviços pagos obrigatórios.
- Sem emissão fiscal, conciliação bancária ou promessa de lucro contábil oficial.
- Sem merge, release ou publicação externa sem autorização.
- Banco vazio e diretório próprio; nunca abrir o banco antigo nem usar dados reais nos testes.
- Operações e auditoria atômicas; dinheiro exato, custódia separada de receita.
- Nenhuma contagem de testes planejados equivale a testes já executados.
- Checkout já isolado: não criar worktree sem pedido explícito; implementação em branches de funcionalidade derivadas da branch de desenho.



## Review Focus

- Quantidade zero, negativa, fracionária ou maior que disponível: recusar sem escrita — tarefas 1 e 4.
- Custo unitário menor que um centavo: conservar valoração total — tarefa 1.
- Desativação com item reservado: manter comanda pagável e impedir novas inclusões — tarefa 4.
- Promoção alterada e item removido/reincluído: preservar condição — tarefas 2 e 4.
- Clique repetido ou falha no último INSERT: uma venda ou nenhuma — tarefa 4.

## Dependências e contratos

Depende do plano 01. Tipos comuns deste plano:
`StockPosition(product_id: int, physical: int, reserved: int, available: int, value_cents: int)`;
`PriceCondition(unit_cents: int, group_qty: int | None, group_cents: int | None)`;
`CartLine(product_id: int, qty: int)` em inventory/models.py, reexportado por sales/models.py;
`Payment(method: str, tendered_cents: int | None)`, métodos MONEY/PIX/DEBIT/CREDIT;
`SaleResult(id: int, total_cents: int, change_cents: int)`.
Definir cada dataclass no models.py do módulo proprietário. Services é definido em bootstrap.py; acrescentar serviços à composição conforme forem implementados. Para correções/devoluções de compras, uma obrigação reduzida não apaga pagamentos existentes: eventual crédito ao bar permanece identificado até confirmação de recebimento.
### Tarefa 1: Inventário, entrada valorizada e compra vinculada

**Files:** Create: `inventory/{__init__,models,service,queries}.py`, `migrations/003_inventory.sql`, `tests_v2/test_inventory.py`; Modify: `tests_v2/support.py`.

**Interfaces:** `InventoryService(db, security)`; `create_product(name: str, price_cents: int, pack_size: int, min_stock: int, command_id: str) -> int`; `receive_purchase(lines: list[PurchaseLine], freight_cents: int, incurred_on: date, due_on: date, command_id: str) -> int`; `position(product_id: int) -> StockPosition`; `adjust(product_id: int, delta: int, reason: str, grant: AdminGrant, command_id: str) -> None`; `deactivate(product_id: int, grant: AdminGrant, reason: str, command_id: str) -> None`. `PurchaseLine(product_id: int, qty: int, total_cents: int)`.

- [x] **1. Escrever testes que falham.** Testar compra 10 unidades/R$20 + 10/R$40, frete por rateio, quantidade inválida, compra repetida e obrigação única. Criar ledger de custo e saída proporcional com residual na última unidade; testar 3 unidades com custo total de 1 centavo. Adicionar Fixture.create_product/receive e relógio fixo em support.py, chamando serviços reais.

```python
pid = self.inventory.create_product("Lata", 500, 12, 6, "p1")
self.receive(pid, 10, 2000, "buy1")
self.receive(pid, 10, 4000, "buy2")
self.assertEqual(self.inventory.position(pid).value_cents, 6000)
self.assertEqual(self.inventory.position(pid).physical, 20)
self.assertEqual(self.scalar("SELECT COUNT(*) FROM obligations"), 2)
```

- [x] **2. Executar antes de implementar.** `python3 -m unittest tests_v2.test_inventory -v`
  Esperado: falha por comportamento ausente; corrigir falha de coleta/configuração antes do ciclo.
- [x] **3. Implementar.** Migração define products, stock_movements, purchases/purchase_items e obligations com source_type/source_id únicos. A obrigação contém amount_cents, incurred_on, due_on, category, deleted_at e fonte; compras não são despesas operacionais. Não usar finance service futuro: emitir obrigação na mesma unidade de trabalho. Preparar `consume(product_id: int, qty: int) -> int` e `reserve/release(product_id: int, owner_type: str, owner_id: int, qty: int) -> None` como operações internas dentro da transação do chamador. Custo devolvido por consume é o total histórico em centavos. Adicionar `reverse_purchase(purchase_id: int, grant: AdminGrant, reason: str, command_id: str) -> None` apenas se as unidades não foram consumidas; para correção posterior, ajuste auditado sem reescrever vendas. `return_to_supplier(purchase_id: int, lines: list[CartLine], grant: AdminGrant, reason: str, command_id: str) -> int` gera devolução e crédito financeiro identificados, sem assumir dinheiro recebido. Acrescentar testes que rejeitam devolução acima do disponível/reservado, conservam CMV passado e impedem crédito duplicado; CartLine é definido em inventory/models.py e reexportado por sales/models.py.
- [x] **4. Executar novamente.** `python3 -m unittest tests_v2.test_inventory -v`
  Esperado: todos os testes desse alvo executados, sem falhas nem pulos; executar também a suíte
  acumulada `python3 -m unittest discover -s tests_v2 -t .` (usar Xvfb se houver UI).
- [x] **5. Revisar e registrar.** `git diff --check`; revisar arquivos da tarefa,
  adicionar somente esses arquivos e fazer commit `feat: controla estoque valorizado e compras`. Não fazer push/merge.

### Tarefa 2: Preço promocional congelado

**Files:** Create: `pricing/{__init__,models,service}.py`, `migrations/004_pricing.sql`, `tests_v2/test_pricing.py`.

**Interfaces:** `PricingService(db)`; `set_promotion(product_id: int, group_qty: int, group_cents: int, active: bool, command_id: str) -> None`; `snapshot(product_id: int) -> PriceCondition`; `quote(condition: PriceCondition, qty: int) -> PriceQuote`; `PriceQuote(total_cents: int, savings_cents: int)`. Condições guardadas por proprietário de pedido e produto, inclusive após remoção.

- [x] **1. Escrever testes que falham.** Testar 1/2/3/4/6 unidades para R$5 e 3/R$12, produtos não combinados, grupo inválido, total promocional que não dá economia e condição antiga após alteração. Promoção válida exige grupo >=2 e preço total positivo inferior ao preço normal do grupo.

```python
condition = PriceCondition(500, 3, 1200)
self.assertEqual([self.pricing.quote(condition, n).total_cents for n in (1,2,3,4,6)],
                 [500,1000,1200,1700,2400])
self.assertEqual(self.pricing.quote(condition, 4).savings_cents, 300)
```

- [x] **2. Executar antes de implementar.** `python3 -m unittest tests_v2.test_pricing -v`
  Esperado: falha por comportamento ausente; corrigir falha de coleta/configuração antes do ciclo.
- [x] **3. Implementar.** Calcular grupos com divmod, sem preço unitário promocional em float. Uma promoção ativa por produto; edição de cadastro não altera snapshot de atendimento. Só criar permissões adicionais se previstas na especificação ou revistas pelo responsável.
- [x] **4. Executar novamente.** `python3 -m unittest tests_v2.test_pricing -v`
  Esperado: todos os testes desse alvo executados, sem falhas nem pulos; executar também a suíte
  acumulada `python3 -m unittest discover -s tests_v2 -t .` (usar Xvfb se houver UI).
- [x] **5. Revisar e registrar.** `git diff --check`; revisar arquivos da tarefa,
  adicionar somente esses arquivos e fazer commit `feat: aplica promocao por grupos completos`. Não fazer push/merge.

### Tarefa 3: Caixa aberto e movimentos

**Files:** Create: `cash/{__init__,models,service,queries}.py`, `migrations/005_cash.sql`, `tests_v2/test_cash.py`.

**Interfaces:** `CashService(db, security, clock)`; `open(opening_cents: int, command_id: str) -> int`; `move(kind: str, amount_cents: int, reason: str, grant: AdminGrant, command_id: str) -> int`; `position(session_id: int) -> CashPosition`; `blockers(session_id: int) -> list[str]`; `CashPosition(expected_cents: int)`. Escritas de recebimentos/saídas vinculadas usam funções internas da mesma transação, sem exigir grant novamente.

- [x] **1. Escrever testes que falham.** Testar abertura única, troco inicial negativo, reforço/retirada positivos, saldo insuficiente, ID repetido e modalidade sem dinheiro físico. Preparar blockers para comandas, delivery, reembolsos e artefatos de fechamento pendentes; consultar tabelas opcionais só após migração correspondente.

```python
session = self.cash.open(10000, "open1")
self.cash.move("WITHDRAWAL", 2000, "Retirada teste", self.withdraw_grant(), "move1")
self.assertEqual(self.cash.position(session).expected_cents, 8000)
with self.assertRaises(BusinessError):
    self.cash.move("WITHDRAWAL", 9000, "Saldo insuficiente", self.withdraw_grant(), "move2")
```

- [x] **2. Executar antes de implementar.** `python3 -m unittest tests_v2.test_cash -v`
  Esperado: falha por comportamento ausente; corrigir falha de coleta/configuração antes do ciclo.
- [x] **3. Implementar.** Tabelas cash_sessions e cash_entries; restrição de sessão ativa única (OPEN ou CLOSING). Movimentos imutáveis, vínculos únicos e custódia explícita. Fechamento final entra no plano 05; nesta etapa demonstrar abertura/posição sem oferecer fechamento falso. `blockers` integra delivery no plano 04.
- [x] **4. Executar novamente.** `python3 -m unittest tests_v2.test_cash -v`
  Esperado: todos os testes desse alvo executados, sem falhas nem pulos; executar também a suíte
  acumulada `python3 -m unittest discover -s tests_v2 -t .` (usar Xvfb se houver UI).
- [x] **5. Revisar e registrar.** `git diff --check`; revisar arquivos da tarefa,
  adicionar somente esses arquivos e fazer commit `feat: registra abertura e movimentos de caixa`. Não fazer push/merge.

### Tarefa 4: Vendas, comandas e correções rastreáveis

**Files:** Create: `sales/{__init__,models,service,queries}.py`, `migrations/006_sales.sql`, `tests_v2/test_sales.py`, `tests_v2/test_tabs.py`.

**Interfaces:** `SalesService(db, inventory, pricing, cash, security)`; `create_tab(name: str, command_id: str) -> int`; `set_tab_qty(tab_id: int, product_id: int, qty: int, grant: AdminGrant | None, reason: str | None, command_id: str) -> None`; `pay_tab(tab_id: int, payment: Payment, command_id: str) -> SaleResult`; `create_cart(command_id: str) -> int`; `set_cart_qty(cart_id: int, product_id: int, qty: int, command_id: str) -> None`; `sell(cart_id: int, payment: Payment, command_id: str) -> SaleResult`; `cancel_tab(tab_id: int, grant: AdminGrant, reason: str, command_id: str) -> None`; `reverse_sale(sale_id: int, return_items: bool, refund: Payment | None, reopen_tab: bool, grant: AdminGrant, reason: str, command_id: str) -> int`.

- [x] **1. Escrever testes que falham.** Testar venda repetida após reinício, pagamento insuficiente, estoque reservado, rollback ao falhar auditoria e custo congelado. Confirmar redução com PIN, nome igual sinalizado e preço persistente após reincluir. Desativação permite receber itens previamente reservados, mas não aumentar/adicionar. Pós-fechamento: correção no caixa atual sem alterar o original; abrir comanda antiga novamente deve falhar.

```python
tab = self.sales.create_tab("João", "tab1")
self.sales.set_tab_qty(tab, self.pid, 3, None, None, "add1")
self.assertEqual(self.inventory.position(self.pid).reserved, 3)
sale = self.sales.pay_tab(tab, Payment("MONEY", 2000), "pay1")
self.assertEqual((sale.total_cents, sale.change_cents), (1200, 800))
self.assertEqual(self.inventory.position(self.pid).reserved, 0)
self.assertEqual(self.sales.pay_tab(tab, Payment("MONEY", 2000), "pay1"), sale)
```

- [x] **2. Executar antes de implementar.** `python3 -m unittest tests_v2.test_sales tests_v2.test_tabs -v`
  Esperado: falha por comportamento ausente; corrigir falha de coleta/configuração antes do ciclo.
- [x] **3. Implementar.** Guardar condições, custos e taxas nos itens/venda; métodos de pagamento únicos. CMV consome estoque somente uma vez e libera reserva. Condições de carrinho precisam ser snapshots persistidos pelos serviços: não aceitar preços arbitrários passados pela tela. A lista de condições é interna, consultada pelo cart_id; set_cart_qty congela a condição na primeira inclusão. `_record_sale` é função interna reutilizável pelo delivery, com parâmetros de receita, custódia e origem; não impõe baixa duplicada. Reverse registra correção, devolução física e reembolso como fatos distintos; pagamento digital apenas confirmado manualmente, nunca simular transferência. Definir taxas em payment_settings, distinguindo desconhecido de zero. Testar payload de preço adulterado: rejeitar ou ignorar e usar snapshot interno, nunca criar desconto manual.
- [x] **4. Executar novamente.** `python3 -m unittest tests_v2.test_sales tests_v2.test_tabs -v`
  Esperado: todos os testes desse alvo executados, sem falhas nem pulos; executar também a suíte
  acumulada `python3 -m unittest discover -s tests_v2 -t .` (usar Xvfb se houver UI).
- [x] **5. Revisar e registrar.** `git diff --check`; revisar arquivos da tarefa,
  adicionar somente esses arquivos e fazer commit `feat: conclui vendas e comandas atomicamente`. Não fazer push/merge.

### Tarefa 5: Telas de atendimento, produtos e caixa

**Files:** Create: `ui/{products,sales,tabs,cash}.py`, `tests_v2/test_attendance_ui.py`, `scripts/demo_v2.py`; Modify: `ui/app.py`, `docs/manual-v2.md`.

**Interfaces:** `ProductsView(parent, services)`, `SalesView(parent, services)`, `TabsView(parent, services)`, `CashView(parent, services)`; services é dataclass de bootstrap com atributos inventory/pricing/sales/cash/security/clock. Cada view expõe `refresh()`; callbacks chamam somente serviços.

- [x] **1. Escrever testes que falham.** Usar Tk real e banco temporário; busca sem acento/código, F1–F12 apenas seleciona produto, Enter confirma somente no contexto explícito. Testar preservação de campos após erro, nome duplicado, promoção visível e foco após venda. Desativar botões durante confirmação, mantendo proteção persistente. Criar atalhos persistentes únicos com 1–12.

```python
view = self.app.sales_view
view.add_product(self.pid, 3)
self.assertEqual(view.total_cents, 1200)
self.assertEqual(self.scalar("SELECT COUNT(*) FROM sales"), 0)
view.submit(Payment("MONEY", 2000))
self.assertEqual(self.scalar("SELECT COUNT(*) FROM sales"), 1)
self.assertEqual(view.total_cents, 0)
```

- [x] **2. Executar antes de implementar.** `PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest tests_v2.test_attendance_ui -v`
  Esperado: falha por comportamento ausente; corrigir falha de coleta/configuração antes do ciclo.
- [x] **3. Implementar.** Antes de editar UI, aplicar Impeccable às restrições nativas e ler craft-floor; preservar Operate e foco no atendimento. Definir `add_product`, `submit`, `total_cents` como interface do controlador da view. Demo usa --data-dir temporário, seed explícito e jamais dados reais. Incluir custo médio, compras e cadastro de promoções nas telas; resumo e PIN para movimentos. Fechamento só fica habilitado quando plano 05 concluído.
- [x] **4. Executar novamente.** `PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest tests_v2.test_attendance_ui -v`
  Esperado: todos os testes desse alvo executados, sem falhas nem pulos; executar também a suíte
  acumulada `python3 -m unittest discover -s tests_v2 -t .` (usar Xvfb se houver UI).
- [x] **5. Revisar e registrar.** `git diff --check`; revisar arquivos da tarefa,
  adicionar somente esses arquivos e fazer commit `feat: entrega atendimento e estoque na interface`. Não fazer push/merge.
