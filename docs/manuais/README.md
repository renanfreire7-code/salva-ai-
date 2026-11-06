# Manuais Bar Simples

Documentação da versão **0.4.4-dev**, edição de **05/11/2026**. Abertura direta, sem login, com PIN para operações administrativas. A identidade das telas de operação continua SALVA AI HEADSHOP.

## PDFs prontos

- [Manual de instalação — 15 páginas](../../dist/Manual_Instalacao_Bar_Simples_0.4.4.pdf): Python, extração, pasta permanente, atalho com logo, primeira abertura, atualização, notebook novo sem dados de teste e solução de dificuldades.
- [Manual de uso — 65 páginas](../../dist/Manual_Uso_Bar_Simples_0.4.4.pdf): 59 tópicos com passos numerados, imagens, exemplos, conferências, glossário, sumário clicável e referências.

O guia de uso cobre produtos, estoque, promoções, atalhos, compras, devoluções, créditos de fornecedor, caixa, balcão, comandas, delivery, troco, cancelamento, reembolso, retorno de mercadorias, nova tentativa, fundo de troco, acerto com entregador, histórico, correções, despesas, pagamentos, recorrências, taxas, DAS, resultados, exportação Excel, previsão de compras, backups, restauração e PIN.

## Origem e limites

- Conteúdo conferido contra o código-base `18155a9353ad57fad2f4901806b1ead8e72a68ba`.
- `instalacao.json` e `uso.json` contêm o conteúdo; o campo `source` registra os arquivos consultados por tópico.
- `imagens/` contém 42 capturas reais, exclusivamente com dados fictícios em uma pasta isolada. Nenhum banco de demonstração integra os PDFs ou este diretório.
- Capturas feitas em Linux/Xvfb; bordas e fontes podem variar no Windows. As figuras de pastas, Python, extração e atalho são esquemas identificados, não capturas de um instalador do Windows.
- O atalho Windows e a abertura sem console ainda exigem confirmação no notebook Windows. Esta documentação não substitui esse teste.
- Desde a versão 0.4.3-dev, está corrigida a confirmação da restauração e a mensagem de falha após a reconstrução da interface. Preserve uma cópia antes de restaurar e reabra/confira os dados antes de atender.
- As capturas gerais são da versão 0.4.2-dev; as três imagens de estoque inicial são da versão 0.4.4-dev. A correção de restauração foi entregue na 0.4.3-dev. Os PDFs anteriores permanecem em `dist/` como histórico da versão anterior.
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
