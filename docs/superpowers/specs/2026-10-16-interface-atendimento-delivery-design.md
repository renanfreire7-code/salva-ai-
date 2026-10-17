# SALVA AI HEADSHOP — interface, atendimento e delivery

Data: 16/10/2026. Especificação aprovada em conversa, assim como seu plano de
10 tarefas e execução nativa nesta sessão. Documento recuperado da conversa
após a substituição do ambiente; os commits locais de documentação não estavam
na cópia restaurada. Base funcional recuperada do GitHub: `cdf6c55`.

## Objetivo e preservação

Simplificar a operação do pequeno bar: busca rápida, teclado previsível e
vendas/entregas/acertos fáceis de conferir. Evoluir a versão entregue, preservando
Python/Tkinter/SQLite offline, pasta de dados, IDs, PIN, auditoria, transações,
replay, reservas, promoções, custos e backup/fechamento recuperáveis. Testar
somente dados fictícios. Atualizar bancos existentes por migração aditiva com
backup anterior; não reiniciar os cadastros do operador nem importar o legado.

## Navegação e identidade

Substituir as duas fileiras de abas por menu lateral fixo e seleção evidente:

| Grupo | Destinos |
| --- | --- |
| Atendimento | Venda de balcão; Comandas; Delivery |
| Controle | Produtos e estoque; Compras e devoluções; Caixa; Histórico de vendas |
| Gestão | Contas e despesas; Resultado do mês; Lucro por produto; Reposição de estoque |

Auditoria e manutenção continuam acessíveis pelo histórico. Cabeçalho compacto
com SALVA AI HEADSHOP, offline, estado do caixa e logo circular à direita (~56px),
sem distorção. Logo fornecida pelo usuário, exterior transparente; nome completo
também no texto e título da janela. Moto simples monocromática junto de Delivery
(~24px) e menor no menu, sempre acompanhada do texto; asset local, não emoji.

Modo Operate: fundo claro, superfícies brancas, texto escuro, tipografia nativa,
uma ação principal por tarefa. Verde confirma, âmbar alerta, vermelho indica
erro/cancelamento, sempre com texto. Tabelas legíveis, dinheiro à direita,
colunas ajustáveis e rolagem; detalhes ao lado da seleção. Não introduzir cartões
decorativos ou animações que atrasem a operação. Ações destrutivas afastadas.
Dimensionar para 1366×768 e escalas 100%/125% sem reduzir fonte para encaixar.

## Atendimento e teclado

Venda: busca/produtos à esquerda, pedido/itens/promoção/economia/total à direita,
Receber sempre visível. Comandas: lista número/nome/total e detalhe, mantendo
seleção ao atualizar. Delivery: lista, filtros e detalhes com entrega, pagamento
e custódia distintos. Salvar pedido ou selecionar produto não confirma venda.

Busca compartilhada: nome/código atuais, ignorar acentos/caixa/espaços, prefixos
em ordem (`cer hei`) e iniciais consecutivas (`CHL` ou `CH` encontram Cerveja
Heineken Latão). Ambiguidade mostra todos os candidatos, sem escolha arbitrária.
Setas navegam; Enter na busca seleciona e foca quantidade; Enter na quantidade
adiciona uma vez e volta à busca. Produto desativado não entra em novo atendimento.

F1–F12 selecionam produto e focam quantidade em balcão, comanda e editor de
delivery, sem adicionar automaticamente. Editor com foco prevalece sobre fundo;
eventos não propagam duplamente nem operam durante PIN/modal administrativo.

Enter valida e avança campos habilitados, preservando Tab/Shift+Tab e multiline.
Último campo foca Salvar/Continuar, sem submeter ao sair. Enter no botão executa
uma vez. Pagamento, cancelamento e acerto têm resumo/confirmação explícita.
Seletores substituem textos livres para modalidades e Sim/Não. Erros mostram
problema e recuperação junto ao campo e preservam dados digitados.

## Filtros e gestão

Períodos: Hoje, Últimos 7 dias (hoje + seis anteriores), Este mês e Personalizado,
DD/MM/AAAA, período aplicado visível, Filtrar/Limpar. Digitar não aplica consulta
parcial; erro mantém a última consulta válida. Padrão do histórico: Hoje; contas:
mês atual por gasto, com gasto/vencimento/pagamento explicados e situação/categoria.
Pago no período não se confunde com saldo atual. Resultado/lucro permanecem mensais.

Delivery operacional mostra PREPARING/OUT inclusive de dias anteriores, com
filtros independentes de entrega/pagamento; consulta de concluídos/cancelados
pode usar data de criação. Reposição continua estoque atual. Caixa separa gaveta,
modalidades e custódia. Resultado explica contribuição/lucro, não saldo bancário.

## Histórico e acertos

Histórico comercial: uma linha por venda de balcão/comanda ou pedido delivery,
número/nome/data/total/estado/pagamento, detalhes com produtos, quantidades,
preços/promoção, entrega e reembolsos. Período: data da venda no balcão/comanda,
confirmação no delivery, inclusive cancelado antes de sair; explicar no filtro.
Comanda reaberta conserva cada venda/estorno vinculado, sem sobrescrever ou
somar versões. Auditoria técnica separada conserva antes/depois/motivo/autorizações.

Congelar nome nas linhas de pedido e venda, junto aos preços existentes. Dados
anteriores são preenchidos com nome disponível na atualização, sem inventar
nomes antigos já perdidos; documentar limite. Não recalcular valores antigos.

Acerto por pedido/corrida, seleção por clique/checkbox sem depender de Ctrl,
detalhes completos: cliente/telefone/endereço, itens congelados, subtotal/taxas,
total, momento/canal/modalidade, previsto/real de troco, recebedor, reembolsos,
custódia pendente e corrida quitada/pendente, datas. Não multiplicar valor do
pedido nos joins. Mostrar antecipados, cancelados e novas tentativas com suas
corridas devidas e vínculos. Manter consulta aos acertos concluídos e parcelas.
Resumo distingue cobrança, corrida, compensação, dinheiro físico e fundo de
troco; reusar serviço atual com PIN/replay, sem criar receita ao acertar.

## Pagamento e troco do delivery

Quando: Antecipado (Pix ou Link) ou Na entrega (Dinheiro/Pix/Débito/Crédito à vista).
Escolher antecipado não comprova pagamento; pode salvar aguardando confirmação,
mas não sair enquanto total não confirmado. Digital recebido pelo bar. Link é
gerado fora do sistema, referência/URL opcional, confirmação manual e nenhuma
API: modalidade real Débito/Crédito à vista, propondo Crédito. Link não é uma
quinta modalidade, não gera Pix/transferência automática ou parcelamento.

Dinheiro na entrega: Precisa de troco? e Troco para quanto? Se Sim, maior que
total promocional + entrega; exemplo R$45/R$50/R$5. Se Não, troco previsto zero.
Guardar combinado sem movimentar dinheiro. Antes de sair pedido novo não pago
com troco, exigir fundo físico suficiente já registrado com entregador. Usar
fluxos existentes para enviar/devolver fundo. Recebimento confirma valores reais;
diferença do previsto exige conferência explícita, preservando combinado original.
Venda, fundo, compensação e devolução continuam separados; não lançar bruto ou
troco como receita. Cancelamento mantém corrida e separa estoque/reembolso.
Reexpedição cria pedido vinculado e preços atuais; rever troco se total mudou.

## Compatibilidade e entrega

Migração posterior à 013, sem editar checksums anteriores. Novos DTOs têm padrões
compatíveis; chamadas antigas preservam fingerprints e replays após reinício.
Pedidos antigos: momento/troco Não informado/Não registrado, sem nova regra
retroativa ou combinado inventado. Mesma pasta de dados e atualização com backup.

Versão 0.2.0-dev, PNGs locais no ZIP/manifesto, sem pip. Preservar pacote anterior.
Autorização de envio de código/ZIP à branch feat/salva-ai-v2 permanece válida;
sem merge/main/release. Uma revisão independente final, correções importantes
em um lote com RED→GREEN e suíte completa. Inspeção visual agrupada uma vez,
correções em lote e no máximo uma confirmação. Windows nativo 100%/125% e ensaio
com operador são aceitação externa; Linux não os comprova.
