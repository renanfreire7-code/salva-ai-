# Validação 0.2.0-dev — SALVA AI HEADSHOP

Evolução da reconstrução na branch `feat/salva-ai-v2`, a partir de
`cdf6c5505cb87908e4b5db0b773baa81c50b5839`. Não importa o banco legado 0.3.6.
A validação anterior 0.1 permanece registrada em [validacao-v2.md](validacao-v2.md).

## Entrega

Navegação lateral com onze destinos, identidade e assets PNG locais; busca por
iniciais/prefixos, F1–F12 no delivery, Enter e formulários com retenção de erros;
filtros explicitamente aplicados, histórico comercial separado da auditoria;
plano antecipado/na entrega, troco previsto e recebimento real discriminados;
acerto por pedido com consulta a acertos parciais e concluídos.

Migração 014 aditiva, backup antes da atualização e snapshots de nomes. Nenhuma
migração anterior foi reescrita. IDs, PIN, saldos e replay dos comandos antigos
são preservados. Nomes históricos já perdidos antes da atualização não podem ser
reconstituídos: a migração guarda o nome disponível naquele momento.

## Verificações

Execução em Linux, Python 3.12, Tk real sob Xvfb, tela virtual 1366 × 768.
Verificação de geometria também com janela 1260 × 680: controles visíveis em
painéis aninhados, cadastro e editor delivery. Inspeção visual agrupada dos onze
destinos e seis superfícies de operação, seguida de um lote de correções e uma
confirmação. A inspeção encontrou decodificação incorreta de PNG pelo carregador
local Tk: envio em base64 resolveu; regressão compara dimensões do PNG original.
A demonstração isolada também foi inicializada sem abrir o banco da loja.

O ensaio integrado cobre banco anterior → migração → promoção/comanda → histórico
→ antecipado Pix → dinheiro com troco e fundo → acerto de ambas corridas →
reinício/replay → fechamento/backup verificado → restauração. Confere estoque,
IDs vinculados, custódia zerada e saldo físico esperado.

Os resultados finais e a revisão independente estão registrados abaixo.
Windows nativo nas escalas 100% e 125% e ensaio com o operador
continuam pendentes. Esta entrega é para validação com dados fictícios.

## Decisões de execução e custos

1. Recuperação da branch após substituição do ambiente; documentos locais
   aprovados foram reconstituídos da conversa. Custo: os IDs dos commits locais
   originais dos documentos não foram recuperados.
2. Uso do checkout isolado já aprovado, sem worktree adicional. Custo: isolamento
   depende do checkout fornecido pela nuvem.
3. Auxiliares executáveis e referência complementar de testes das skills não
   estavam disponíveis; execução e registro equivalentes feitos manualmente.
   Custo: orquestração manual, sem alegação de execução desses auxiliares.
4. Nova tentativa com plano explícito nasce em preparação, aguardando confirmação
   antecipada e revisão do troco antes da saída; pedidos legados mantêm o fluxo
   compatível. Custo: uma ação de despacho adicional para o novo fluxo.
5. PNGs no empacotador e Resultado do mês funcional foram antecipados para a
   tarefa de navegação. Custo: integração antecipada para manter app/pacote válidos.
6. Reentrega aceita revisão opcional do troco; zero remove a previsão, omissão
   preserva payload/replay antigo. Custo: conferência adicional em tentativa em
   dinheiro quando preços/taxas atuais mudarem o total.
7. Pendentes de delivery inclui entregues sem pagamento e cancelados com reembolso
   a conferir, além de preparação/na rua, sem corte diário. Custo: lista mais
   longa para não ocultar impedimentos financeiros.

O ZIP anterior é preservado. Entrega somente na branch autorizada, sem merge,
alteração de main ou release. Manual: [manual-v2.md](manual-v2.md).


## Revisão independente e correções finais

Uma revisão independente read-only do intervalo base →
`8033ec6ee05f8333dd0766afea8ae4cfc63565f5` identificou dois achados Important,
nenhum Critical. Correções em um único lote, sem segunda rodada de revisão:

- Reembolso de Link passa a usar a modalidade real de `collections`, conserva
  formulário em erros e oferece seletor de saída da gaveta somente para dinheiro.
- Histórico mostra modalidade real e situação financeira separada da situação de
  entrega. Balcão/comanda preserva e exibe valor entregue/troco nos detalhes,
  incluindo situação de reembolso pendente ou concluído.

As novas regressões falharam antes e passaram após a correção (13 testes alvo).
O revisor também exercitou o formulário de acerto: valor inválido permaneceu
para correção e acerto de R$38 + R$7 de compensação gerou um único registro,
custódia zero e saldo físico correto.

### Ajustes menores adiados

- Enter no nome da comanda ainda abre diretamente a comanda; a regra de apenas
  focar a ação no último campo não foi aplicada a esse campo específico.
- Cancelar delivery ainda abre PIN/motivo sem resumo explícito adicional do pedido
  e valores. Autorização e motivo continuam obrigatórios.

Esses desvios menores ficam registrados para a próxima evolução; não houve
expansão do lote final para ajustes cosméticos.


## Resultado final verificado

Após o lote de correções `d1993ef`:

- Checkout: **157/157 testes aprovados**, sem pulos.
- Legado: **30/30 aprovados**, sem pulos.
- Código do ZIP extraído: **155/155 aprovados**, sem pulos; os dois testes do
  empacotador são executados no checkout.
- ZIP: 147 arquivos no manifesto, integridade e hashes conferidos; fontes,
  migrações, PNGs e manual iguais aos do checkout. Sem banco, backup ou cache.
- Demonstração isolada inicializada; interface inspecionada no Linux conforme
  procedimento acima. Windows nativo e aceite do operador permanecem pendentes.

Artefato: `dist/Salva_AI_novo_0.2.0-dev.zip` (1.990.407 bytes).
SHA-256: `bfb6ce15182e6f6d1d16c3f43d35386d67b341d2799cd45febb2242801b6da2b`.
O arquivo distribuído é a mesma cópia usada na suíte extraída.

Comandos finais: `python3 -m unittest discover -s tests_v2 -t .` e
`python3 -m unittest discover -s tests -t .`, ambos sob Xvfb, além da suíte
copiada para a pasta extraída com espaços/acentos, excluindo `test_distribution`.
