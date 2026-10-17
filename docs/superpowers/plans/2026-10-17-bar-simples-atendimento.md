# Bar Simples: Atendimento e Entrega Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar a evolução aprovada com complemento no delivery, busca uniforme, nomes completos, ações claras e pacote verificado do Bar Simples.

**Architecture:** Extensão aditiva do DTO/payload do delivery; apresentação compartilhada de produtos com linhas que quebram nomes, sem alterar seus IDs ou valores. Reaproveitar regras financeiras existentes e integrar o checkpoint autenticado do planoA antes da única revisão final e distribuição.

**Tech Stack:** Python 3.12+, Tkinter/ttk/Canvas, SQLite, unittest, zipfile/hashlib; sem dependências de runtime novas.

**Spec:** `docs/superpowers/specs/2026-10-17-bar-simples-acesso-atendimento-design.md`

## Global Constraints

- Executar após `2026-10-17-bar-simples-acesso.md`; manter contratos de Application/AccountService e PIN3.
- “complemento opcional separado”; pedidos antigos recebem vazio, sem reinterpretar referência.
- “Estender DTOs/payloads sem invalidar replays de comandos antigos”.
- “Mesmo comportamento no balcão, comanda e editor delivery”; código/texto/prefixos/iniciais sem diferenciação de maiúsculas/acentos.
- “Não depender exclusivamente de tooltip, reticências ou rolagem horizontal para identificar o produto”; não reduzir fonte.
- “Preservar F1–F12 e seleção → quantidade → adicionar”.
- “Não mudar fórmulas financeiras”; reembolso, retorno ao estoque e nova saída/corrida são fatos separados.
- Mesma pasta SalvaAiHeadshopV2; migrações antigas imutáveis; sem merge/main/release.

## Review Focus

1. Reexecução de comando0.2 com DTO/payload novo vazio: retorna resultado original sem criar pedido duplicado (B1).
2. Nome muito longo sem espaços, acentos e janela estreita: todos os caracteres permanecem legíveis com quebra, preservando valores e identidade da seleção (B2).
3. Filtro/refresh com nomes iguais: escolher segunda linha mantém ID, não adiciona produto errado nem duplica evento de teclado (B2).
4. Cancelar resumo ou PIN em retorno/reembolso/reentrega: não altera estoque/caixa/corridas nem perde os campos válidos (B3).
5. ZIP extraído em caminho acentuado, migração de banco com PIN6 e restauração anterior: autentica pelo fluxo correto, assets locais e histórico/saldos preservados (B4).

---

## Estrutura

B1 e B2 são unidades independentes de domínio/apresentação; B3 consome ambas, B4 integra os dois planos. Não delegar em paralelo por padrão: os contratos de bootstrap/fixtures e shared UI são compartilhados.

- `migrations/016_delivery_complement.sql`, `delivery/models.py`, `payment_plan.py`, `service.py`, `cancellation.py`: complemento compatível.
- `ui/product_table.py`: linhas de produto com altura variável, seleção e teclado.
- `ui/shared.py`: fábrica e picker; views continuam usando IDs e fill.
- `ui/delivery_actions.py`: resumos das ações, sem regra financeira duplicada.
- `docs/manual-v2.md`, `docs/validacao-bar-simples.md`, `scripts/build_v2.py`: entrega e evidência.

### Task B1: Complemento persistente e compatibilidade

**Files:** Create `salva_ai_v2/migrations/016_delivery_complement.sql`, `tests_v2/test_delivery_complement.py`; Modify `delivery/models.py`, `payment_plan.py`, `service.py`, `cancellation.py`, `ui/delivery_editor.py`, `ui/order_details.py`.

**Interfaces:** Acrescentar `DeliveryDraft.complement: str = ''` no FINAL do dataclass, preservando todos argumentos posicionais. `draft_payload(draft) -> dict` omite complement quando vazio, além da regra existente dos campos0.1. `DeliveryQueries.detail` retorna `order['complement']` por seleção já existente. Editor expõe `fields['complement']` entre endereço/referência; `delivery_text` inclui linha Complemento somente quando não vazio.

- [x] **Step 1: Escrever testes.** `test_complement_is_optional_and_survives_restart`: confirmar 'Apartamento202, blocoB', reabrir banco e conferir detalhe/histórico/acerto; nome/endereço/referência originais iguais. `test_previous_v02_command_fingerprint_replays_with_empty_complement`: gravar comando em banco/payload de014, upgrade015/016, chamar com campo default; mesmo ID e countorders1. `test_redelivery_copies_complement_and_snapshots`: resolver anterior, nova tentativa copia complemento sem sobrescrever anterior, preserva regras de preço/troco/corrida. `test_editor_error_keeps_complement`: estoque insuficiente mantém endereço e complemento digitados.
- [x] **Step 2: RED.** Xvfb unittest `tests_v2.test_delivery_complement`; falha por campo ausente, usando helper autenticado do planoA.
- [x] **Step 3: Implementar.** ADD COLUMN complement TEXT NOT NULL DEFAULT ''; nunca editar014. INSERT de delivery com colunas nomeadas, copiar no redeliver e payload somente se não vazio; legacy DTOs não ganham chave vazia no fingerprint. Formulário: complemento opcional, Enter avança corretamente, sem aumentar geometria além da tela; detalhes usados por histórico/acerto mostram campo. Não alterar stored reference.
- [x] **Step 4: GREEN.** Testes alvo + test_delivery_payment_plan/test_delivery_cancellation/test_delivery_details/test_experience_upgrade/test_experience_end_to_end. Backup prévio e no-reset verificados.
- [x] **Step 5: Commit.** diff--check; `git commit -m 'feat: adiciona complemento ao endereco do delivery'`.

### Task B2: Produtos legíveis e busca nos três atendimentos

**Files:** Create `salva_ai_v2/ui/product_table.py`, `tests_v2/test_product_table.py`, `tests_v2/test_product_search_flows.py`; Modify `ui/shared.py`, `ui/sales.py`, `ui/tabs.py`, `ui/delivery_editor.py`, `ui/products.py`, `ui/purchases.py`, `ui/order_details.py`, `ui/results.py`, `tests_v2/test_layout.py`.

**Interfaces:** `ProductTable(parent, columns: list[str], height=12)` é ttk.Frame com Canvas/scroll vertical e linhas Label com wrap por largura/font. Expor API usada nas views: `insert(parent,index,iid,values)`, `delete(*ids)`, `get_children() -> tuple[str]`, `exists(id)`, `item(id, option=None, **kwargs)`, `column(name, **kwargs)`, `heading(name, **kwargs)`, `selection()`, `selection_set(id)`, `focus(id=None)`, `see(id)`, acesso `['columns']`, `bind` e evento `<<TreeviewSelect>>`. Valores retornados por item são os originais, não strings alteradas por quebra. `table(...)` escolhe ProductTable apenas para colunas contendo Produto; demais tabelas continuam ttk.Treeview. `fill` preserva ID selecionado. `ProductPicker` mantém `.search/.picker/.qty/.selected_product/.select_shortcut` e acrescenta `.candidates` com lista legível e `.selected_name` que mostra integralmente o produto escolhido.

- [x] **Step 1: Escrever testes.** `test_wrap_long_and_unbroken_names_without_loss`: nome com180caracteres e token100sem espaços; labels têm texto integral, requestedheight cabe na linha após widthresize, valores/id intactos. `test_keyboard_selection_refresh_and_duplicate_names`: Up/Down/Home/End/Enter selecionam IDs previsíveis, fill conserva segunda linha de mesmo nome, duplo clique produz um evento útil, scroll leva seleção à vista. `test_hei_prefix_and_initials_in_all_three_flows`: produtosHeineken+outra cerveja; hei/cerhei/CHL filtram corretamente nas três views, buscaambígua não adiciona, F1 apenas seleciona e foca quantidade, Enter adiciona uma vez. `test_full_names_in_every_product_surface`: catálogo/carrinho/comanda/delivery/produtos/compras/retornos/histórico/acerto/lucro/reposição usam componente ou texto multilinha integral. `test_primary_actions_stay_visible_when_names_wrap`: quantidade/total/Receber/Confirmar não saem da janela1366×768, lista é que rola.
- [x] **Step 2: RED.** Xvfb unittest `tests_v2.test_product_table tests_v2.test_product_search_flows tests_v2.test_layout`; falha por nomes cortados/componentes ausentes.
- [x] **Step 3: Implementar.** Componente composto com header fixo e scroll de linhas de altura variável; coluna Produto absorve espaço após reservar colunas numéricas legíveis. Label quebra inclusive tokens sem espaços, sem truncamento e sem limite artificial de linhas. Eventos de clique/teclado encaminhados ao container uma vez; seleção browse. Picker exibe candidatos legíveis nos três fluxos e o nome selecionado fora da Entry; manter Combobox apenas como campo auxiliar compatível, sem depender de dropdown nativo para ler nomes longos. Reutilizar search_products existente, sem sinônimos customizados/fuzzy. Só factory/consumidores necessários, sem refatorar tabelas financeiras. Em telas estreitas com muitas colunas, detalhes do item ficam abaixo; nome continua integral na linha, colunas extras podem rolar sem ocultar o nome.
- [x] **Step 4: GREEN.** Alvo + test_checkout_experience/test_attendance_ui/test_form_keyboard/test_delivery_experience/test_history_experience/test_settlement_experience/test_navigation, depois nova suíte. Fazer uma inspeção visual agrupada com nomes reais longos, em1366×768 e janela1260×680; corrigir em lote, uma confirmação máxima. Preservar IDs/snapshots e fonte normal.
- [x] **Step 5: Commit.** diff--check; `git commit -m 'feat: exibe produtos completos e uniformiza busca nos atendimentos'`.

### Task B3: Ações de delivery claras e Enter da comanda

**Files:** Create `salva_ai_v2/ui/delivery_actions.py`, `tests_v2/test_delivery_action_summaries.py`; Modify `ui/delivery.py`, `ui/tabs.py`, `ui/settlement.py` somente se necessário para nomes de ações.

**Interfaces:** `action_summary(detail: dict, action: str) -> str` aceita CANCEL/REFUND/RETURN/REDELIVER e inclui pedido, cliente/endereço/complemento, itens/total, pagamento real, valores já devolvidos/pendentes e custo de corrida. `confirm_action(parent, detail, action) -> bool` mostra resumo antes de solicitar PIN; não muta serviços. `.refund/.returned/.redeliver/.cancel` mantêm métodos públicos e command_id estável por intenção. Renomear rótulos e atualizar action_buttons sem quebrar as chaves por nome de método.

- [x] **Step 1: Escrever testes.** `test_action_labels_and_summary_match_actual_facts`: rótulos aprovados e pagamento realDEBIT deLink combinadoCREDIT, complemento e corrida já devida. `test_declined_summary_or_pin_is_noop`: recusar resumo ou cancelarPIN mantém dump das tabelas estoque/movimentos/refunds/trips; nada enviado ao serviço; campos preenchidos permanecem em caso de erro. `test_completed_actions_keep_financial_separation`: reembolso não retorna produto, retorno não devolve dinheiro, nova tentativa cria vínculo mas corrida só na saída. `test_tab_last_field_enter_only_focuses_create`: Enter no nome não cria; foco botão; confirmação seguinte gera uma comanda.
- [x] **Step 2: RED.** Xvfb unittest `tests_v2.test_delivery_action_summaries`; falha nos rótulos/resumo e Enter atual.
- [x] **Step 3: Implementar.** Resumos com texto claro: reembolso confirma devolução externa; retorno só revenda; nova tentativa tem preços atuais e outra corrida ao sair. Diálogos com callbacks preservam dados em erros e não registram antes de confirmar. Não mudar APIs financeiras, regras de cancelamento nem conferência de troco; PIN só após resumo aceito. Acrescentar explicação curta na seleção da ação e manter acessibilidade do texto sem depender de cor/tooltip. Enter no nome foca Abrir comanda.
- [x] **Step 4: GREEN.** Alvo + delivery_cancellation/payment_plan/settlement/experience/history e test_form_keyboard/test_attendance_ui. Conferir saldos e contagem de comandos, não apenas texto de botão.
- [x] **Step 5: Commit.** diff--check; `git commit -m 'feat: esclarece reembolso retorno e nova tentativa de entrega'`.

### Task B4: Integração, única revisão e pacote

**Files:** Create `tests_v2/test_bar_simples_end_to_end.py`, `dist/Bar_Simples_0.3.0-dev.zip`; Modify `salva_ai_v2/__init__.py`, `scripts/build_v2.py`, `scripts/demo_v2.py`, `INICIAR_V2.bat`, `tests_v2/test_distribution.py`, `docs/manual-v2.md`, `docs/validacao-bar-simples.md`, `README.md`.

**Interfaces:** `build_v2(output_dir) -> Path` preservado, novo nome Bar_Simples_0.3.0-dev.zip; prefixo/marca de VERSAO.txt Bar Simples, código continua módulo salva_ai_v2 e data-dir anterior. BAT existente permanece ponto de entrada compatível; não exige reinstalar Python ou copiar banco.

- [x] **Step 1: Escrever testes.** `test_v02_to_bar_simples_complete_operation_and_restore`: banco014 com dados+PIN6→upgrade+backup→transiçãoPIN007→login→buscahei nos três fluxos→venda/comanda promocional→delivery complemento/antecipado e dinheirotroco→acerto→fechamento→reinício/login→restore→novo login com credencial restaurada; comparar saldos/estoque/IDs e replay antigo. `test_clean_bar_simples_archive_assets_manifest_and_entrypoint`: novo nome/versão, logo+ícone+moto+migrações, manifesto confere cada hash, sem bancos/caches/testes; extrair em pasta com espaços/acentos, abrir entrada e operação após login com dadosfictícios. Testes de distribuição da0.2 são atualizados para contrato0.3, ZIP0.2 preservado.
- [x] **Step 2: RED.** Xvfb unittest test_bar_simples_end_to_end/test_distribution; falha na integração/nomeversão antes de alterações de empacotamento.
- [x] **Step 3: Integrar e documentar.** Versão0.3.0-dev da reconstrução, distinta de referência0.3.6-beta. Ajustar marca/manuais/demo/BAT sem alterar a política de instância única nem apagar locks/bancos. Gerar ZIP sem credenciais/dados fictícios. Manual login/PIN/chave e atualização; registrar limites Windows e decisões reais, nenhum resultado presumido. Preparar artefato antes de envio.
- [x] **Step 4: Verificar e revisar.** `PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t .`; legado com `discover -s tests -t .`. Copiar testes para ZIP extraído e rodar sem test_distribution (empacotador ausente noZIP); conferir fontes/assets/manual por hash. Depois de verde, uma revisão independente final da base4102932 até HEAD, cobrindo ambos os planos e ReviewFocus. Só aqui delegar review, conforme método nativo; Important/Critical em um lote com regressão RED→GREEN e nova suíte completa, minors registrados. Não alegar validação Windows nativa; aceite100%/125% e operador ficam explícitos. Revisão não muda política de acesso nem inventa escopo adicional.
- [x] **Step 5: Entregar.** Commit de correções/verificação; gerar/conferir novamente artefato se conteúdo mudar; versionar apenas ZIP específico com add -f, preservar anteriores. Enviar somente feat/salva-ai-v2 sob autorização existente; conferir download HTTP e SHA256 contra arquivo testado. Relatório com resultados/revisão/decisões/minors e link direto. Sem merge/main/release.

## Autorrevisão do plano

Complemento/compatibilidadeB1; nomes e buscaB2; explicações e EnterB3; integração/distribuiçãoB4. ReviewFocus cinco itens com testes correspondentes, além das regressões financeiras existentes. ProductTable conserva API efetivamente consumida pelas views (IDs/selection/item/column/eventos); AccountService/Application são consumidos dos contratosA2/A3, sem segundo login paralelo. Migração016 vem após015. Uma revisão final após todos os testes, sem revisão por tarefa no método nativo. Documentos de plano são a única alteração nesta etapa.
