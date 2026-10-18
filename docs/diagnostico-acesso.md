# Diagnóstico local de acesso

Esta ferramenta investiga “Chave de recuperação inválida”. Não redefine o acesso,
não restaura backups e não altera o programa, as credenciais ou os dados comerciais.
Não envia informações pela internet. A recuperação por e-mail não foi implementada.

1. Feche o Bar Simples/Salva AI e extraia todo o ZIP do diagnóstico em uma pasta.
2. Execute DIAGNOSTICAR_ACESSO.bat. Usa o Python já instalado no computador.
3. Cole a chave apenas no terminal local e pressione Enter. Ela não aparece enquanto
   você digita/cola; isso é esperado para proteger a chave.
4. Envie somente RELATORIO_ACESSO.txt (criado ao lado do BAT), ou uma imagem do
   resultado. O relatório não inclui chave, senha, PIN, hashes, nome de usuário ou vendas.

O diagnóstico examina o banco padrão ~/SalvaAiHeadshopV2/dados/salva_ai.sqlite3
em modo somente leitura. Se a chave não corresponder, verifica também até20 backups
mais recentes da pasta backups. Não restaure uma cópia por conta deste resultado:
uma restauração também troca os registros comerciais pelo estado do backup.

Valores do relatório: EXACT = corresponde ao banco padrão; OUTER_WHITESPACE =
corresponde sem espaços nas extremidades; INNER_WHITESPACE = corresponde sem
quebras/espaços inseridos na cópia; NO_MATCH = não corresponde à credencial atual;
MISSING = banco padrão não encontrado; OTHER_DATABASE = outro formato de banco;
NO_CREDENTIALS = acesso ainda não configurado; READ_ERROR = leitura não concluída.
backup_matches informa quantos backups examinados correspondem à chave. Nenhum
resultado revela a chave atualmente válida nem permite entrar sem comprovar acesso.

O diagnóstico não determina sozinho qual pasta uma abertura personalizada do programa
está usando. Para esse caso, a opção --data-dir permite indicar a pasta de dados
explicitamente. Não faça cópias de dados reais para o checkout do projeto.

Verificação: quatro testes com credenciais fictícias cobrem cópia com espaços,
chave anterior em backup após recuperação, banco ausente/outro formato/arquivo
inválido e ausência de segredos no relatório. Comparam bytes antes/depois para
verificar que o diagnóstico não modifica os bancos. Windows nativo permanece
pendente de ensaio; a lógica foi verificada com SQLite/Python no Linux.
