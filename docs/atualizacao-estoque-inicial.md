# Atualização 0.4.4 — estoque que o bar já tinha

## Atualizar o notebook instalado

1. Na versão atual, use Histórico de vendas → Auditoria e manutenção → Backups → Criar backup. Verifique a cópia e guarde outra fora do notebook.
2. Feche o Bar Simples. Extraia o kit 0.4.4 numa nova pasta permanente, por exemplo `Documentos\Bar Simples 0.4.4`.
3. Execute `CRIAR_ATALHO.vbs` nessa pasta. O atalho Bar Simples passa a abrir a versão nova.
4. Use o mesmo usuário do Windows. A pasta `SalvaAiHeadshopV2` continua com os dados; não a apague, não copie outro banco por cima e não precisa recadastrar produtos.
5. Abra pelo atalho e confira os cadastros, caixa e demais registros existentes.

## Produtos já cadastrados, ainda sem movimentos

Abra Produtos e estoque, selecione a linha e clique em **Estoque inicial**. Informe a quantidade existente em unidades e o custo de uma unidade. Clique em Salvar e confirme o PIN.

Exemplo: 24 Heineken com custo de R$ 4,50 cada → R$ 108,00 de estoque inicial. Se a caixa tem 12 e custou R$ 54,00, informe R$ 4,50 por unidade; duas caixas são 24 unidades.

Não há nova compra, despesa, obrigação ou saída da gaveta. A entrada é de mercadoria já paga. O custo passa a compor as vendas futuras.

## Próximos cadastros

Em Novo produto, preencha **Quantidade inicial em unidades** e **Custo por unidade do estoque inicial** para fazer tudo no mesmo cadastro. Se não há mercadoria, deixe ambos em zero. Quantidade positiva exige custo positivo. A confirmação administrativa usa o PIN existente.

## Entender os valores

- **Valor em estoque**: custo do saldo atual de cada produto.
- **Inicial registrado**: soma das entradas iniciais; permanece após vendas.
- **Valor atual**: custo das mercadorias que ainda existem; muda com vendas, compras e ajustes.

Os totais incluem mercadorias de produtos desativados. Não são despesas do mês, saldo de caixa ou todo o gasto histórico.

Estoque inicial só pode ser registrado uma vez, em produto ativo ainda sem movimentos ou reservas. Se já houve entrada por compra, não repita o mesmo saldo. Reposições futuras seguem em Entrada / compra. Perdas e correções seguem em Ajustar estoque.

A atualização não altera o esquema nem instala dependências adicionais. O ZIP e o kit não incluem banco de dados. O teste de atualização usa uma cópia isolada criada com a versão 0.4.3; o banco real do bar nunca é acessado neste ambiente.
