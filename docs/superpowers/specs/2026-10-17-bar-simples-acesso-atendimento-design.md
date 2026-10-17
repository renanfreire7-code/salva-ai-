# Bar Simples — acesso, identidade e atendimento

## Objetivo e decisões do usuário

Facilitar a operação do pequeno bar por seu proprietário, mantendo o PDV offline
em Python/Tkinter/SQLite e preservando os dados da reconstrução atual. O usuário
aprovou: nome Bar Simples, logo opção 3 Tradicional (balcão, banquetas e copo
americano), uma conta por estabelecimento criada no primeiro acesso, senha
para entrar e PIN de exatamente três dígitos nas operações sensíveis. Também
aprovou complemento do endereço, busca uniforme por palavras/iniciais, nomes
completos e esclarecimento das ações de delivery. Não haverá múltiplos usuários,
perfis ou integrações online nesta evolução.

Este documento consolida o desenho para revisão; não autoriza por si só alterações
no programa. Detalhes recomendados abaixo ficam sujeitos à revisão do usuário.

## Acesso e recuperação — proposta

Primeira configuração em instalação nova: usuário, senha, confirmação da senha,
PIN de três dígitos e confirmação do PIN. Usuário não vazio; senha com pelo menos
oito caracteres, aceitando espaços e sem composição obrigatória. PIN aceita
exatamente três algarismos, incluindo zeros iniciais; sem valor padrão. Senha e
PIN são segredos distintos, armazenados com salt e hash, nunca em texto puro.

Inicializações seguintes exibem uma tela de entrada com logo, usuário, senha,
mostrar/ocultar senha, Entrar e Recuperar acesso. Enter no usuário leva à senha;
Enter na senha leva ao botão Entrar; somente a confirmação seguinte envia. Sem
salvar a senha automaticamente ou exigir internet. Erro mantém o usuário e
permite corrigir a senha. Antes de autenticar, telas operacionais não ficam
acessíveis. Fechar a entrada encerra a aplicação e libera o bloqueio da pasta.

Login e PIN terão contagem de falhas e espera temporária após cinco erros
consecutivos, com mensagem e tempo restante. Preservar a proteção existente de
PIN contra autorizações expiradas, reutilização e consumo fora da transação.
Autenticar não concede autorização permanente para operações financeiras.

Recuperação offline por chave secreta exibida somente na configuração. A chave
permite definir nova senha/PIN, sem redefinir o banco. Recuperação concluída
invalida autorizações antigas e gera outra chave. Não haverá senha mestre,
recuperação por e-mail ou suporte com acesso aos segredos.

### Instalações existentes

Não truncar o PIN antigo para três dígitos e não redefinir credenciais
silenciosamente. Na primeira atualização, exigir o PIN atual de seis dígitos
(ou a chave de recuperação existente) antes de criar login/senha e escolher o
novo PIN de três dígitos. Enquanto a transição não terminar, a instalação
continua protegida pelo PIN antigo, sem acesso operacional pela atualização.

Migração aditiva com backup prévio, preservando saldos, IDs, produtos, histórico e
fechamentos. Conclusão da transição é atômica: falha ou cancelamento não deixa
uma conta parcialmente configurada. Manter a pasta SalvaAiHeadshopV2: mudar a
marca não cria outro banco nem exige copiar arquivos manualmente.

## Identidade e telas

Nome visível Bar Simples, logo Tradicional em verde escuro e terracota. Preparar
versão completa para entrada e versão simplificada para cabeçalho/ícone, mantendo
balcão e copo americano reconhecíveis. Arquivos PNG locais no pacote, sem download
em execução; gerar adaptações a partir da opção escolhida. Referência aprovada:
`docs/design/bar-simples-propostas-logo.png`, terceira opção.

Continuar o tema claro e navegação lateral existentes. Entrada com uma área de
marca e formulário legível, sem animações que atrasem operação. Controles e
mensagens devem caber em 1366×768; Windows 100%/125% requer ensaio nativo.

## Endereço do delivery

Manter endereço/número e referência existentes; adicionar complemento opcional
separado (apartamento, bloco, fundos). Guardar no pedido, mostrar no editor,
detalhes, histórico e discriminação do acerto. Reentrega copia o complemento.
Pedidos antigos recebem complemento vazio, sem reinterpretar o campo referência.
Estender DTOs/payloads sem invalidar replays de comandos antigos.

## Busca e leitura de produtos

Mesmo comportamento no balcão, comanda e editor delivery: código, texto parcial,
prefixos das palavras e iniciais. `hei` encontra Cerveja Heineken; `cer hei` e
`CHL` encontram Cerveja Heineken Latão. Ignorar maiúsculas/acentos. Resultados
ambíguos exigem seleção. Preservar F1–F12 e seleção → quantidade → adicionar.

A busca básica já existe na 0.2: verificar sua aplicação nas três superfícies,
sem introduzir busca aproximada ou cadastro de sinônimos nesta entrega. Sinônimos
customizados são uma possibilidade futura, não requisito aprovado específico.

Nomes completos nas listas operacionais, pedidos, históricos e acertos: coluna
Produto com prioridade de espaço e quebra em múltiplas linhas onde necessário.
Não depender exclusivamente de tooltip, reticências ou rolagem horizontal para
identificar o produto. Quantidade, preços e ações continuam legíveis e acessíveis.
Como Treeview nativo tem limitações para altura variável, avaliar apresentação
composta de linhas com nomes quebrados nas superfícies que precisarem, preservando
IDs de seleção e navegação por teclado. Não reduzir fonte para encaixar nomes.

## Ações do delivery

Rótulos: Registrar reembolso, Conferir produtos devolvidos e Criar nova tentativa
de entrega. Explicação curta junto à ação e resumo de pedido/cliente/valores antes
da confirmação. Cancelamento também ganha resumo antes de PIN/motivo.

Reembolso confirma devolução financeira efetiva na modalidade recebida, sem
transferência bancária automática. Retorno ao estoque somente para unidades
conferidas em condição de revenda. Nova tentativa mantém vínculo, resolve
cancelamento/reembolso/retorno anterior conforme regras existentes, usa preços e
taxas atuais e gera outra corrida somente na nova saída. Preservar combinado de
troco separado de recebimento e fundo físico. Não mudar fórmulas financeiras.

Ajuste menor já registrado: Enter no nome da comanda passa a focar Abrir comanda;
a confirmação seguinte cria. Evitar criação acidental ao sair do campo.

## Verificação e limites

Regressões de PIN novo/antigo, transição interrompida, recuperação, bloqueio de
tentativas, proteção antes do login, fechamento/liberação de instância e
migração populada. Verificar complemento/reentrega/replay; busca nos três fluxos;
nomes longos com teclado e ações visíveis; histórico, pagamentos e acerto sem
alteração de saldos. Executar suítes nova e legado e conferir pacote extraído,
PNGs e manifesto. Inspeção visual agrupada com correções em lote.

Não trocar ZIP atual nem publicar artefatos finais antes da implementação e
verificação. Sem merge/main ou release. Escrever plano de implementação após
aprovação deste documento; combinar método de execução na apresentação do plano.
