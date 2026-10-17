# Bar Simples

## Aplicação offline em validação

A nova aplicação está em `salva_ai_v2/`, com **banco vazio e separado do legado**.
Inclui atendimento, comandas, promoções por quantidade, estoque com custo médio,
caixa, financeiro auditável, delivery/acertos, resultados e backups.

- **Iniciar:** `python3 -m salva_ai_v2`; no Windows, `INICIAR_V2.bat`.
- **Ensaio isolado:** `python3 -m scripts.demo_v2`.
- **Gerar ZIP:** `python3 -m scripts.build_v2`.
- **Evolução de interface e delivery:** [plano aprovado](docs/superpowers/plans/2026-10-16-interface-atendimento-delivery.md).
- **Validação atual:** [relatório Bar Simples](docs/validacao-bar-simples.md).
- **Acesso:** conta do estabelecimento, senha e PIN de três dígitos, com transição do PIN antigo.
- **Documentação:** [manual da nova aplicação](docs/manual-v2.md).
- **Desenho e tarefas:** [plano geral](docs/superpowers/plans/2026-10-16-salva-ai-plano-geral.md).
- **Testes novos:** `python3 -m unittest discover -s tests_v2 -t . -v` com display;
  no Linux sem monitor, usar Xvfb conforme o manual.

Requer Python 3.12 ou superior com Tkinter. A versão `0.3.0-dev` identifica a
reconstrução, ainda pendente de validação no Windows e ensaio com o operador.
Não use o banco do estabelecimento para testes. Não foi feita release nem merge.

## Referência: aplicativo anterior

As instruções abaixo se referem ao código anterior em `salva_ai_headshop/`.

Sistema **offline** de vendas, estoque e gestão financeira para uma headshop: comandas por cliente, venda direta, controle de caixa com backup automático, despesas, taxas de maquininha, provisão de DAS MEI, lucro estimado por produto e exportação para Excel.

Aplicativo desktop em **Python 3 + Tkinter + SQLite**. Usa só a biblioteca padrão do Python; a única dependência externa, o [XlsxWriter](https://github.com/jmcnamara/XlsxWriter), já vem dentro da pasta. Não precisa de internet, servidor nem `pip install`.

> **Protótipo beta (0.3.4-beta).** Teste com dados fictícios. Os resultados são **estimativas gerenciais**, não apuração contábil ou fiscal. Leia [`COMECE_AQUI.txt`](salva_ai_headshop/COMECE_AQUI.txt) antes de usar com dados reais.

## Funcionalidades

| Aba | O que faz |
| --- | --- |
| **Comandas** | Abre uma comanda por nome do cliente. Os itens ficam *reservados* no estoque até o pagamento. Fecha a comanda em Dinheiro, Pix, Débito ou Crédito. |
| **Venda direta** | Vende um produto por operação e baixa o estoque na hora. |
| **Produtos e estoque** | Cadastro, preço, custo, estoque mínimo e entradas por caixa/fardo (convertidas em unidades) ou por unidade, além de perdas e ajustes. |
| **Caixa** | Abertura com troco inicial, totais por forma de pagamento, dinheiro esperado e fechamento com **backup automático** do banco. |
| **Histórico** | Últimas vendas e movimentos de estoque, exportação para Excel e reabertura de uma comanda paga por engano (só com o caixa original aberto). |
| **Financeiro mensal** | Despesas com data do gasto, vencimento e pagamento, mais o resumo do mês (vendas − CMV − taxas − despesas − DAS). |
| **Lucro por produto** | Margem de contribuição e lucro estimado após rateio de despesas e DAS pelo faturamento. Também configura as taxas e o DAS. |
| **Previsão de compras** | Sugere reposição em caixas/fardos inteiros a partir do estoque mínimo. |

## Como rodar

### Windows (usuário final)

1. Baixe o zip da versão e extraia **tudo** em uma pasta nova.
2. Abra a pasta `salva_ai_headshop` e execute **`INICIAR.bat`**.

É preciso ter o Python 3 instalado (o instalador do [python.org](https://www.python.org/downloads/) já inclui o Tkinter). O passo a passo completo está em [`COMECE_AQUI.txt`](salva_ai_headshop/COMECE_AQUI.txt).

### macOS / Linux (desenvolvimento)

```bash
git clone https://github.com/renanfreire7-code/salva-ai-.git
cd salva-ai-
python3 salva_ai_headshop/app.py
```

Para experimentar sem tocar nos seus dados, abra com dados fictícios em uma pasta temporária:

```bash
python3 scripts/demo.py
```

Se aparecer `No module named '_tkinter'`, seu Python não tem Tk:

- **macOS (Homebrew):** `brew install python-tk@3.14` (troque pela sua versão do Python). Não use o `/usr/bin/python3` da Apple: o Tk 8.5 dele fecha o app no macOS 15.
- **Debian/Ubuntu:** `sudo apt install python3-tk`

## Onde ficam os dados

| O quê | Caminho |
| --- | --- |
| Banco de dados (SQLite) | `~/SalvaAiHeadshop/dados/bar.sqlite3` (no Windows, `%USERPROFILE%\SalvaAiHeadshop\...`) |
| Backups de fechamento de caixa | `~/SalvaAiHeadshop/backups/salva_ai_backup_caixa_<n>_<data>.sqlite3` |
| Backup antes de atualizar o banco | `~/SalvaAiHeadshop/backups/antes_atualizacao_034_<data>.sqlite3` |

Para restaurar um backup, feche o app e rode `RESTAURAR_BACKUP.bat` (ou `python3 salva_ai_headshop/restaurar_backup.py`). O restaurador valida o arquivo e guarda uma cópia do banco atual antes de substituir.

## Estrutura do código

```
salva_ai_headshop/        # pasta distribuída no zip (scripts soltos, sem pacote)
├── app.py                # interface Tkinter: abas, estilos, ações dos botões
├── core.py               # Store: produtos, comandas, vendas, caixa, estoque (SQLite)
├── finance.py            # migrações de esquema, despesas, taxas, DAS, lucro, reposição
├── reports.py            # exportação .xlsx
├── restaurar_backup.py   # assistente de restauração de backup
├── xlsxwriter/           # biblioteca XlsxWriter incluída (BSD-2-Clause)
├── INICIAR.bat / RESTAURAR_BACKUP.bat
└── COMECE_AQUI.txt / LEIA-ME.txt / VERSAO.txt
tests/                    # testes automatizados (unittest)
scripts/
├── demo.py               # abre o app com dados fictícios
└── build_zip.py          # gera o zip de distribuição em dist/
```

Convenções que valem para todo o código:

- **Dinheiro em centavos** (`int`). `parse_money('1.234,56') == 123456` e `money(123456) == 'R$ 1.234,56'`.
- **Taxas em pontos-base** (1 bp = 0,01%). `parse_percent('3,5') == 350`.
- **Histórico não é recalculado.** A taxa e o custo são gravados na venda (`payment_fee`, `payment_rate_bp`, `cost_at_sale`), então mudar a configuração só afeta vendas novas.
- **Erros de regra de negócio** levantam `BusinessError` com mensagem em português. A interface mostra essa mensagem ao usuário.
- **Migrações** ficam em `finance.migrate()`: são idempotentes e só adicionam tabelas e colunas. Antes de migrar um banco antigo com dados, `backup_before_upgrade()` tira uma cópia consistente.

## Testes

```bash
python3 -m unittest discover -s tests -t .
```

Os testes cobrem dinheiro e taxas, reserva de estoque, caixa e backup, resumo mensal, rateio de lucro, reabertura de comanda e um teste de fumaça da interface. Os testes de interface são pulados automaticamente se o Python não tiver Tkinter ou se não houver display.

## Gerar o zip de distribuição

```bash
python3 scripts/build_zip.py
# -> dist/salva_ai_headshop_prototipo_0_3_4_beta.zip
```

A versão vem de `VERSAO.txt`. O zip tem o mesmo layout das versões anteriores (pasta `salva_ai_headshop/` completa). Anexe o arquivo a uma [Release do GitHub](https://docs.github.com/pt/repositories/releasing-projects-on-github/managing-releases-in-a-repository) em vez de versioná-lo no repositório.

## Limitações conhecidas

- Não emite nota fiscal nem faz apuração tributária. O DAS é uma provisão configurada manualmente.
- Não concilia recebimentos de Pix/cartão com o banco.
- O rateio de despesas por faturamento é uma convenção gerencial.
- A aba "Lucro por produto" do Excel usa o mês corrente do computador.
- Em telas com menos de ~900 px de altura, a aba Histórico não mostra todas as linhas da tabela de estoque sem rolar.
