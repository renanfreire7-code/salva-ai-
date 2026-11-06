# Estoque inicial já pago

O proprietário já tem mercadorias quando instala o PDV. Deve informar quantidade em unidades e custo unitário em reais no cadastro ou, para produtos já cadastrados e sem movimentos, em Estoque inicial. Não há compra, obrigação, despesa nem movimento de caixa; o custo compõe o estoque e o custo histórico das vendas futuras.

Alternativas consideradas: simular compra quitada criaria histórico financeiro artificial; liberar ajuste sem custo prejudicaria a lucratividade; entrada inicial explícita com quantidade e custo atende ao pedido. O usuário autorizou seguir considerando tudo já pago, dispensando nova rodada de perguntas.

Proposta de implementação: botão Estoque inicial para cadastro existente; campos opcionais Quantidade inicial e Custo por unidade em Novo produto, ambos zero quando não há saldo inicial. Valores positivos são obrigatórios ao informar estoque. Criação e saldo na mesma transação; PIN de ajuste quando houver saldo. A entrada inicial só pode ocorrer uma vez, antes de qualquer movimento/reserva, e exige produto ativo. Ajustes e compras seguintes mantêm suas regras.

Exibir valor atual por produto, total inicial registrado e total atual. O total inicial soma as entradas iniciais, mantendo-se após vendas; o atual reflete os saldos inclusive de produtos desativados. Identificar esses significados na tela. Usar centavos inteiros e multiplicação quantidade × custo, sem floats. Sem alteração de esquema ou dependências. Manter IDs, estoque existente, PIN e pasta de dados.

Entregar nova versão 0.4.4-dev, ZIP e kit sem dados, manuais atualizados e instruções de atualização sem exclusão de dados. Capturar as telas novas com dados fictícios. Testar abertura de cópia de banco 0.4.3 já populado sem alteração dos registros.
