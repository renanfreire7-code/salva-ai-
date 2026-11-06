# Estoque inicial — validação 0.4.4-dev

Edição 05/11/2026. Base anterior: 1dd7445, implementação: 18155a9.

## Comportamento

- Produtos novos podem receber quantidade inicial e custo por unidade no cadastro; ambos zero mantêm cadastro sem saldo.
- Produtos já cadastrados e ainda sem movimentação podem usar Estoque inicial sem recadastro.
- Quantidade e custo positivos; centavos inteiros. Limite de valor SQLite validado antes da gravação.
- Entrada única INITIAL_STOCK, com PIN stock.adjust e auditoria. Transação inclui cadastro e saldo; falha não deixa produto parcial. Repetição da mesma chave é idempotente.
- Produto inativo, movimentado, com saldo ou reserva não recebe outra abertura.
- Não cria compra, despesa, obrigação ou movimento de caixa.
- Valor inicial registrado permanece após vendas; valor atual segue saldos. Totais incluem inativos.
- Custo entra no CMV das vendas e na média ponderada das próximas compras.

## Evidências

RED: métodos de serviço ausentes; botão/campos de interface ausentes. GREEN: 12 testes novos de serviço/interface, incluindo erro de custo, atomicidade, autorização, cancelamento, reexecução, saldo, CMV, média ponderada, totais e layout.

Um teste cria um banco com o pacote real 0.4.3-dev, com PIN, produtos, compra, obrigação e caixa. Após abrir com 0.4.4, compara todos os registros de todas as tabelas com o snapshot anterior: iguais. Em seguida inicializa somente o produto sem movimentos e confirma preservação do caixa e da obrigação prévia.

- Suíte atual completa: **270/270**, 192,951 s, sem skips ou expected failures.
- Legado: **30/30**, 0,600 s.
- Revisão independente: nenhum achado acionável. Revisor confirmou cancelamento de PIN e quantidade de 100 dígitos sem criar produto, além de formulário 414×566 e Salvar visível em 1366×768.
- Três capturas novas reais com dados fictícios em pasta temporária; imagem principal e formulário conferidos visualmente.
- PDF de instalação: 15 páginas. Uso: 65 páginas, 59 tópicos. Todos os títulos/passos/notas conferidos, sem texto fora da página e links internos com destinos válidos. Novas páginas inspecionadas visualmente.
- Manifestos de programa/kit e ZIPs íntegros. Kit sem bancos, caches ou dados de demonstração.
- Kit extraído em caminho com espaços/acentos: entrada .pyw real abre e fecha; entrada inicial 24×450=10800 sem financeiro, venda de 3 com CMV1350 e valor atual9450; fechamento libera recursos.

Comandos na raiz:

```sh
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t . -v
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a python3 -m unittest discover -s tests -t . -v
python3 scripts/build_v2.py
python3 scripts/build_manuals.py
```

## Pacotes

`Bar_Simples_0.4.4-dev_sem_login.zip`: SHA256 `65e6919f3348dbdd21135bab4d3db096b811c8ff5ac6f3e1b2ec5792ee5e0062`.

`Kit_Instalacao_Bar_Simples_0.4.4.zip`: SHA256 `e9609b5ff1c5c1a34a0b4e9d648915a6c805b32a226be4ff75c5572cdf8d465d`.

O kit contém os mesmos arquivos do ZIP, dois PDFs, COMECE_AQUI.txt e ESTOQUE_INICIAL.txt. Os manifestos permitem conferir os conteúdos. Os pacotes antigos foram preservados. Instruções de atualização em docs/atualizacao-estoque-inicial.md.

Nenhuma migração, dependência nova ou acesso ao banco real do proprietário. Testes em Linux/Xvfb; Windows nativo/DPI e comportamento real do atalho continuam dependendo da conferência no notebook. Entrega na feature branch, sem merge/main/release.
