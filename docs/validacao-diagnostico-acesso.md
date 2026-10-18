# Validação do diagnóstico de acesso

Ferramenta independente de suporte; o aplicativo continua na versão0.3.2-dev.
Não modifica credenciais nem implementa recuperação por e-mail. A causa do erro
no computador do usuário permanece pendente do relatório local.

Quatro testes escritos antes do módulo evidenciaram sua ausência. Após implementar,
passaram4/4 testes direcionados e210/210 testes de tests_v2, sem falhas ou skips.
Abertura do ZIP extraído com --help validada. Um ensaio interativo PTY com chave
fictícia confirmou entrada sem eco, resultado EXACT e ausência da chave no terminal
e no relatório. A lógica de diagnóstico foi testada no Linux; Windows nativo ainda
requer execução pelo usuário. Manifesto dos três arquivos do ZIP conferido.

SHA-256 de dist/Diagnostico_Acesso.zip: `4d55dad2fd29ebcc3be3ed9962ca9db276e9d506ea0fd54636f74e48bfcc86d7`.

A investigação real exige executar o BAT localmente e compartilhar somente
RELATORIO_ACESSO.txt. Não solicitar banco ou chave por chat. Os códigos distinguem
espaços na cópia, chave correspondente a backup e problemas de localização/leitura
do banco padrão; não inferir automaticamente que toda divergência é erro de digitação.
