# Salva AI — reconstrução do PDV e gestão offline

Data: 16/10/2026. Branch: `projeto/salva-ai-novo`.

Estado: desenho consolidado para revisão do responsável; implementação não iniciada.

## 1. Objetivo e contexto

Atender um proprietário que abriu um bar e precisa controlar comandas, fechamento
do caixa, estoque e lucro. O operador também será o administrador. A prioridade
é atendimento simples e rápido, números compreensíveis e registros rastreáveis.

Reconstruir do zero, com banco inicialmente vazio, usando o aplicativo antigo como
referência de comportamento. Não importar dados nem modificar o banco antigo.
Preservar o código anterior no histórico e usar diretório de dados exclusivo do
novo aplicativo, inclusive durante desenvolvimento e testes.

Referências verificadas:

- GitHub/main: commit `cb6f1fc7a5176ad21ce3c7e4174041cb021d9967`, versão 0.3.4-beta.
- ZIP fornecido: 0.3.6-beta, inspecionado separadamente, sem pasta de testes.
- Os 30 testes da base 0.3.4 passaram contra os módulos da 0.3.6. Isso não valida
  todos os recursos acrescentados; os 54 testes relatados não foram fornecidos.

## 2. Escopo aprovado

Primeira versão completa com oito áreas: comandas, venda direta, produtos e
estoque, caixa, histórico, financeiro mensal, lucro por produto e previsão de
compras. Inclui promoções por quantidade, backups, restauração, relatórios,
recorrência de despesas e autorização administrativa. Delivery integra atendimento,
estoque, caixa e financeiro conforme a seção 6.1.

Entregas de desenvolvimento serão incrementais e verificáveis; não representam
liberação parcial para operação real sem validação do conjunto.

Restrições:

- Python 3, Tkinter/ttk e SQLite; Windows prioritário; funcionamento offline.
- Um dispositivo, um operador e aproximadamente 20 produtos.
- Venda em unidades inteiras de produtos fechados; sem receitas, doses ou ingredientes.
- Dinheiro, Pix, débito e crédito apenas à vista; um meio por venda.
- Sem fiado, descontos manuais ou pagamentos divididos.
- Promoções por quantidade são a exceção de preço explicitamente autorizada.
- Sem servidor, dependência de internet para vender ou serviços pagos obrigatórios.
- Sem emissão fiscal, conciliação bancária ou promessa de lucro contábil oficial.
- Sem merge, release ou publicação externa sem autorização.

## 3. Organização técnica

Monólito modular: uma aplicação local com módulos de interface, regras de negócio,
persistência, relatórios e backup. As telas chamam serviços de aplicação, sem
duplicar regras financeiras ou executar gravações de negócio diretamente.

SQLite será a fonte única dos dados. Ativar integridade referencial; definir limites
de transação explicitamente e usar consultas parametrizadas. Dinheiro em centavos
inteiros; cálculos intermediários exatos com arredondamento explícito. Nunca usar
float binário para decisões monetárias.

Operações financeiras e sua auditoria devem confirmar ou reverter juntas. Prevenir
confirmação repetida tanto na interface quanto na persistência; desabilitar um
botão sozinho não garante ausência de duplicidade.

Separar módulos de atendimento, estoque/custeio, caixa, financeiro, autorização,
auditoria, exportação e manutenção do banco. Não introduzir serviços distribuídos.

## 4. Interface e atendimento

Agrupar a navegação em Atendimento (vendas e comandas), Controle (produtos,
estoque, caixa e histórico) e Gestão (despesas, resultados e reposição), mantendo
as oito áreas acessíveis. Venda direta e comandas têm acesso imediato.

Interface em português brasileiro, adequada a 1366 × 768, com navegação por
teclado, foco previsível, tabelas legíveis e ações essenciais visíveis. Usar texto
junto às cores para estados. Formulários de despesa ficam em janela própria.

Feedback após cada operação, sem alertas modais desnecessários. Erros preservam
os dados digitados para correção. Confirmar ações destrutivas com contexto claro.

### Venda direta

Buscar produto por nome/código ou atalho F1–F12; adicionar ao carrinho; ajustar
quantidades; conferir itens e total; escolher recebimento; confirmar uma vez.
Selecionar um produto nunca conclui uma venda. Exigir caixa aberto.

Em dinheiro, registrar valor entregue e troco; somente o valor líquido da venda
compõe o dinheiro esperado. Pix e cartões não aumentam o dinheiro na gaveta.

A confirmação grava venda, itens, preços/promocões, custo histórico, taxas,
movimentação de estoque e vínculo ao caixa em uma transação. Não deixar venda
parcial após falha. Mostrar identificador ao concluir e preparar novo atendimento.

### Comandas

Identificação por nome e número automático; avisar se já existir nome igual aberto.
Itens reservam estoque; pagamento converte a reserva em baixa definitiva sem
descontar duas vezes. Aumentos respeitam disponibilidade.

Reduzir/remover itens já registrados e cancelar comanda exige PIN e motivo,
mantendo histórico. Fechar a comanda usa o mesmo recebimento da venda direta.

## 5. Promoções

Uma promoção ativa por produto selecionado: quantidade do grupo e preço total.
Não misturar produtos diferentes. Aplicar automaticamente grupos completos;
sobras usam o preço normal. Exibir condição, quantidade, total e economia.

Exemplo: unidade R$ 5; grupo de 3 por R$ 12. Totais: 1 = R$ 5; 2 = R$ 10;
3 = R$ 12; 4 = R$ 17; 6 = R$ 24.

Na primeira inclusão do produto na comanda, guardar preço normal e condição
promocional. Inclusões posteriores do mesmo produto usam essa condição até o
encerramento; mudanças no cadastro não alteram o combinado. Recalcular grupos
ao alterar quantidade, preservando os registros necessários à auditoria.

Gravar condição e total efetivamente cobrados na venda. O custo do estoque é
independente da promoção. Arredondamentos de distribuição não podem modificar
o total cobrado; usar critérios determinísticos e conservar centavos.

## 6. Caixa

Somente um caixa aberto. Abertura informa troco inicial. Separar recebimentos
por modalidade. Reforço e retirada exigem valor, motivo e PIN; não são receita
nem despesa automaticamente. Bloquear retirada superior ao dinheiro esperado.

Esperado = troco inicial + vendas válidas em dinheiro + reforços − retiradas,
considerando também correções financeiras autorizadas e auditadas.

Bloquear fechamento enquanto houver comandas abertas; mostrar quais resolver.
Comparar contado e esperado; divergência exige justificativa e PIN. Preservar
caixas encerrados, sem reescrever sua movimentação histórica.

Pagamento de despesa pela gaveta é uma operação única: pagamento da despesa e
retirada vinculada, com auditoria atômica. Uma mesma saída não pode ser
registrada novamente por outro fluxo sem detecção da duplicidade.

Fechamento gera relatório e backup verificado. Só mostrar sucesso após concluir
todos os passos. Como SQLite e arquivos não compartilham transação, usar estado
de fechamento recuperável: em falha de arquivo, não confirmar sucesso nem permitir
novo fechamento/atendimento conflitante; oferecer retentativa sem duplicar eventos.
O backup final precisa conter o fechamento e suas diferenças. Detalhar esse
protocolo no plano técnico e testar falhas entre cada etapa.

### 6.1. Delivery e acerto com entregador

Controle manual offline para pedidos recebidos pelo operador. Primeira versão
sem integração de WhatsApp, plataformas externas, mapas ou rastreamento.
Um entregador próprio recebe valor fixo por corrida, sem acesso individual ao PDV.

Pedido registra número, nome, telefone, endereço, referência, produtos, promoções,
taxa de entrega, modalidade e situação do pagamento. Usar regras comuns de preços
e promoções; detalhar o congelamento das condições ao confirmar o pedido no plano.

Taxa cobrada do cliente e remuneração do entregador são dois valores fixos
configuráveis e independentes. Guardar ambos no pedido; alterações de configuração
não reescrevem pedidos nem corridas anteriores.

Estados: Novo → Em preparação → Saiu para entrega → Entregue, além de cancelado.
Entrega, pagamento e acerto têm estados separados. Reserva de estoque ao confirmar
pedido; baixa na saída, sem duplicar a reserva. Antes da saída, cancelamento libera
reservas; depois dela, mercadoria só retorna ao estoque por conferência explícita.
Preservar histórico, motivo e autorização para cancelamentos sensíveis.

O cliente pode pagar ao bar antes da saída ou pagar ao entregador na entrega.
Registrar modalidade e destino do recebimento. Pix confirmado na conta do bar é
recebimento pelo bar, mesmo quando solicitado pelo entregador. Dinheiro em posse
do entregador fica como valor sob sua responsabilidade, sem aumentar a gaveta.
Entrega marcada como concluída não confirma automaticamente pagamento.

Ao registrar a saída, gerar uma única obrigação pelo custo da corrida. O entregador
recebe mesmo em cancelamento posterior ou tentativa sem sucesso. Retentativa da
mesma operação não gera outra corrida nem outra baixa. O plano distinguirá
retentativa técnica de uma nova saída física que possa exigir outra corrida.

Tela de pedidos em andamento com ação de acerto: listar entregas, recebimentos em
posse do entregador, corridas devidas e acertos anteriores. Conferir o dinheiro que
ele entrega ao bar e registrar sua entrada na gaveta. Pagar remuneração é uma
saída própria e vinculada. Se houver compensação, registrar explicitamente valores
brutos e compensados, para não criar entrada/saída física fictícia na gaveta.

Bloquear fechamento do caixa enquanto houver pedidos em andamento ou dinheiro do
entregador sem conferir. Mostrar pendências e não oferecer baixa automática.
Corridas não pagas podem permanecer como obrigação financeira identificada após
o fechamento, sem alterar posteriormente o caixa encerrado.

Relatórios separam receita dos produtos, taxa cobrada e custo do entregador.
Gerar o custo uma vez na saída e quitar a obrigação no acerto; não reconhecer
novamente a despesa ao pagar. Cancelamento exige conciliar receita, eventual
devolução ao cliente, estoque e corrida devida, sem apagar fatos já registrados.

## 7. Produtos, compras e estoque

Cadastro: código automático, nome, preço, unidades por caixa/fardo, mínimo e
promoção opcional. Exibir físico, reservado e disponível.

Entrada informa quantidade, custo total e data; converter caixas em unidades.
Atualizar custo médio ponderado pelo valor do estoque existente e da nova compra.
Preservar precisão suficiente para custo unitário fracionário de centavo e
arredondar valores monetários nos limites definidos, sem acumular desvios.
Cada venda conserva custo histórico, independente de compras futuras.

Perdas e ajustes exigem PIN e motivo. Não permitir estoque negativo nem físico
inferior ao reservado. Desativar produtos sem apagar histórico.

Compra registra estoque e obrigação financeira na mesma operação; indicar paga
ou pendente. Comprar não deduz novamente o valor do lucro: reconhecer CMV na
venda. Usar identificação da compra para vincular estoque, financeiro e auditoria.

Reposição usa disponível, mínimo e tamanho da caixa; sugere caixas completas e
custo estimado. Sugestão não altera estoque nem gera despesa antes da confirmação.

## 8. Financeiro mensal

Separar resultado gerencial por competência de pagamentos e compromissos.
Nenhuma dessas visões deve ser chamada automaticamente de saldo bancário.

Despesa: ID estável, descrição, categoria, valor, data do gasto, vencimento,
situação e data do pagamento. Valores positivos e datas válidas.

Edição exige PIN e motivo; registrar antes/depois e instante da operação.
Exclusão lógica exige PIN e motivo, preserva linha e auditoria e remove a despesa
dos cálculos ativos. Permitir consulta explícita aos excluídos.

Pagamento ligado à gaveta exige tratar a retirada vinculada. Excluir despesa não
significa retorno de dinheiro. Correções não podem alterar caixa já encerrado;
qualquer compensação efetiva deve ser uma nova operação explícita e auditada.

Consulta padrão: mês atual pela data do gasto. Filtros: mês/ano ou intervalo,
categoria, descrição e situação. Ao escolher outra referência de data, deixar
explícito se é gasto, vencimento ou pagamento; não misturar bases silenciosamente.

Estados: paga (verde), pendente ainda não vencida (cinza), vencida não paga
(vermelho), sempre com texto. Vencimento hoje ainda não é atraso.

Resumo do conjunto filtrado: pago, pendente incluindo vencido, vencido como
subconjunto, total de compromissos e categorias. Não somar vencido duas vezes.
Resultado mensal usa o período e as regras gerenciais indicadas, sem mudar
silenciosamente conforme filtros operacionais incompatíveis.

Duplicidade: comparar descrição normalizada, valor, categoria e mês do gasto;
mostrar semelhantes e pedir confirmação. Não impedir repetições legítimas.

Recorrência: regra mensal gera ocorrências pendentes identificadas por regra e
competência, com valor ajustável e proteção persistente contra geração repetida.
Nunca inferir pagamento. O plano detalhará calendário de vencimentos e mudança
de uma ocorrência versus alteração das próximas, sem reescrever ocorrências pagas.

DAS: considerar despesa ou provisão conforme regra explícita, nunca ambos para
a mesma competência. Compra de estoque fica fora das despesas operacionais do
resultado para não duplicar CMV. Conservar taxas e custos das vendas históricas.

## 9. Lucro, histórico e relatórios

Lucro por produto apresenta quantidade, receita após promoções, CMV histórico,
taxas e margem de contribuição. Distribuir despesas e DAS proporcionalmente ao
faturamento para resultado estimado; explicar o rateio. Conservar centavos no
rateio, inclusive sobras; não inventar margem percentual quando receita é zero.

Taxas configuráveis de débito e crédito à vista; Pix começa com zero ajustável.
Guardar taxa e valor em cada venda, sem recalcular histórico com a taxa atual.
Destacar custos ausentes e taxas ainda não confirmadas; zero informado e dado
desconhecido precisam ser distinguíveis.

Histórico com filtros por período e identificador, eventos e motivos. Relatórios
Excel e fechamento imprimível devem identificar período, filtros e exclusões.
Consultar dados pela mesma regra usada nas telas para evitar totais divergentes.

Estornos exigem PIN e motivo, preservam o original e corrigem estoque e efeito
financeiro sem duplicação. Reabertura de comanda paga somente no caixa original
ainda aberto. Sistema não devolve Pix/cartão automaticamente. O plano detalhará
estorno de venda direta e compensação após fechamento, preservando caixas fechados.

## 10. Autorização, auditoria e manutenção

PIN criado no primeiro uso, armazenado com salt e derivação criptográfica
adequada, nunca em texto puro. Espera progressiva após erros. Sem PIN mestre.
Autorizações devem ser verificadas nos serviços de aplicação, não só nos botões.

Chave de recuperação offline, exibida para armazenamento fora do computador;
guardar somente verificador seguro. Recuperação cadastra outro PIN e gera evento.
Não registrar PIN/chave nos logs, auditoria ou relatórios. PIN não criptografa SQLite.

Auditoria registra ID da operação, horário, motivo, objeto afetado, antes/depois e
autorização administrativa. Um operador não oferece identificação individual de
pessoas; não apresentar isso como prova de autoria pessoal ou proteção contra
modificação direta do arquivo por alguém com acesso ao computador.

Backup manual, no fechamento e antes de migração; usar cópia consistente do
SQLite e verificar integridade/compatibilidade. Migrações versionadas, repetíveis
e seguras; banco antigo da reconstrução não será migrado nem aberto por engano.

Restauração exige PIN, identificação do backup e confirmação explícita, preserva
backup do banco atual e fecha conexões antes da substituição. Verificar banco
restaurado antes de retomar operação. Disponibilizar pasta adicional, como
pendrive, indicando falha ou ausência sem afirmar que a cópia externa foi feita.

## 11. Validação e critérios de aceitação

Usar somente bancos temporários e dados fictícios. A suíte nova não herda o
número de testes da referência; reportar executados, falhas e pulos separadamente.

- Vendas atômicas, confirmação repetida, falta de estoque e entradas inválidas.
- Reserva, pagamento, alteração e cancelamento de comanda, com PIN e auditoria.
- Promoções: 1/2/3/4/6 unidades, sobras, alteração e condição congelada.
- Caixa: modalidades, troco, movimentos, despesa vinculada, divergência e bloqueio
  por comandas; falhas de relatório/backup e recuperação de fechamento.
- Delivery: reserva/baixa, confirmação de saída repetida, pagamento antecipado e
  na entrega, cancelamento antes/depois da saída e devolução conferida. Verificar
  corrida devida mesmo sem sucesso, valores fixos históricos, acerto parcial ou
  repetido sem duplicações, compensação explícita e bloqueio do fechamento por
  pedidos ou dinheiro pendentes. Remuneração a pagar não bloqueia fechamento.
- Custo médio com compras de custos diferentes, estoque zerado, perdas e
  arredondamentos; histórico de venda preservado após mudança de custo/preço/taxa.
- Despesas: dois aluguéis fictícios de R$ 1.000; excluir um deixa R$ 1.000 ativo e
  ambos consultáveis. Edições, exclusões e repetições não deixam eventos parciais.
- Datas na virada do mês, vencimento hoje, pagamento em outro período,
  filtros, recorrência repetida, DAS e ausência de dupla dedução de compras.
- Exportações conciliadas com telas e regras, inclusive excluídos e promoções.
- PIN incorreto, bloqueio progressivo, recuperação e ausência de segredos em logs.
- Persistência após reinício; integridade, migrações e restauração; falhas de
  gravação e recuperação, sem tocar nos dados do estabelecimento.
- Interface a 1366 × 768, teclado, foco, contraste, mensagens e ausência de ações
  essenciais cortadas; confirmar também no Windows e com escala de tela habitual.
- Ensaio com o operador: vender, manter comanda, receber, registrar compra/despesa,
  fechar caixa e consultar resultado usando dados fictícios.

## 12. Sequência de desenvolvimento proposta

1. Revisar esta especificação e resolver decisões técnicas no plano.
2. Estruturar aplicação nova, banco exclusivo, migrações, auditoria e autorização.
3. Produtos, compras, estoque e custo médio.
4. Caixa, atendimento, comandas, promoções e recebimento.
5. Financeiro, recorrência e integrações com caixa/compras.
6. Delivery, reservas/saídas, recebimentos e acertos com entregador.
7. Resultados, reposição, histórico e relatórios.
8. Backup/restauração, testes de falha, interface e distribuição Windows.

Cada etapa exige testes e revisão. A próxima ação após aprovação desta
especificação será elaborar o plano técnico e seus testes; implementação depende
da revisão do plano. Esta lista é uma sequência de trabalho, não o plano técnico.

## 13. Pontos a detalhar antes da implementação correspondente

As decisões abaixo não são licença para alterar o escopo aprovado. Explicitar
alternativas no planejamento e consultar o responsável quando mudarem a operação:

- Política de estorno após caixa fechado e recuperação de fechamento incompleto.
- PIN: tamanho, espera, recuperação e rotação da chave após uso.
- Retenção e rotação dos backups, inclusive destino externo ausente.
- Precisão e arredondamento de custo médio, taxas, rateios e grupos promocionais.
- Vencimentos recorrentes em meses curtos e edição de ocorrências futuras.
- Precificação de um carrinho em edição e produto removido/reincluído em comanda.
- Tratamento de compras com frete, devoluções e correções de entradas incorretas.
- Delivery: tentativas físicas adicionais, devoluções e reembolsos, confirmação
  de cartão recebido fora do balcão, bases de taxas e rateio de receita/custo de
  entrega no resultado por produto. Não confundir modalidade com custódia do valor.

## 14. Registro de aprovação

O responsável aprovou em conversa: reconstrução do zero, oito áreas, banco vazio,
tecnologia atual, monólito modular e blocos de atendimento/promoções, caixa,
estoque/compras, financeiro, resultados/relatórios e segurança/backups. Aprovou
também o desenho de delivery: taxa e corrida fixas independentes, remuneração
devida na saída, pagamento antecipado ou ao entregador, acerto explícito e
bloqueio do fechamento por pedidos em andamento ou dinheiro não conferido.

Este documento consolida os blocos; requer revisão explícita antes do plano de
implementação. Nenhuma funcionalidade nova foi implementada nesta etapa.
