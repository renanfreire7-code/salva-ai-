# Atalho Bar Simples sem console —0.4.2-dev

Escopo aprovado: criar atalho na Área de Trabalho com a logo Bar Simples, abrindo
diretamente o programa sem login e sem janela preta. Mantém Python instalado,
mesmos dados/PIN e marca SALVA AI HEADSHOP dentro do programa.

## Uso no Windows

1. Feche a versão anterior e extraia todo o ZIP numa pasta permanente, como
   `Documentos\Bar Simples`. Não execute arquivos de dentro do ZIP.
2. Abra `CRIAR_ATALHO.vbs` uma vez. A verificação oculta confirma Python3.12+,
   Tcl/Tk e pythonw.exe; não abre nem cadastra conta no programa.
3. Use o ícone **Bar Simples** criado na Área de Trabalho. Se mover a pasta,
   execute CRIAR_ATALHO de novo para atualizar o caminho do atalho.

`ABRIR_BAR_SIMPLES.vbs` também abre silenciosamente, sem depender da associação de
arquivos .pyw. `INICIAR_V2.bat` fica disponível com console para diagnóstico.
Não há instalação de dependências, alteração do registro, execução como administrador
ou alteração de política de scripts. O Windows precisa permitir Windows Script Host.

## Implementação e limites

O atalho .lnk é gravado na pasta Desktop retornada pelo Windows (inclui redirecionamento
OneDrive), com o ícone ICO multirresolução da logo já existente (16até256pixels).
Aponta para wscript.exe e o launcher da pasta extraída. WScript.Run oculto executa
a ponte Python; ela localiza pythonw.exe ao lado do intérprete real e abre
Bar_Simples.pyw. Não usa cmd.exe nem concatena caminhos para shell intermediário.
A lista de argumentos e cwd preservam caminhos com espaços e acentuação.

A entrada .pyw chama o mesmo build_application e fecha recursos ao sair. Mensagens
de início/instância já aberta são exibidas em janela nativa do Windows, sem console.
Registro de falha contém apenas data/tipo de exceção, sem mensagem ou dados sensíveis,
em `~/SalvaAiHeadshopV2/logs/inicializacao.log`, com rotação limitada. Não altera banco,
conta antiga, configuração de e-mail, PIN ou pasta dos dados.

Os arquivos VBS são ASCII. O código42 indica que a ponte já exibiu o erro; outros
códigos do launcher Python geram um aviso de instalação, evitando falhas silenciosas.

## Evidências

RED→GREEN: módulo desktop ausente e nova distribuição ausente;7testes de detecção do
pythonw, argumentos/flags/cwd, probe sem abertura, sucesso/fechamento, aviso de falha,
log sem conteúdo sensível e instância existente;14/14 com distribuição/acesso direto.
O teste de distribuição extrai em caminho acentuado com espaços, verifica manifesto,
ICO e launchers, e executa a entrada .pyw real com Tk e fechamento programado.
Não requer Pillow no computador do usuário: ele foi usado somente para converter a
logo existente em ICO durante o desenvolvimento.

Revisão independente estática dos scripts Windows, diretório Desktop, aspas, erros,
pythonw e empacotamento: nenhum bloqueio encontrado. Não houve teste de Windows nativo:
este ambiente tem Linux/Xvfb, sem Windows/Wine/PowerShell. Assim, ausência real de
console e criação do .lnk ainda precisam ser confirmadas no computador do operador.

Aceite Windows: pasta com espaços/acentos/&, Desktop OneDrive, Python/Tk/pythonw ausentes,
duas aberturas (aviso de instância), e atualizar atalho após mover a pasta. A pasta de
programa deve ser mantida depois da criação do atalho.

Suíte completa:254/254 (179.404s); legado:30/30 (0.577s), sem skips ou expected failures.
Manifesto, fontes, entrada .pyw/VBS, ícone e manual do ZIP conferidos.
SHA256: `89d81c83beebcc970755bfdcdd7f5c9e141a0a657022fa0254a54123fd515036`.

[Baixar0.4.2-dev com atalho](https://raw.githubusercontent.com/renanfreire7-code/salva-ai-/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.4.2-dev_sem_login.zip).
Entrega somente na branch feat/salva-ai-v2; não houve merge/main/release.
A confirmação real do atalho/ausência de console no Windows continua pendente.
