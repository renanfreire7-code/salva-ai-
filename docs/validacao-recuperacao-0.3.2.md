# Recuperação de usuário e senha — 0.3.2-dev

Solicitação: recuperar o acesso quando o usuário e a senha foram esquecidos ou
cadastrados incorretamente, mediante a chave de recuperação válida.

A tela Recuperar acesso agora pede chave, novo usuário, nova senha com confirmação
e PIN de três dígitos com confirmação. Não pede as credenciais antigas. Ao concluir,
mostra uma nova chave (a anterior deixa de valer) e volta ao login com o novo usuário
preenchido; a senha permanece vazia. A autenticação continua obrigatória para operar.

O nome é normalizado como no cadastro, sem remover espaços da senha. Usuário,
senha, PIN e chave são gravados em uma transação, com incremento da revisão da conta,
limpeza da espera e invalidação das sessões anteriores. Falhas na gravação desfazem
a troca das credenciais; a chave válida anterior continua utilizável. Dados comerciais
e pasta de dados permanecem intactos, sem migração ou recriação do banco.

O serviço mantém compatibilidade com chamadas antigas que não redefinem o usuário;
a interface de recuperação exige escolher o novo nome. O registro de auditoria
informa a redefinição sem incluir senha, PIN ou chave em texto puro.

Quatro regressões escritas antes da alteração comprovaram a ausência do parâmetro
no serviço e do campo na interface. Após corrigir, passaram25/25 testes direcionados:
chave inválida, nome inválido, rollback por erro SQLite, preservação de produtos,
invalidação de sessão/chave anterior, senha com espaços, fluxo Tk e geometria.
O teste de distribuição extrai o ZIP em caminho acentuado, recupera também o nome
e autentica com as novas credenciais.

Inspeção visual única da recuperação com erro e campos preenchidos em1260×680
sob Tk/Linux/Xvfb1366×768: todos os campos, aviso e botões ficaram visíveis.
Validação nativa Windows100%/125% e aceite pelo operador continuam pendentes.

Verificação final:206/206 testes de tests_v2 passaram, sem falhas ou skips.
Manifesto dos158 arquivos conferido; código e manual do ZIP idênticos ao checkout.
Arquivo: `dist/Bar_Simples_0.3.2-dev.zip`.
SHA-256: `cd735e50ed9deec4f08a46c8a50a7e1022653c52961bc6e0d8a41dba94fbbceb`.
Download: https://github.com/renanfreire7-code/salva-ai-/raw/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.3.2-dev.zip
