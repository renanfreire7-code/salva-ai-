# Bar Simples — guia de instalação e operação

## Estado desta evolução

O Bar Simples sucede a reconstrução Salva AI 0.2.0-dev, mantendo a mesma pasta
de dados. Esta é a versão de desenvolvimento **0.3.2-dev**, para ensaio com dados fictícios.
Os resultados de verificação estão no relatório `validacao-bar-simples.md`.
Windows nativo nas escalas 100% e 125% ainda precisa de ensaio antes de uso real.

## Marca da entrada e do estabelecimento

A entrada (cadastro, login e recuperação) usa **Bar Simples**. Após o login,
o título da janela, o cabeçalho, a logo e o ícone usam **SALVA AI HEADSHOP**.
A logo do estabelecimento mantém o desenho anterior, com contornos refinados.
A moto continua identificando o delivery. Ao restaurar um backup e retornar ao
login, a identidade Bar Simples volta a aparecer até a nova autenticação.

## Usuário, senha e PIN

No primeiro acesso, escolha o usuário, uma senha com pelo menos oito caracteres
e um PIN de exatamente três dígitos (incluindo zeros iniciais). Confirme ambos.
Espaços fazem parte da senha. Guarde a chave de recuperação fora do computador:
ela será mostrada uma vez, antes de entrar no atendimento.

Na atualização de uma instalação existente, confirme seu PIN anterior de seis
dígitos ou escolha Chave de recuperação. Só depois será criada a conta com o
novo PIN. Os números antigos não são cortados nem substituídos automaticamente.
Se cancelar, pode repetir a configuração sem perder os dados cadastrados.

A senha permite entrar no programa; o PIN confirma operações sensíveis como
reembolso, ajustes e exclusões. Após cinco erros consecutivos há espera
temporária. Reiniciar o programa não remove esse tempo de espera.

Em Recuperar acesso, informe a chave e escolha novo usuário, nova senha e PIN de
três dígitos. Não é necessário lembrar o usuário ou a senha antigos. Ao concluir,
o login terá o novo usuário preenchido; digite a nova senha para entrar. Guarde a
nova chave exibida: a anterior deixa de valer. Produtos, vendas e histórico ficam
preservados. Sem chave não existe senha mestre.
Usuário, senha e PIN funcionam sem internet; o banco não é criptografado por
essas credenciais. Proteja também o acesso ao computador e aos backups.

Restaurar um backup pede novo login e usa as credenciais que estavam naquele
backup. Se ele for anterior à conta, a atualização de acesso será solicitada
novamente com o PIN ou a chave que existiam no backup.

## Instalação no Windows

1. Instale Python 3.12 ou superior com Tkinter pelo instalador oficial.
2. Extraia todo o ZIP em uma pasta própria, diferente da versão antiga.
3. Execute **INICIAR_V2.bat**. Não mova o BAT para fora da pasta extraída.
4. Cadastre usuário, senha e PIN de três dígitos; confirme e guarde a chave de recuperação fora do computador.
5. Cadastre os produtos e entradas com dados fictícios para o ensaio inicial.

Não é necessário pip, servidor, conexão com internet ou conta em serviço externo.
O ZIP contém o código, a biblioteca XlsxWriter com licença e manifesto SHA-256.
Ainda não foi produzido um instalador executável independente do Python.

## Dados separados e início para desenvolvimento

Banco novo: `~/SalvaAiHeadshopV2/dados/salva_ai.sqlite3`.
Backups: `~/SalvaAiHeadshopV2/backups/`.
Fechamentos imprimíveis: `~/SalvaAiHeadshopV2/relatorios/`.

O aplicativo não abre nem importa `~/SalvaAiHeadshop`. Não copie o banco antigo
para o diretório novo. Apenas uma instância pode abrir cada pasta de dados.

Na raiz do checkout:

```bash
python3 -m salva_ai_v2
python3 -m salva_ai_v2 --data-dir /tmp/salva-ai-ensaio
python3 -m scripts.demo_v2
python3 -m scripts.build_v2
```

A demonstração usa uma pasta temporária e dados fictícios, removidos ao fechar.
Use um PIN fictício no ensaio. Não altere HOME para testar.

## Atualizar das reconstruções 0.1.0-dev ou 0.2.0-dev

Feche a versão anterior, faça uma cópia da pasta `~/SalvaAiHeadshopV2` e
extraia o ZIP Bar Simples 0.3.2-dev em outra pasta de programa. Inicie pelo novo BAT.
A pasta de dados continua a mesma: não copie nem substitua o banco pelo ZIP.
A migração é aditiva e cria um backup antes de alterar a estrutura; preserva
IDs, PIN, estoque e movimentos. A versão 0.3.6-beta de referência não é importada.
Depois de atualizar, use o código Bar Simples 0.3.2; não abra o banco atualizado com versões anteriores.
Em pedidos anteriores, momento de pagamento e troco aparecem como não informados.

## Organização das telas

- **Atendimento:** Venda de balcão, Comandas e Delivery.
- **Controle:** Produtos e estoque, Compras e devoluções, Caixa e Histórico de vendas.
- **Gestão:** Contas e despesas, Resultado do mês, Lucro por produto e Reposição de estoque.

A navegação fica na lateral; mudar de tela conserva o pedido em andamento.
A logo fica no canto superior direito e a moto identifica o Delivery.
Busque por nome, código, começo das palavras (`cer hei`) ou iniciais (`CHL`).
Se houver mais de um resultado, selecione o desejado. F1–F12 também funciona
no editor do Delivery: seleciona e leva à quantidade, sem adicionar sozinho.
Enter avança pelos campos válidos; no último campo leva ao botão Salvar.
Um novo Enter confirma. Erros mantêm os valores digitados para correção.
O nome da comanda também segue essa regra: Enter foca Abrir comanda, e a próxima
confirmação cria. As listas de produtos mostram nomes completos em linhas que
se ajustam ao texto, com rolagem vertical; selecionar não altera o nome salvo.

Os filtros oferecem Hoje, Últimos 7 dias, Este mês e Personalizado. Digitar
ou escolher valores não altera a consulta até clicar em **Filtrar**.
O período aplicado aparece abaixo; **Limpar filtros** restaura o padrão.
No resultado mensal, use **Consultar** para aplicar o mês.

Os formulários indicam o formato da data. Valores aceitam formato brasileiro,
por exemplo `1.234,56`. Quantidades são unidades inteiras.

## Produtos, entradas e promoções

Cadastre nome, preço normal, unidades por caixa/fardo e estoque mínimo.
Entradas podem ser em unidades ou caixas/fardos; informe o custo total e frete.
Indique compra pendente ou já paga. Dinheiro da gaveta exige caixa aberto, saldo
e PIN. A entrada registra estoque e obrigação financeira uma única vez.

Em **Compras / devoluções**, consulte entradas e itens. Para uma entrada incorreta
sem movimentos posteriores, use **Reverter compra** e registre a entrada correta.
A reversão é conservadora: compras já consumidas exigem correção auditada própria.
Valores já pagos geram crédito identificável ao fornecedor, sem entrada automática
de dinheiro. Para devoluções parciais, selecione o item e informe as unidades.

A aba **Créditos do fornecedor** distingue valor, liquidado e pendente. Confirme
o recebimento efetivo por modalidade ou abata o crédito no saldo pendente da
própria compra. Só **Dinheiro na gaveta** aumenta o caixa físico. A liquidação
exige PIN e motivo; pagamentos vinculados a abatimentos e compras revertidas
ficam protegidos contra anulação genérica no Financeiro.

O custo médio é calculado a partir de quantidade e valor do estoque; vendas
guardam o custo histórico. Alterar um preço não muda vendas anteriores.
Editar cadastro, ajustar perdas e desativar produtos exige autorização e motivo.

Configure uma promoção por produto: por exemplo, unidade R$ 5 e grupo de três
por R$ 12. Quatro unidades custam R$ 17; seis custam R$ 24.
Produtos diferentes não se misturam. A comanda preserva a condição da primeira
inclusão, inclusive se o item for retirado e incluído de novo. Editar preço normal
desativa uma promoção que deixe de oferecer economia para novos atendimentos.

Associe F1–F12 a produtos. A tecla seleciona o produto e leva à quantidade;
**não registra venda automaticamente**.

## Atendimento e recebimentos

Abra o caixa com troco inicial antes de vender. Na venda direta, adicione produtos,
confira quantidades e promoções e use Receber pagamento. Dinheiro informa
valor entregue e troco. Pix, débito e crédito à vista exigem confirmação de
recebimento; o aplicativo não consulta bancos nem maquininhas.

Comandas são identificadas por nome e número. Nomes iguais geram aviso.
Adicionar itens reserva estoque. Pagar converte reserva em baixa definitiva.
Reduzir/remover itens registrados ou cancelar exige PIN e motivo.

Sem fiado, desconto manual, parcelamento ou divisão do pagamento da venda.

## Caixa

Somente dinheiro recebido na gaveta altera o saldo físico esperado.
Pix/cartões ficam separados. Reforços e retiradas têm motivo e autorização;
não são receita/despesa automaticamente.

Fechamento exige resolver comandas, pedidos de entrega e dinheiro a conferir.
Informe o valor efetivamente contado. Diferença exige PIN e justificativa.

O fechamento gera relatório HTML imprimível e backup local verificado.
Caixa e relatório mostram **recebido, reembolsado e líquido por modalidade**.
Delivery entra nessa conferência somente quando o recebimento é confirmado;
saída para entrega não significa recebimento. Dinheiro com o entregador integra
os recebimentos, mas só a transferência efetiva entra nos movimentos da gaveta.
Estorno e reembolso são fatos separados; o relatório preserva o caixa original
quando o reembolso ocorre em outro caixa.
Se houver falha, o sistema bloqueia operações conflitantes até recuperar os
artefatos. Reinicie ou use **Retomar fechamento**; não abra outro caixa para
contornar a pendência. Corridas ainda não pagas podem continuar como contas a pagar.

## Financeiro mensal

Cadastre descrição, categoria, valor, data do gasto e vencimento.
Use Quitar para informar data e modalidade reais. Se saiu da gaveta, o sistema
vincula a retirada ao pagamento, sem exigir um segundo lançamento manual.

- Editar preserva ID e histórico de antes/depois, motivo e autorização.
- Excluir retira dos cálculos ativos; não apaga histórico nem devolve dinheiro.
- Pagamentos permite corrigir data/modalidade e anular registro com motivo.
  Corrigir uma saída física exige conferir o que realmente voltou à gaveta.
- Verde/Paga, cinza/Pendente e vermelho/Vencida sempre têm texto.
  Vencimento hoje não é considerado atraso.
- O aviso de possível duplicidade permite confirmar repetições legítimas.

A consulta abre no mês atual por data do gasto. É possível escolher intervalo,
vencimento ou pagamento, categoria, descrição e situação. Vencido é parte do
saldo pendente; não some os dois novamente. No filtro por pagamento,
**Pago no período** soma apenas parcelas
pagas entre as datas escolhidas. Situação e saldo pendente mostram o estado atual
das contas selecionadas, considerando todos os pagamentos dessas contas.

Em Contas mensais, crie regras e gere o mês selecionado explicitamente.
A ocorrência nasce pendente. Dia 31 vira o último dia válido nos meses curtos.
Editar a regra só afeta ocorrências futuras ainda não geradas.

Use **DAS MEI** para o lançamento correspondente. Despesa de DAS da competência
substitui a provisão, sem dedução em dobro. Compra de estoque não é deduzida
novamente como despesa operacional: seu custo entra no CMV ao vender.

## Delivery e acerto com entregador

Pedidos são cadastrados manualmente; não há integração com WhatsApp, mapas ou
plataformas. Preencha endereço e número, complemento opcional (apartamento, bloco, fundos)
e ponto de referência em campos separados. O complemento acompanha os detalhes
do pedido, histórico, acerto e nova tentativa. Pedidos anteriores ficam com
complemento vazio, preservando a referência cadastrada.

Configure dois valores fixos independentes: taxa do cliente e
remuneração do entregador. O pedido guarda os valores combinados.

Ao confirmar, reserva estoque. **Saiu para entrega** baixa os produtos e gera
a obrigação da corrida, mesmo se a entrega falhar depois.
Entregue não significa pago. Confirme pagamento antecipado ao bar ou recebimento
pelo entregador. Pix/cartão pertence à conta/maquininha do bar; só dinheiro físico
fica sob custódia do entregador.

No novo pedido, escolha **Antecipado** (Pix ou Link de pagamento) ou
**Na entrega** (Dinheiro, Pix, Débito ou Crédito à vista). Link é uma referência
externa opcional; informe a modalidade real conforme o comprovante. O programa
não gera links nem confirma pagamento automaticamente. Antecipado pendente
pode ser salvo, mas precisa do recebimento confirmado antes de sair.

Para dinheiro, selecione **Precisa de troco?** e **Troco para quanto?**.
O pedido mostra o troco previsto, sem registrar dinheiro. Envie e registre o
fundo antes da saída se houver troco. No recebimento, confira o valor real;
se diferir do combinado, a confirmação mostra a diferença explicitamente.
Reembolso usa a modalidade do recebimento efetivamente confirmado, inclusive
quando o Link foi combinado em crédito e recebido em débito.
**Pendentes** inclui pedidos antigos em preparação/na rua, entregues sem pagamento
e cancelados com reembolso pendente, sem limitar ao dia atual.

Em **Acertar entregas**, selecione recebimentos e corridas, confira dinheiro
entregue à gaveta, pagamento da gaveta e eventual compensação combinada.
Exemplo: recebeu R$ 45, deve receber R$ 7 por corrida e entrega R$ 38 ao bar.
O caixa recebe apenas R$ 38 físicos; os outros R$ 7 quitam a corrida por compensação.

Selecione um pedido e marque recebimento e/ou corrida; duplo clique inclui
ou retira ambos, sem precisar de Ctrl. O painel mostra cliente, endereço,
produtos, valores, troco, pagamentos, retornos e reembolsos. **Acertos anteriores**
permite conferir vínculos e valores de cada acerto parcial ou concluído.

Enviar e devolver troco são transferências registradas, não despesas.
Sem troco registrado suficiente, não confirme recebimento que exija devolução.

As ações **Registrar reembolso**, **Conferir produtos devolvidos** e
**Criar nova tentativa de entrega** exibem um resumo antes de pedir o PIN.
Recusar a confirmação não registra a operação. Na devolução, quantidades
inválidas permanecem preenchidas para correção.

Cancelar depois da saída não elimina a corrida. Confira separadamente retorno de
mercadoria em condição de revenda e reembolso efetivamente realizado.
Uma nova tentativa cria pedido vinculado, nova saída e nova corrida com valores
atuais, após resolver o anterior.

## Resultado e relatórios

Margem de contribuição = faturamento após promoções − custo histórico − taxas.
Resultado por produto desconta rateio de despesas e DAS pelo faturamento.
Entrega tem receita/custo separados. Pagamento de corrida não registra a despesa
uma segunda vez.

O resultado é estimativa gerencial, não saldo disponível nem apuração fiscal.
Configure taxas confirmadas em Lucro por produto → Taxas e DAS. Dados
desconhecidos geram avisos. Correções entram no período da operação, sem mudar
o fato original. Relatórios Excel identificam o período e usam valores em reais.

Previsão de compras usa estoque disponível e mínimo e sugere caixas completas.
Não gera compra nem pagamento automaticamente.

## Histórico, estorno e reembolso

Histórico de vendas separa Balcão, Comanda e Delivery, com número, cliente,
valor, situação do atendimento, situação do pagamento e modalidade real.
Nos detalhes de balcão/comanda, dinheiro mostra também o valor entregue e troco.
Selecione uma linha para ver produtos, quantidades, promoção
e total. Os nomes guardados na venda não mudam ao renomear o cadastro.
Para fatos anteriores à atualização, o nome disponível no momento da migração
é preservado; nomes antigos já perdidos não podem ser reconstruídos.
**Auditoria e manutenção** abre eventos, correções e motivos de alterações.
A confirmação de venda mostra número, valor, modalidade e produtos; use esse
número para a correção. Há rolagem horizontal para detalhes longos.
Corrigir venda exige PIN; devolução de produtos e devolução de dinheiro são
confirmações distintas. Reabrir comanda paga só é permitido no caixa original
ainda aberto. Após fechar, a correção financeira entra no caixa atual, preservando
o anterior.

Se o reembolso ficar pendente, use **Concluir reembolso** após realizá-lo.
Para delivery, use exclusivamente cancelamento, devolução e reembolso na tela
Delivery. O programa não transfere Pix nem devolve cartão automaticamente.

## Backup, restauração e PIN

Histórico de vendas → Auditoria e manutenção → Backups oferece cópia manual, verificação e pasta adicional.
A cópia local verificada é obrigatória no fechamento. Falha na pasta adicional
é informada separadamente. Uma pasta no mesmo disco não protege contra perda
do equipamento; prefira uma cópia fora dele.

Restaurar exige PIN, consulta e confirmação explícita. O banco atual é copiado
antes da substituição. Feche outras ferramentas que estejam usando o arquivo.
Depois, abra o aplicativo novamente; o PIN será o existente no backup.
Um journal permite recuperar uma substituição interrompida.

A senha, o PIN e a chave não são armazenados em texto puro. Após cinco erros há espera
progressiva. A chave permite trocar o PIN e é renovada após uso.
Sem PIN e sem chave não há senha mestre oculta.
O PIN não criptografa o banco; proteja acesso ao computador e aos backups.

## Verificações de desenvolvimento

Linux sem monitor:

```bash
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t . -v
```

Windows com display:

```bat
py -3 -m unittest discover -s tests_v2 -t . -v
```

Também preservar a suíte do legado. O pacote final exclui bancos, backups, testes
e caches e inclui manifesto de integridade. Não publicar uma release nem
substituir o aplicativo em uso sem autorização.

## Ensaio pendente com o proprietário no Windows

- Abrir o pacote extraído em caminho com espaços/acentos.
- Conferir 1366 × 768 com escalas de 100% e 125%, teclado e visibilidade de ações.
- Cadastrar, comprar, vender, usar promoção, receber/cancelar comanda e conferir caixa.
- Corrigir despesas, gerar recorrência, operar entrega e acertar com entregador.
- Simular backup externo ausente e restauração de dados fictícios.
- Registrar dificuldades encontradas antes de colocar dados reais.
