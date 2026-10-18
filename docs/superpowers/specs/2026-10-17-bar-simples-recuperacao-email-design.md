# Bar Simples / Salva AI — recadastro e recuperação por e-mail

Estado: aprovada pelo usuário nesta sessão; implementação ainda não iniciada. Substitui a entrega
antiga0.2 como direção de evolução, preservando a base atual0.3.2 e suas melhorias.

## Resultado para o operador

Manter produtos, estoque, comandas, vendas, despesas, caixa, entregas, relatórios,
identificadores e histórico. Refazer somente o cadastro de acesso. Entrada mantém
Bar Simples; após login, SALVA AI HEADSHOP com logo refinada e moto no delivery.
Continua uma conta por estabelecimento e PIN administrativo de três dígitos.
Não reproduzir credenciais reais compartilhadas em conversa em arquivos ou testes.

O atendimento e o login usual continuam offline. Confirmar o e-mail e recuperar
credenciais exigem conexão. A nova recuperação não depende da chave antiga.

## Decisões de arquitetura

Opção escolhida pelo usuário: serviço online de autenticação, em vez de uma conta
Gmail configurada como remetente no computador. Provedor proposto: Supabase Auth,
com código numérico de uso único por e-mail. Não é necessário hospedar um servidor
próprio de aplicação; o projeto de autenticação e o envio precisam ser configurados.

Usuário, senha local, PIN e dados comerciais não são enviados ao Supabase. O serviço
recebe o e-mail e os dados técnicos normais de uma solicitação de autenticação.
A comprovação online fica vinculada ao identificador do usuário no provedor, ao
e-mail confirmado e ao projeto configurado. Validar apenas o texto de um e-mail
ou uma resposta simulada não autoriza recuperar a conta.

Alternativa considerada: SMTP direto no computador. Exigiria configurar/proteger
uma credencial de envio em cada instalação. Não é o caminho selecionado.

### Configuração e envio real

- Projeto Supabase com autenticação por e-mail/OTP habilitada e template contendo
  `{{ .Token }}`. Expiração do código configurada em600 segundos.
- Endereço HTTPS do projeto e chave pública/publishable configurados localmente.
  Nunca distribuir service_role, chave secreta ou senha SMTP no ZIP/SQLite/logs.
- SMTP transacional/remetente autorizado configurado no painel do provedor para
  uso real. O serviço SMTP padrão do Supabase limita destinatários a membros da
  equipe e se destina a testes; não prometer envio para qualquer endereço sem isso.
- A escolha/contratação do remetente respeita disponibilidade, limites e preços
  do serviço. Nenhuma assinatura, domínio ou projeto externo foi criado nesta etapa.
- As configurações são validadas antes de iniciar o cadastro. Configuração ausente
  mostra orientação e mantém o cadastro atual intacto; não libera login por isso.
- A entrega somente poderá ser declarada operacional após um código chegar a um
  endereço autorizado e a recuperação real concluir no computador do operador.

Fontes oficiais consultadas pelo repositório do Supabase:
https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/auth-email-passwordless.mdx
https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/auth-smtp.mdx

## Fluxos

### Instalação existente: refazer cadastro mantendo os dados

1. Na entrada, oferecer Refazer cadastro para conta ainda sem e-mail confirmado.
   Isso não apaga nem desbloqueia o cadastro atual por si só.
2. Pedir novo usuário, senha com confirmação e e-mail. Confirmar esse endereço
   mediante código enviado pelo serviço. Manter entradas em caso de erro.
3. Antes de concluir, solicitar o PIN administrativo que já está cadastrado.
   Validá-lo no próprio computador, com a política atual de tentativas/espera.
   Não presumir que um PIN fornecido em conversa está correto.
4. Criar e verificar um backup do banco antes de alterar credenciais. Efetuar a
   validação fresca do PIN após operações demoradas para respeitar a validade da
   autorização administrativa. Backup ou PIN inválidos impedem a conclusão.
5. Em uma transação, substituir usuário/hash da senha na mesma conta, registrar o
   vínculo do e-mail verificado, incrementar revisão, limpar espera do login e
   registrar auditoria. Não substituir o banco nem recriar a conta comercial.
6. Invalidar sessões e autorizações anteriores somente após a gravação concluída.
   Voltar ao login com o novo usuário preenchido e senha vazia. Entrar normalmente.

Não pedir novo PIN neste recadastro: manter o PIN atual e todas as proteções
administrativas. Se o PIN atual também não funcionar, parar sem mudar os dados e
tratar a recuperação assistida separadamente; não criar um atalho público para
apagar credenciais. Depois de vinculado o e-mail, o recadastro excepcional não
permanece disponível na tela bloqueada como alternativa para contornar o e-mail.

### Instalação nova

Cadastro em etapas para caber na janela: usuário/senha, e-mail/código e PIN de
três dígitos com confirmação. Criar conta e PIN apenas após confirmação válida;
falha/cancelamento não deixa conta parcialmente utilizável. A chave administrativa
legada não é o método de recuperação de usuário/senha apresentado ao operador.

### Esqueci usuário ou senha

1. Na entrada, Recuperar acesso solicita o e-mail cadastrado. Não exige nome de
   usuário, senha antiga, PIN ou chave antiga para recuperar usuário/senha.
2. Enviar código ao endereço vinculado; não criar outro usuário no provedor.
3. Validar código online, confirmação do endereço e o mesmo identificador/projeto
   já vinculado à conta local. Código de outro e-mail/projeto não é aceito.
4. Permitir escolher novo usuário e nova senha com confirmação. Gravar de forma
   atômica, incrementar revisão, limpar espera e invalidar sessões anteriores.
5. Voltar ao login com o novo nome preenchido e sem senha armazenada na interface.

O PIN administrativo é preservado. Recuperar/trocar PIN via e-mail e trocar um
e-mail já vinculado são evoluções separadas, fora desta entrega. Os serviços de
recuperação legados permanecem compatíveis com backups/testes existentes, mas a
interface normal de recuperação de usuário/senha passa a usar e-mail.

## Dados e compatibilidade

- Manter o diretório atual `~/SalvaAiHeadshopV2`; não usar a pasta vazia criada para
  o teste do pacote0.2. Não mesclar bancos automaticamente nem abrir dados novos
  com código antigo. A opção --data-dir continua explícita quando utilizada.
- Migração017 aditiva: vínculo do e-mail confirmado (endereço normalizado,
  identificador do provedor, projeto/issuer, instante da confirmação) na conta.
  Contas antigas recebem vínculo ausente, sem alterar senha/PIN/identificadores.
- Registrar tentativas de envio/verificação e espera com relógio monotônico em
  relação ao último instante persistido; reiniciar não remove limites locais.
- Login/PIN continuam locais com hashes e esperas existentes. PIN não vira número
  inteiro; senha preserva espaços. Reutilizar normalização/validação do usuário.
- Backups antigos continuam exigindo migração e novo login. Ao restaurar, invalidar
  provas de e-mail em memória, sessões e autorizações; usar o vínculo presente no
  backup, sem transportar silenciosamente o vínculo de outro estado do banco.
- Não alterar regras de estoque, dinheiro, delivery, pagamentos, promoções ou IDs.

## Segurança e falhas

A prova de e-mail é opaca, curta e de uso único; fica apenas em memória, vinculada
a ação, desafio, conta/revisão, e-mail, identidade no provedor e projeto. A prova
expira no máximo600 segundos depois de verificada e é conferida novamente no
commit. Strings/JSON de interface não constituem autorização. Consumir prova
somente no commit bem-sucedido; falha SQLite mantém credenciais anteriores.
Se o OTP remoto já foi consumido e a prova local foi perdida por reinício, pedir
outro código; não relaxar a verificação para compensar a falha.

Reenvio com espera mínima60 segundos; máximo5 erros por desafio, depois exigir
novo código respeitando a espera. Expiração/uso único e limites também precisam
ser aplicados pelo serviço online. Limites do provedor podem ser mais restritivos;
respeitá-los e informar a espera em português, sem reenviar em laço.

Rede via HTTPS/TLS validado, timeout10 segundos, resposta limitada e sem encaminhar
credenciais para outro host por redirecionamento. Nunca usar confirmação local
fictícia ou modo de desenvolvimento como fallback de falha na rede. Rejeitar
resposta sem e-mail confirmado, sessão válida ou identificador esperado. Provas e
respostas de uma operação abandonada não podem alterar um cadastro posterior.

Chamadas de rede fora da thread Tk, resultados aplicados na thread principal.
Bloquear clique duplicado e ignorar callbacks após fechar/trocar de tela. Erros
preservam campos e explicam a ação possível; códigos, senhas, PINs, tokens e chaves
não vão para auditoria, relatórios ou mensagens de debug.

O banco local continua sem criptografia. Essa evolução oferece comprovação por
PIN/e-mail na aplicação, sem alegar proteção contra edição direta do arquivo por
quem controla o computador. Não incluir dados reais em fixtures/ZIPs.

## Interface

Assistente curto de cadastro/recadastro e recuperação em etapas; manter fonte,
cores e identidades atuais. Labels claros para e-mail cadastrado, código, reenviar
e espera. O endereço digitado é visível antes do envio. Login usual não precisa
consultar o serviço online. Não concentrar todos os campos em um formulário alto.
Inspeção nativa agrupada em1260×680 e1366×768, com no máximo uma confirmação após
correções. Windows100%/125% precisa de ensaio nativo, sem inferir pelo Xvfb.

## Verificação e critérios de aceite

- Banco0.3.2 populado mantém produtos, saldos, estoque, vendas e IDs após migração
  e recadastro autorizado; PIN anterior permanece válido.
- PIN errado, e-mail não confirmado, código expirado/reutilizado/outro projeto,
  resposta forjada e revisão alterada não mudam a conta nem liberam atendimento.
- Erro de disco/backup/rede mantém o acesso anterior e permite tentar de novo.
- Esperas sobrevivem a reinício/relógio atrasado; limites remotos são respeitados.
- Confirmar novo e-mail não permite sobrescrever uma conta já vinculada a outro.
- Recuperar usuário/senha não depende da chave antiga nem altera PIN/dados comerciais.
- Sessões/provas antigas deixam de funcionar após recuperação ou restauração.
- Login, venda, comanda e delivery funcionam offline após cadastro concluído.
- Testes de adapter com transporte controlado e JSON adverso, integração real de
  banco/UI e suíte atual completa. Código enviado/recebido de verdade é uma etapa
  separada de aceite; simulação não comprova entrega de e-mail.
- ZIP novo preserva os anteriores, código/assets/configuração pública corretos,
  manifesto e download conferidos; sem segredos ou bancos. Não declarar envio
  operacional sem configurar o projeto/remetente e executar o teste real.

## Fora do escopo e próxima etapa

Sem múltiplos operadores, sincronização de vendas, armazenamento comercial na
nuvem, reset silencioso do banco, compra de serviços ou envio de e-mail nesta etapa.
Após revisão desta especificação, escrever o plano de implementação e definir a
configuração do projeto de autenticação. Não iniciar código de produto antes disso.
