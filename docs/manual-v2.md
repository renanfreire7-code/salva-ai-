# Salva AI novo — manual em desenvolvimento

Esta reconstrução está em desenvolvimento e ainda não é uma versão para operar a loja.

## Dados separados

O novo aplicativo usa `~/SalvaAiHeadshopV2/dados/salva_ai.sqlite3`.
Ele não abre nem importa o banco antigo em `~/SalvaAiHeadshop`.
Nunca copie o banco antigo para esse diretório.

Executar: `python -m salva_ai_v2`. No Windows: `py -3 -m salva_ai_v2`.
Para ensaios: `python -m salva_ai_v2 --data-dir CAMINHO_TEMPORARIO`.
Python precisa incluir Tkinter; nenhum serviço de internet é necessário.

## PIN e recuperação

No primeiro uso crie um PIN de seis dígitos e guarde a chave de recuperação
fora do computador. O aplicativo não guarda o PIN nem a chave em texto puro.
A recuperação troca o PIN e emite uma nova chave; a antiga deixa de funcionar.
O PIN protege ações pelo aplicativo e não criptografa o arquivo SQLite.

As funções de atendimento, financeiro, delivery e manutenção serão documentadas
junto de suas respectivas entregas e validações.

