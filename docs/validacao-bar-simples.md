# Bar Simples — registro de implementação e validação

Base da evolução:99d71f1; branch feat/salva-ai-v2. Especificação e dois planos
aprovados pelo usuário. Execução nativa nesta sessão, uma revisão independente
final após integrar acesso e atendimento. Sem merge/main/release.

## Acesso e identidade

A1: PIN novo de três dígitos e migração do PIN legado de seis; testes alvo8/8 e
suíte159/159. A2: conta offline, transição atômica, espera e recuperação; alvo15/15
e suíte166/166. A3: entrada protegida e ciclo de vida; alvo10/10 e suíte173/173.
A4: identidade Tradicional e demonstração após cadastro; alvo14/14, e inspeção
agrupada dos quatro modos/cabeçalho. A inspeção encontrou o botão Fechar cortado
na transição: regressão de limites dos ancestrais falhou antes e passou após a
correção; três testes de marca/geometria aprovados. Uma confirmação visual feita.

A5: teste integrado de banco014 populado detectou que a restauração antiga não
aplicava migrações antes da entrada; corrigido para upgrade com backup antes do
callback. Falha na montagem parcial da entrada recebeu regressão própria para
fechamento sem deixar instância bloqueada. Alvo14/14, suíte179/179 e legado30/30 aprovados.

## Decisões de execução

- Checkout isolado existente, conforme preferência aprovada; custo: isolamento
  depende do checkout fornecido pela nuvem.
- Scripts de execução das skills e referência auxiliar de testes não disponíveis
  localmente; briefs, comandos e ledger equivalentes fora do checkout; custo:
  orquestração manual.
- Launcher Impeccable indisponível e sem PRODUCT/DESIGN existentes; contexto vem
  do projeto e desenho Operate nativo aprovado; custo: verificação visual manual.
  Revisão final única examinou também o resultado visual, preservando o método
  de execução aprovado.

## Limites

Interface Tk real sob Xvfb no Linux. Isso não comprova Windows nativo/DPI nem
aceite pelo operador. Pacotes anteriores permanecem preservados. Validação nativa no Windows em
100%/125% e aceite do operador permanecem pendentes.


## Atendimento e integração

B1: complemento persistente, reentrega, payload/replay0.2 e retenção no editor;
alvo23/23, suíte183/183. B2: linhas de produtos com nomes completos, seleção por
ID/teclado e busca nos três atendimentos; alvo40/40, suíte189/189. Inspeção agrupada
com nomes longos e confirmação única; detalhes comerciais separados em painéis
para preservar também as informações de pagamento. B3: confirmação antes do PIN,
recusa sem mutação, devolução com quantidade preservada inclusive em erro de
disco, detalhes com complemento e Enter da comanda; alvo44/44, suíte196/196.

O ensaio completo0.2→Bar Simples passou junto aos dois testes do empacotador.
Ele confirma login/PIN, busca nos três fluxos, promoção, comanda, antecipado Pix,
dinheiro com fundo/troco, acerto físico/compensação, fechamento e backup,
reinício/replay de comando antigo e restauração autenticada. A mudança da versão
para0.3.0-dev foi observada falhando no teste de distribuição antes da alteração.

A demonstração `scripts/demo_v2.py` também acompanha o ZIP: a suíte extraída
precisa exercitar o mesmo fluxo real de cadastro, sem importar arquivos do
checkout. Custo dessa decisão: um módulo adicional no pacote. O manifesto
confere cada arquivo; banco, credenciais, caches e testes não são distribuídos.

## Revisão independente final

Uma revisão consolidada examinou os dez focos dos planos, código, testes e
quinze capturas. Três achados Important foram aceitos e receberam regressões
que falharam antes das correções:

- Restauração: após iniciar a substituição do banco, qualquer resultado encerra
  a sessão anterior e limpa autorizações; falha na tela de entrada fecha a aplicação.
- Reentrega legada: o resumo informa a saída e a corrida imediatas, preservando
  a compatibilidade do domínio antigo; pedidos novos continuam em preparação.
- Confirmações extensas: janela nativa com texto rolável e ações sempre visíveis,
  sem omitir produtos ou fatos financeiros; fechar/Escape recusa a operação.

Nenhuma segunda revisão foi solicitada. Minor adiado: o rodapé pode continuar
mostrando “Entre para abrir o atendimento” após login até outra operação atualizar
a mensagem. Custo: informação visual temporariamente desatualizada, sem bloquear
a operação nem liberar acesso indevido.

## Verificação da entrega

Código verificado:63b262c. Após as correções da revisão, passaram os30 testes
direcionados,201/201 testes novos no checkout,199/199 no ZIP extraído em pasta
com espaços/acentos (sem o empacotador) e30/30 do legado, todos com Tk/Xvfb
1366×768. Sem falhas nem skips nessas execuções finais. Uma chamada do legado
sem Xvfb antes da execução final teve cinco skips e uma falha de estado de import;
reexecutada no ambiente gráfico previsto, passou30/30 sem alteração de código.

Manifesto dos157 arquivos conferido, ZIP íntegro e código/manual idênticos ao
checkout. Nenhum banco, credencial, cache ou teste acompanha a distribuição.
Arquivo: `dist/Bar_Simples_0.3.0-dev.zip`.

SHA-256: `e5349ea6a370e287c622a29c0758b314f8f05e5f9f16eed0e07b0b0dd99a4965`.

Entrega somente na branch `feat/salva-ai-v2`, preservando os pacotes anteriores.
Download: https://github.com/renanfreire7-code/salva-ai-/raw/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.3.0-dev.zip
