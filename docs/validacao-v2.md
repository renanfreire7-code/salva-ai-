# Validação da reconstrução Salva AI

Entrega de desenvolvimento **0.1.0-dev**, branch `feat/salva-ai-v2`.
Base da implementação: `9625e7f`. Cabeça avaliada pela revisão independente:
`56aae9f564456aa1528f41332ced971bdefcff72`. As correções posteriores foram
validadas pelo implementador com testes de regressão, sem segunda rodada de revisão.

## Escopo entregue

Aplicativo offline separado do legado: produtos/estoque, promoções por quantidade,
venda direta, comandas, caixa, financeiro mensal, despesas auditáveis, recorrência,
delivery com custódia e acerto, histórico, lucratividade, previsão de compras,
Excel, fechamento HTML, PIN/recuperação, backup e restauração.
Banco novo vazio; sem migração dos dados da versão antiga.

O ZIP exige Python 3.12+ com Tkinter; não é instalador independente do Python.
O manual está em `docs/manual-v2.md` e como `LEIA-ME.md` dentro do ZIP.

## Revisão e correções

Revisão independente do conjunto: seis achados importantes, nenhum crítico
confirmado. Todos entraram em um único lote de correções. A inspeção do
implementador acrescentou filtro de pagamentos mensais e crédito fracionário de
fornecedor. As regressões de cada comportamento foram observadas falhando antes
da correção e passando depois.

| Achado | Correção e evidência |
| --- | --- |
| Sincronização com descritor somente de leitura | Temporários abertos com acesso de escrita; teste exige descritor gravável, simulando o contrato de sincronização do Windows. Não substitui execução nativa. |
| Devoluções parciais criavam custo | Quantidade e custo remanescentes conservam o total; teste devolve/revende unidades de custo fracionário sem custo negativo. |
| Anular pagamento de corrida reabria dívida já compensada | Bloqueio no Financeiro para pagamentos pertencentes a acertos; teste mantém corrida quitada e custódia conciliada. |
| Histórico guardava comando em vez do número da venda | Identidade real persistida, detalhes de valor/modalidade/produtos e recuperação dos IDs anteriores pela migração. |
| Fechamento omitia modalidades e confundia saída com recebimento | Livro de recebimentos/reembolsos por sessão, tela e HTML com bruto/reembolso/líquido; testes preservam caixa anterior e distinguem recebimento de delivery, cancelamento e devolução parcial. |
| Operador não conseguia corrigir compras | Consulta, reversão, devolução por item e créditos acessíveis na interface; reversão paga gera crédito, recebimento/abatimento explícitos com PIN. Teste de interface executa devolução e abatimento. |
| Filtro de pagamento somava parcelas fora do mês | Total pago restrito ao período; situação e saldo continuam considerando todos os pagamentos da conta. |
| Devoluções ao fornecedor arredondavam crédito repetidamente | Alocação cumulativa conserva o crédito original. Pagamentos vinculados a crédito ou compra revertida ficam protegidos contra anulação genérica. |

Migração `013_review_reconciliation.sql` acrescenta os fatos e preserva as
migrações anteriores com seus checksums. Um teste reconstrói recebimentos,
reembolsos e identidade de vendas de um banco anterior à migração.

## Verificação automatizada

Verificação final registrada nesta sessão em Linux, com Tkinter real sob Xvfb:

- Suíte nova: **97 testes aprovados**, sem pulos.
- Regressão do legado: **30 testes aprovados**, sem pulos.
- Pacote extraído: **95 testes aprovados**, sem pulos; os dois testes do
  empacotador foram executados na suíte do checkout.

```bash
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t .
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a python3 -m unittest discover -s tests -t .
python3 scripts/build_v2.py
git diff --check
```

O pacote extraído é testado em pasta temporária, com testes copiados do checkout,
executados usando somente os módulos e recursos do ZIP. Os dois testes do
empacotador ficam no checkout, pois o script de build não pertence à distribuição.
Cada arquivo do ZIP é conferido contra o manifesto SHA-256.

## Decisões de execução

Estas decisões complementam a especificação e os planos aprovados:

1. Checkout isolado da nuvem, sem worktree adicional, conforme a especificação.
   Custo se a suposição de isolamento estiver errada: alterações podem compartilhar
   o checkout; não houve merge nem push.
2. Scripts remotos das skills e referência auxiliar de testes não estavam
   disponíveis no início. Registro e comandos equivalentes foram usados, sem
   inventar execuções. Custo: menor automação do acompanhamento, compensada por
   commits, testes e este relatório.
3. Reversão de compra bloqueada após movimentos negativos posteriores.
   Protege custo histórico; custo: alguns casos seguros também exigem correção
   manual auditada em vez de reversão direta.
4. Modelo interno de pedidos compartilhado por venda, comanda e delivery,
   com APIs próprias. Custo: acoplamento interno que exige testes entre fluxos.
5. Reexpedição cria novo pedido vinculado com preços e taxas atuais após resolver
   retorno/reembolso anterior. Custo: novo número e eventual mudança de preço.
6. Correções financeiras entram na data da correção; retorno de mercadoria entra
   na data real do retorno. Preserva passado; custo: relatórios diferem de uma
   recomposição retroativa de todos os meses.
7. Consultas pequenas ficam junto ao serviço responsável. Custo: extração futura
   pode mudar imports internos; APIs públicas permanecem verificadas.
8. Branch renomeada para `feat/salva-ai-v2`, pois contém a reconstrução completa.
   Custo: referências locais ao nome anterior precisam ser atualizadas.
9. Execução nativa no Windows, escalas de 100%/125% e ensaio do proprietário
   permanecem critérios externos de aceitação. Linux não os comprova.
   Custo: ainda podem existir diferenças de plataforma e dificuldades de operação.
10. Falhas de escrita e troca de arquivos foram injetadas nos testes; disco cheio
    real e queda física de energia não foram julgados pela revisão. Custo:
    durabilidade real depende também do sistema de arquivos e equipamento.
11. Política de correção por data e reversão conservadora foram mantidas por
    decisão explícita; a biblioteca vendorizada foi excluída da revisão de código
    e conferida por identidade de arquivos/licença. Custo: limitações de operação
    acima e ausência de auditoria independente da biblioteca de terceiros.
12. Mantida a branch separada para cumprir a solicitação de novo projeto e
    permitir o ensaio. Custo: integração e publicação continuam para outra etapa.

Nenhum achado menor formal da revisão ficou adiado.

## Aceitação externa pendente

Não declarar esta entrega pronta para uso comercial antes do ensaio do manual:
Windows com caminhos acentuados/com espaços, escalas 100%/125%, fechamento,
backup/restauração e uso real com o colega em dados fictícios. O relatório da
revisão não julgou essas condições. Não houve substituição do aplicativo antigo,
merge, push ou publicação de release.
