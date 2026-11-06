# Estoque inicial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar estoque inicial já pago e seu valor sem criar compras ou despesas.
**Architecture:** Reutilizar products.value_cents, stock_movements e CommandBus; INITIAL_STOCK identifica a abertura. Serviço transacional e idempotente; formulário e totais em Produtos e estoque.
**Tech Stack:** Python 3.12+, Tkinter, SQLite, unittest.
**Spec:** docs/superpowers/specs/2026-11-05-estoque-inicial-design.md

## Global Constraints
- Quantidade inteira e custo unitário em centavos, ambos positivos na abertura.
- Nenhuma compra, obrigação, despesa ou movimento financeiro.
- Preservar dados e PIN, sem mudança de esquema ou dependências.
- Versão 0.4.4-dev, abertura direta e atalho existentes.

## Review Focus
- Duplicação e retry: uma entrada por produto, chave idempotente.
- Cadastros existentes com histórico: rejeitar sem alterar registros.
- Custo inválido ou PIN recusado: cadastro e saldo atômicos.
- Venda e compra posteriores: custo histórico e média ponderada corretos.
- Tela 1366×768 e banco anterior: controles acessíveis e dados preservados.

### Task 1: Serviço de estoque inicial
Files: salva_ai_v2/inventory/service.py, tests_v2/test_initial_stock.py.
Interfaces: initialize_stock(product_id,qty,unit_cost_cents,grant,command_id)->product_id; create_product_with_initial_stock(name,price_cents,pack_size,min_stock,qty,unit_cost_cents,grant,command_id)->product_id; stock_totals()->dict(initial_value_cents,current_value_cents).
- [ ] Escrever testes para 24×450=10800, nenhum lançamento financeiro, idempotência, autorização, limites, histórico, rollback, custo e totais após consumo/compra.
- [ ] Rodar unittest tests_v2.test_initial_stock -v e observar falhas por métodos ausentes.
- [ ] Implementar validação, proteção stock.adjust e movimento INITIAL_STOCK; transação única na criação; totais distinguem inicial e atual.
- [ ] Verificar testes do serviço e inventário, depois registrar resultado e commit.

### Task 2: Formulários e totalização
Files: salva_ai_v2/ui/products.py, salva_ai_v2/ui/audit.py, tests_v2/test_initial_stock_ui.py.
Consumes: interfaces da Task 1.
Produces: botão Estoque inicial, criação com saldo opcional, custo e valor total visíveis; eventos nomeados em português.
- [ ] Escrever testes reais FormDialog: produto existente sem recadastro; criar com e sem saldo; custo incorreto mantém formulário; cancelamento não altera; PIN; totais e layout.
- [ ] Rodar testes e observar falha antes de implementar.
- [ ] Implementar formulários, confirmação do total calculado no resultado, coluna Valor em estoque e resumo inicial/atual.
- [ ] Testar UI e inventário, conferir imagem em 1366×768, registrar resultado e commit.

### Task 3: Atualização e entrega
Files: versão, distribuição, scripts/documentação/manuais/kit.
Consumes: comportamento final e interfaces anteriores.
- [ ] Testar atualização de cópia 0.4.3 com produtos, PIN e compras existentes preservados.
- [ ] Bump 0.4.4-dev, atualizar documentação e capturar novas telas fictícias.
- [ ] Rodar suíte completa tests_v2 e legado em Xvfb; conferir saída e contagens.
- [ ] Revisão independente final do diff e riscos financeiros; corrigir bloqueios com RED→GREEN.
- [ ] Gerar ZIP, PDFs e kit com manifesto, sem banco; testar entrada extraída e verificar downloads; commit e push na feature branch já autorizada.
