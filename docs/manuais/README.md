# Manuais Bar Simples

Documentação da versão **0.4.2-dev**, edição de **19/10/2026**. Abertura direta, sem login, com PIN para operações administrativas. A identidade das telas de operação continua SALVA AI HEADSHOP.

## PDFs prontos

- [Manual de instalação — 15 páginas](../../dist/Manual_Instalacao_Bar_Simples_0.4.2.pdf): Python, extração, pasta permanente, atalho com logo, primeira abertura, atualização, notebook novo sem dados de teste e solução de dificuldades.
- [Manual de uso — 64 páginas](../../dist/Manual_Uso_Bar_Simples_0.4.2.pdf): 58 tópicos com passos numerados, imagens, exemplos, conferências, glossário, sumário clicável e referências.

O guia de uso cobre produtos, estoque, promoções, atalhos, compras, devoluções, créditos de fornecedor, caixa, balcão, comandas, delivery, troco, cancelamento, reembolso, retorno de mercadorias, nova tentativa, fundo de troco, acerto com entregador, histórico, correções, despesas, pagamentos, recorrências, taxas, DAS, resultados, exportação Excel, previsão de compras, backups, restauração e PIN.

## Origem e limites

- Conteúdo conferido contra o código-base `397acca183f7ecd8283c3fdad60d2d35548b141d`.
- `instalacao.json` e `uso.json` contêm o conteúdo; o campo `source` registra os arquivos consultados por tópico.
- `imagens/` contém 39 capturas reais, exclusivamente com dados fictícios em uma pasta isolada. Nenhum banco de demonstração integra os PDFs ou este diretório.
- Capturas feitas em Linux/Xvfb; bordas e fontes podem variar no Windows. As figuras de pastas, Python, extração e atalho são esquemas identificados, não capturas de um instalador do Windows.
- O atalho Windows e a abertura sem console ainda exigem confirmação no notebook Windows. Esta documentação não substitui esse teste.
- O guia registra o limite conhecido da mensagem final de restauração: os dados podem já ter sido substituídos quando a mensagem falha. Deve-se preservar uma cópia e reabrir/conferir o resultado antes de atender.
- Exemplos de diferentes páginas são independentes; não representam o fechamento de um único dia.
- A criação dos manuais não altera o aplicativo nem os dados do estabelecimento.

## Regenerar os PDFs

Dependências de autoria: Python 3, ReportLab, Pillow e fontes Noto Sans Regular/Bold/Italic em `/usr/share/fonts/truetype/noto`. Não são requisitos adicionais para o usuário do PDV. Nesta edição foram usados ReportLab 4.4.9 e Pillow 12.3.0; consulte as versões instaladas antes de reproduzir.

Na raiz do repositório:

```sh
python3 scripts/build_manuals.py
```

Saída: os dois PDFs em `dist/`. O script mantém os arquivos originais das imagens e cria apenas recortes temporários para a diagramação. As referências oficiais e o link do ZIP estão dentro dos PDFs. Os arquivos têm marcadores e links internos para consulta.

Conferência: verificar número de páginas, presença de todos os títulos e passos do JSON, links do sumário/referências, limites de texto, fontes e renderização visual. Não é necessário executar novamente testes do PDV para uma alteração apenas nestes documentos.
