# Salva AI — plano geral de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir a nova aplicação completa, incluindo delivery, em entregas testáveis que preservem o sistema anterior.

**Architecture:** Monólito modular novo em `salva_ai_v2/`, ao lado do código antigo. Serviços recebem conexão/unidade de trabalho explícita; telas apenas orquestram serviços e apresentam resultados. Consultas compartilhadas alimentam telas e relatórios.

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

1. Disco cheio ou processo interrompido entre banco e arquivo: fechamento recuperável e sem falso sucesso — plano 05, tarefa 2.
2. Repetição do comando após reiniciar: devolver resultado anterior sem nova gravação — plano 01, tarefa 1.
3. Troca de data, fuso ou relógio retrocedendo: competência local explícita e espera do PIN não burlada — plano 01, tarefa 2; plano 03, tarefa 1.
4. Produto desativado com reserva existente: impedir novas vendas sem perder atendimento pendente — plano 02, tarefas 1 e 4.
5. Delivery cancelado já pago: separar estorno, devolução física e corrida ainda devida — plano 04, tarefa 3.

## Como ler e executar

Especificação aprovada em conversa após inclusão de delivery. Esta aprovação permite
planejar; o plano e o método de execução ainda precisam de revisão antes de programar.

Dividir a implementação nos cinco planos abaixo, em ordem. Cada um entrega serviços
ou fluxos executáveis com testes próprios. As telas são entregues junto dos respectivos
fluxos; não acumular uma integração de interface inteira para o último dia.

| Ordem | Plano | Resultado verificável |
|---|---|---|
| 01 | [Fundação e segurança](2026-10-16-01-fundacao.md) | Banco exclusivo, transações, auditoria, PIN e shell Tk |
| 02 | [Estoque e atendimento](2026-10-16-02-atendimento.md) | Comprar, vender, reservar, receber e movimentar caixa |
| 03 | [Financeiro](2026-10-16-03-financeiro.md) | Corrigir despesas, pagar e gerar recorrências sem duplicação |
| 04 | [Delivery](2026-10-16-04-delivery.md) | Expedir, receber, conferir e acertar entregas |
| 05 | [Resultados e entrega](2026-10-16-05-entrega.md) | Relatórios, fechamento recuperável, restauração e Windows |

Os cinco planos compõem uma primeira versão completa. Marcos intermediários são
para desenvolvimento e ensaios com dados fictícios, não autorização de uso comercial.

## Arquivos e responsabilidades

- `salva_ai_v2/__main__.py`, `bootstrap.py`: composição e inicialização, sem dados de demonstração na inicialização normal.
- `salva_ai_v2/common/{db,commands,audit,money,clock,errors}.py`: transação, repetição segura, valores e tempo.
- `salva_ai_v2/migrations/`: SQL versionado com identificador de aplicação próprio.
- `salva_ai_v2/security/{service,models}.py`: credenciais, autorizações e recuperação.
- `salva_ai_v2/inventory/{service,models,queries}.py`: produtos, compras, valoração e reservas.
- `salva_ai_v2/pricing/{service,models}.py`: promoções e preços congelados.
- `salva_ai_v2/sales/{service,models,queries}.py`: vendas, comandas, pagamentos e estornos.
- `salva_ai_v2/cash/{service,models,queries,closing}.py`: gaveta, sessões e fechamento.
- `salva_ai_v2/finance/{service,models,queries,recurrence}.py`: obrigações, pagamentos e ocorrências.
- `salva_ai_v2/delivery/{service,models,settlement}.py`: pedidos, corridas e custódia.
- `salva_ai_v2/reporting/{queries,models,xlsx,html}.py`: DTOs e exportação, sem regras alternativas.
- `salva_ai_v2/maintenance/{backup,restore}.py`: cópias consistentes e recuperação.
- `salva_ai_v2/ui/{app,dialogs,products,sales,tabs,cash,finance,delivery,history,results}.py`: telas e atalhos.
- `tests_v2/`: unittest separado dos testes do legado; fixtures em `support.py`.
- `scripts/{demo_v2,build_v2}.py`, `INICIAR_V2.bat`: ensaio e pacote Windows.
- `docs/manual-v2.md`: instalação, operação, recuperação e limitações.
- `salva_ai_v2/vendor/xlsxwriter/`: cópia inalterada da biblioteca incluída, com licença.

Manter cada módulo focalizado. Arquivos dessa lista são criados apenas quando a
tarefa correspondente precisar deles. Não gerar toda a árvore vazia antecipadamente.

## Contratos comuns

Serviços recebem `Database` no construtor. Escritas recebem `command_id: str`
(UUID) estável por intenção do usuário. Repetir ID com os mesmos dados retorna
o resultado anterior; com conteúdo diferente gera `ConflictError`. Alteração,
auditoria e resultado do comando são confirmados juntos em `BEGIN IMMEDIATE`.
Nenhum serviço chama outro iniciando uma transação independente: usar a mesma
unidade de trabalho nas operações compostas.

Retornos públicos são dataclasses imutáveis com campos definidos na tarefa.
Persistir datas de negócio ISO locais e instantes UTC com fuso; a interface usa
datas brasileiras. Injetar relógio nos testes. Erros de negócio são exceções
específicas com mensagem em português; não capturar tudo como sucesso.

`AdminGrant` é uma autorização em memória, curta, vinculada ao tipo de ação;
nunca um booleano fornecido pela tela. Validação ocorre no serviço. Métodos
marcados protegidos recebem `grant: AdminGrant, reason: str`.

## Decisões propostas para aprovação do plano

Estas escolhas completam os detalhes deixados na especificação:

1. **Precisão:** preços e pagamentos em centavos; estoque guarda quantidade e valor
   total em centavos. Custo unitário é a razão exata valor/quantidade. Na saída,
   arredondar o custo total HALF_UP e subtrair da valoração; a última saída leva
   todo o residual. Nunca recalcular CMV histórico. Taxas em pontos-base;
   rateios usam maiores restos, com desempate por ID.
2. **PIN:** seis dígitos; PBKDF2-HMAC-SHA256 com salt aleatório de 16 bytes e
   600.000 iterações, comparação constante e versão dos parâmetros. Após cinco
   erros, espera de 30 s, dobrando até 15 min; prazo persistente e controle de
   relógio conservador. Chave de recuperação aleatória de 32 bytes, exibida uma
   vez, trocada após uso. Autorizações de 60 s, específicas e consumidas na ação.
3. **Preços:** congelar carrinho na primeira inclusão; oferecer reinício explícito
   do carrinho para usar condições novas. Na comanda, manter condição do produto
   mesmo se removido e reincluído. No delivery, congelar na confirmação do pedido.
4. **Recorrências:** dia 29/30/31 vira o último dia válido do mês. Alterar regra
   só afeta ocorrências ainda não geradas; a gerada é editada individualmente.
5. **Estornos:** sem apagar venda. Mesmo caixa aberto permite reversão; após
   fechamento, lançar correção e eventual reembolso no caixa atual aberto, com PIN
   e referência original. Reabertura de comanda continua restrita ao caixa original.
   Não supor devolução de Pix/cartão nem retorno físico de mercadoria.
6. **Compras:** receber uma compra não exige frete. Campo opcional de frete pode
   integrar custo total da compra, com rateio por valor dos itens. Correção de
   entrada não consumida pode ser revertida com PIN; se já houve consumo, usar
   ajuste auditado sem reescrever CMV. Devolução ao fornecedor terá operação
   explícita com quantidade/custo e tratamento financeiro, sem estoque negativo.
7. **Delivery:** uma saída física gera uma corrida; repetir comando não gera outra.
   Reexpedição real após retorno conferido exige confirmação e cria nova corrida.
   Crédito/débito na entrega exige confirmação manual do recebimento na maquininha;
   isso não é dinheiro em custódia do entregador. Taxa de cartão incide no total
   efetivamente cobrado, incluindo taxa de entrega. Separar resultado da entrega
   do lucro dos produtos para não distorcer o rateio de produtos. Se sair troco
   com o entregador, controlar transferência e devolução dessa custódia, sem
   tratá-la como despesa.
8. **Backups:** inicialmente sem exclusão automática. Exibir espaço/erros e permitir
   limpeza manual explícita de cópias identificadas; nunca apagar banco ativo ou
   único backup válido. Falha de cópia externa aparece como aviso, sem afirmar
   sucesso externo; cópia local verificada continua obrigatória no fechamento.
9. **Fechamento recuperável:** persistir intenção e valores contados em estado
   CLOSING, bloquear atendimento e gerar relatório/cópia por caminhos temporários.
   Confirmar CLOSED no banco antes da cópia final, ainda com marcador de artefatos
   pendentes; finalização da operação só após verificar/promover arquivos. Reinício
   retoma esse marcador. Backup final registra caixa encerrado e é autossuficiente;
   sua restauração reconcilia marcadores sem reabrir o caixa.
10. **Cancelamento/reembolso:** valor recebido, receita, devolução de produto e
    obrigação de devolver dinheiro são fatos separados. Uma corrida já iniciada
    continua devida. A interface guia os passos pendentes e impede fechamento
    com pedido/recebimento/reembolso sem resolução explícita.

## Qualidade, Git e revisão

Em cada tarefa: teste que falha por comportamento ausente, implementação mínima,
teste verde, revisão do diff e commit focalizado. Executar testes existentes do
legado como regressão ao final de cada plano quando seus arquivos compartilhados
forem tocados; não adaptar testes antigos para encobrir falhas novas.

Comandos padrão a partir da raiz:
`python3 -m unittest discover -s tests_v2 -t . -v`.
UI Linux:
`PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t . -v`.
Windows: mesmo comando com `py -3`, sem Xvfb, e ensaio manual documentado.

A verificação deste planejamento é documental. Nenhum teste do aplicativo novo
foi executado ou declarado aprovado. O plano não autoriza merge nem release.

## Método de execução a escolher

- **Inline/native — recomendação:** implementar e verificar uma tarefa por vez
  nesta sessão, com revisão independente do conjunto ao final. Evita contextos
  novos a cada tarefa em módulos fortemente ligados por contratos.
- **Com subagentes:** implementador e revisor por tarefa, com maior custo de
  contexto e mais verificações independentes intermediárias.

Não iniciar execução antes da revisão deste plano e escolha do método.
