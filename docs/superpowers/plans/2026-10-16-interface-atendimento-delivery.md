# Interface, Atendimento e Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execução nativa nesta sessão e revisão independente final aprovadas pelo usuário.

**Goal:** Entregar 0.2.0-dev com todas as mudanças aprovadas de interface/teclado/histórico/delivery, preservando dados e regras financeiras.
**Architecture:** Migração aditiva e snapshots; serviços transacionais existentes; consultas comerciais/delivery compartilhadas; componentes de formulários/período/teclado e shell lateral; PNGs locais.
**Tech Stack:** Python 3.12+, Tkinter/ttk, SQLite, unittest, Xvfb no Linux, XlsxWriter já incluído.
**Spec:** [Especificação aprovada](../specs/2026-10-16-interface-atendimento-delivery-design.md).

Documento restaurado do plano de 10 tarefas aprovado na conversa, após nova
máquina recuperar apenas a branch remota cdf6c55. Nenhuma nova aprovação exigida.

## Global Constraints

- Mesma pasta de dados, IDs/PIN/auditoria/transações/replay/reservas/promoções/custos/backup; testar só dados fictícios.
- Migração após013; não alterar migrações antigas. Dinheiro inteiro em centavos, crédito à vista, sem fiado/descontos/pagamentos divididos.
- Link externo com confirmação manual, nenhuma API/servidor/pip obrigatório.
- Previsão de troco não é transferência/recebimento; atalhos não adicionam/vendem automaticamente.
- Menu lateral, SALVA AI HEADSHOP, logo à direita, moto no Delivery; 1366×768, Windows100%/125% ainda externo.
- Checkout já isolado; sem worktree extra. Envio de código/ZIP à branch autorizado; sem main/merge/release.
- TDD por tarefa, commit e registro; uma revisão independente final, um lote de correções importantes.
- Ler craft-floor antes de UI. Assets no pacote; preservar original da logo fornecida pelo usuário.

## Review Focus

1. F1/Enter em editor/modal/PIN: somente destino correto, sem ação no fundo — tarefas3/7.
2. Pedido/replay antigo após reinício: compatibilidade e fingerprint sem novas exigências retroativas — tarefas1/2.
3. Comanda reaberta/produto renomeado: vendas distintas e nomes/valores preservados — tarefas1/4/8.
4. Virada do dia/troco real diferente: pedido ativo visível, conferência e dinheiro conservado — tarefas2/7/9.
5. Acerto parcial de vários pedidos/corridas/antecipados/cancelados: sem joins multiplicadores nem perda de vínculos liquidados — tarefas4/8.

## Verificações e interfaces comuns

Backend: `python3 -m unittest <módulos> -v`. UI: prefixar com
`PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24'`.
Suíte completa: `python3 -m unittest discover -s tests_v2 -t .`; legado: `python3 -m unittest discover -s tests -t .`, ambos com display.
Guardar logs fora do checkout; ler contagens/códigos de saída, sem pulos como prova.

Serviços mantêm command_id estável por intenção; novas informações são parte do
payload de novos comandos, mas padrões de chamadas antigas não mudam fingerprints.
Bootstrap conserva `views`, atributos públicos das views e `show_view(view)`.

## Tarefa1: Migração e snapshots

**Files:** migrations/014_service_experience.sql; sales/service.py; delivery/service.py; reporting/queries.py; tests_v2/test_experience_upgrade.py e test_migrations.py.
**Interfaces:** order_items/sale_items.name_snapshot; delivery_orders.payment_timing='UNSPECIFIED', payment_channel=None, change_for_cents=None, link_reference=''. Sales.lines preserva `name`, agora congelado.

- [ ] 1. Escrever testes: fixture001–013 preenchida, atualização/backup/PIN/IDs/saldos preservados; nome continua após renomear/remover/reincluir e comanda reaberta não altera venda anterior.
- [ ] 2. Rodar test_experience_upgrade/test_migrations: esperado RED por campos/snapshots ausentes.
- [ ] 3. Implementar migração aditiva, backfill por nome disponível, inserts com colunas explícitas; snapshot na primeira inclusão e cópia para venda. Nenhum valor antigo recalculado.
- [ ] 4. Rodar mesmos testes e test_sales/test_tabs/test_delivery/test_review_regressions: GREEN; suíte acumulada antes de concluir.
- [ ] 5. diff --check; commit `feat: preserva nomes historicos e prepara dados de atendimento`; registrar ledger.

## Tarefa2: Pagamento combinado e troco

**Files:** delivery/payment_plan.py, models.py, service.py, receipts.py, cancellation.py; test_delivery_payment_plan.py.
**Interfaces:** DeliveryDraft acrescenta campos da migração ao final; validate_plan(draft,total_cents), expected_change(total_cents,change_for_cents); record_payment(...,command_id,*,confirm_change_difference=False). DeliveryOrder atual preservado.

- [ ] 1. Testar R$45/R$50/R$5 previsto sem dinheiro movido; fundo insuficiente bloqueia saída sem corrida; enviar fundo permite; real diferente exige confirmação/fundo suficiente. Antecipado pendente bloqueia saída, Pix/link confirmado não mexe gaveta; LINK aceita Débito/Crédito, digital só BAR. Replay antigo após reabrir DB preserva resultado/fingerprint. Reexpedição recalcula plano/troco com total atual.
- [ ] 2. Rodar test_delivery_payment_plan: RED pelo comportamento ausente.
- [ ] 3. Implementar timing ADVANCE/ON_DELIVERY, channel PIX/LINK/MONEY/DEBIT/CREDIT, validação de total e troco. UNSPECIFIED preserva operações antigas; omitir extensão padrão dos payloads antigos. Validar custódia antes de expedir novos não pagos com troco; não reservar/transferir previsão. Receber fato real e auditar discrepância, sem alterar combinado.
- [ ] 4. Rodar alvo e test_delivery/test_delivery_cancellation/test_delivery_settlement/test_review_regressions: GREEN e suíte acumulada.
- [ ] 5. diff --check; commit `feat: registra pagamento combinado e troco previsto do delivery` e ledger.

## Tarefa3: Busca, formulários e foco

**Files:** inventory/queries.py; ui/forms.py, keyboard.py, shared.py; test_product_search.py, test_form_keyboard.py.
**Interfaces:** search_products(products,query); FieldSpec(name,label,initial='',kind='text',choices=(),required=False,validator=None); ask_fields(parent,title,fields,*,on_submit=None), tuples antigos aceitos; ShortcutRouter(root,current_picker).register(window,picker).

- [ ] 1. Testar CHL/cer hei/código/acentos/ambiguidade; Enter valida/avança/pula desabilitado/multiline/foca Salvar sem submeter; callback falho mantém dados. F1 no editor não atua no fundo; PIN/modal não registrado bloqueia; quantidade Enter adiciona uma vez.
- [ ] 2. Rodar test_product_search/test_form_keyboard com Xvfb: RED esperado.
- [ ] 3. Implementar normalização/prefixos/iniciais e ordem estável; escolha explícita em ambiguidade. Seletores reais, erros por campo, callbacks fecham só após sucesso; eventos tratados retornam break e respeitam foco/grab. Manter ProductPicker APIs.
- [ ] 4. GREEN dos alvos, test_attendance_ui/test_finance_ui/test_security e acumulado.
- [ ] 5. diff --check; commit `feat: unifica busca por iniciais e navegacao por teclado`; ledger.

## Tarefa4: Consultas comerciais e acerto

**Files:** reporting/commerce.py, commerce_models.py; delivery/queries.py; bootstrap.py; test_commerce_history.py, test_delivery_details.py.
**Interfaces:** CommerceFilter(start,end,kind=None,state=None,text=''); CommerceRow(key,kind,order_id,sale_id,customer,occurred_at,total_cents,state,paid_cents); CommerceItem(product_id,name,qty,unit_cents,group_qty,group_cents,total_cents). CommerceQueries.list(filters), detail(key) com row/items/delivery/refunds; key sale:id ou delivery:id. DeliveryQueries.detail(order_id), settlement_orders(pending_only=True), settlements(), settlement_detail(id). Compor services.commerce/delivery_queries.

- [ ] 1. Testar tipos/IDs colidentes, comanda reaberta, cancelado pré-saída, nomes congelados, filtros seguros e datas corretas. Acerto45/7 parcial20 e depois18+7: entregue38, compensado7, sem duplicação. Incluir Pix antecipado/cancelado/nova tentativa e acertos anteriores.
- [ ] 2. Rodar test_commerce_history/test_delivery_details: RED consultas ausentes.
- [ ] 3. Implementar SQL parametrizado e agregações separadas; detalhe contém order/items/payment_plan/collections/trips/returns/refunds/settlements/custody_pending_cents. Não escrever nem calcular pagamento por combinado.
- [ ] 4. GREEN alvo, test_results/test_delivery_settlement/test_review_regressions e acumulado.
- [ ] 5. diff --check; commit `feat: consulta historico comercial e detalhes de entregas e acertos`; ledger.

## Tarefa5: Identidade e shell lateral

**Files:** ui/theme.py, navigation.py, assets.py, app.py, bootstrap.py; assets/logo.png, motorcycle.png; test_navigation.py, test_layout.py.
**Interfaces:** NavigationShell(parent,groups,on_select).show(view), selected_view; load_asset(master,name,max_size)->PhotoImage. Atributos públicos de Application preservados; acrescentar purchases_view/monthly_view.

- [ ] 1. Testar todos os destinos/seleção, título SALVA AI HEADSHOP, assets offline e carrinho preservado; ações dentro de1260×680 e inspeção em escala Tk ampliada.
- [ ] 2. RED test_navigation/test_layout sob Xvfb.
- [ ] 3. Tema Operate e shell, cabeçalho logo56px/moto24px. Preservar original logo e incluir cópia; gerar moto via ferramenta de imagens, sem emoji/rede em execução. Carregar PNG com Tk e manter referências; substituir notebooks, integrar router, destinos novos funcionais sem placeholders.
- [ ] 4. GREEN alvo/bootstrap/attendance_ui/finance_ui/delivery_ui e acumulado.
- [ ] 5. diff --check; commit `feat: aplica identidade e navegacao lateral ao Salva AI Headshop`; ledger.

## Tarefa6: Balcão, comandas e produtos

**Files:** ui/sales.py,tabs.py,products.py,purchases.py,payment.py; test_checkout_experience.py,test_attendance_ui.py.
**Interfaces:** SalesView.add_product/submit/total_cents e ask_payment(parent,total)->Payment|None preservados; PaymentDialog com seletor/modalidade; purchase_history direciona destino próprio.

- [ ] 1. Testar busca/atalho, pedido/total/economia visíveis, foco; Pix dispensa recebido;12 com20 mostra8; inválido mantém formulário/carrinho. Comanda conserva seleção/PIN em redução. Cadastro Enter e erro mantém nome; devolução/crédito continuam.
- [ ] 2. RED test_checkout_experience/test_attendance_ui sob Xvfb.
- [ ] 3. Pedido lateral, Receber fixo, seletores e resumo; formularários com callbacks sem perda de dados; compras como destino próprio sem mudar serviços. Adaptar expectativas de navegação dos testes preservando assertivas financeiras.
- [ ] 4. GREEN alvo/sales/tabs/inventory/pricing/obligation_payments e acumulado.
- [ ] 5. diff --check; commit `feat: simplifica balcao comandas e cadastro de produtos`; ledger.

## Tarefa7: Editor e recebimento do delivery

**Files:** ui/delivery.py,delivery_editor.py,delivery_receipt.py; test_delivery_experience.py,test_delivery_ui.py.
**Interfaces:** DeliveryEditor ProductPicker registrado no router; DeliveryReceiptDialog usa flag de discrepância; tree mantém Situação e Pagamento separados.

- [ ] 1. Testar F1/Enter no editor sem atuar no fundo; seletores antecipado/entrega, troco50 para45 mostra5; trocar Pix limpa campo incompatível; antecipado pendente pode salvar, não sair; discrepância exige resumo, estoque inválido mantém endereço/itens.
- [ ] 2. RED test_delivery_experience/test_delivery_ui.
- [ ] 3. Separar componentes, validar plano/total, mostrar combinado/real; URL é registro, não pagamento automático. Ações conforme estado; fundo pelos serviços existentes, sem duplicar baixa/corrida.
- [ ] 4. GREEN alvo/payment_plan/cancellation/settlement/form_keyboard e acumulado.
- [ ] 5. diff --check; commit `feat: organiza formulario e recebimento do delivery com troco`; ledger.

## Tarefa8: Histórico comercial e acerto detalhado

**Files:** ui/history.py,audit.py,order_details.py,settlement.py,delivery.py,bootstrap.py; test_history_experience.py,test_settlement_experience.py.
**Interfaces:** HistoryView usa services.commerce; OrderDetails.show(key); AuditView preserva filtros/backup/restore/estorno/reembolso. SettlementView usa conjuntos separados de IDs e serviço settle existente, consulta anteriores.

- [ ] 1. Testar tipos/itens/números humanos, reabertura/estornos, auditoria acessível; acerto por clique sem Ctrl, Pix com corrida sem custódia, dinheiro com troco, cancelado devedor e consulta parcial/concluída com vínculos corretos.
- [ ] 2. RED test_history_experience/test_settlement_experience.
- [ ] 3. Painéis ajustáveis, checkbox/estado textual, resumo físico/compensação/fundo, PIN e command_id; sem receita nova. Extrair manutenção sem perder funcionalidades.
- [ ] 4. GREEN alvo/commerce_history/delivery_details/review_regressions/restore/closing_recovery e acumulado.
- [ ] 5. diff --check; commit `feat: apresenta historico comercial e acertos detalhados`; ledger.

## Tarefa9: Filtros, controle e gestão

**Files:** ui/period.py,monthly.py,history.py,delivery.py,finance.py,results.py,cash.py,products.py,bootstrap.py; test_period_filters.py,test_management_experience.py.
**Interfaces:** PeriodSelection(start,end); PeriodFilter(parent,clock,default_preset,on_apply).apply/clear/applied; MonthSelector(parent,clock,on_apply); MonthlyView reutiliza reports.monthly; Finance.filters usa período aplicado.

- [ ] 1. Testar7dias/virada mês, inválido mantém última consulta, Limpar padrão, digitar não aplica; delivery ativo ontem visível, filtros independentes, financeiro por pagamento não duplica parcelas, mensal conserva fórmulas. Enter/erros nos formulários de despesa/compra/recorrência.
- [ ] 2. RED test_period_filters/test_management_experience.
- [ ] 3. Aplicar filtros validados atomicamente, datas explicadas; defaults Hoje/histórico, mês/contas e ativos/delivery sem restrição diária. Resultado mensal separado de lucratividade, caixa discrimina gaveta/modalidades/custódia; formularários comuns sem mudar autorização/duplicidade.
- [ ] 4. GREEN alvo/finance_ui/expenses/recurrence/results/settings/layout e acumulado.
- [ ] 5. diff --check; commit `feat: esclarece filtros e organiza controle e gestao`; ledger.

## Tarefa10: Integração, revisão e pacote

**Files:** __init__.py,scripts/build_v2.py,demo_v2.py,docs/manual-v2.md,validacao-v2.md,README.md; test_distribution.py,test_experience_end_to_end.py,test_layout.py; dist/Salva_AI_novo_0.2.0-dev.zip.

- [ ] 1. Testar ZIP/assets/migração em caminho acentuado com espaços; e2e banco anterior→upgrade→promoção/comanda→histórico→antecipado/dinheiro com troco→acerto→fechamento/backup/restore, replay após reinício; geometria das superfícies reais.
- [ ] 2. RED distribution/experience_end_to_end/layout.
- [ ] 3. Versão0.2.0-dev, PNGs/manifesto, sem bancos/caches/testes no ZIP, manual atualização e limites históricos; inspeção visual agrupada uma rodada, correções em lote e uma confirmação máxima. Não alegar Windows validado.
- [ ] 4. GREEN suíte nova/legado, ZIP extraído (exceto testes empacotador), hash. Uma revisão independente final; Important/Critical em um lote RED→GREEN e suíte completa, minors/decisões registrados.
- [ ] 5. Commit entrega, versionar ZIP específico com add -f, enviar só branch autorizada e verificar download remoto por hash. Informar link GitHub direto, manual e Windows pendente; sem main/merge/release.

## Cobertura e revisão

Spec identidade/telas:5–9; busca/teclado:3/6/7; snapshots/histórico:1/4/8;
pagamento/troco/acerto:2/4/7/8; filtros:9; preservação/distribuição:1/10.
Interfaces entre tarefas verificadas no pre-flight do ledger; dados antigos/replay
antes da UI, serviços antes de consultas, shell conserva APIs das views.
