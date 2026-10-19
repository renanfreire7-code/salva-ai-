# Bar Simples0.4.1-dev — abertura direta

Pedido aprovado: manter as melhorias e os dados, retirar login/senha e redefinição
por e-mail, manter PIN apenas nas operações administrativas.

A execução pública `python -m salva_ai_v2`/INICIAR_V2.bat abre as11telas diretamente.
Não inicializa conta, serviço de e-mail, runner de rede nem tela de acesso. Ignora
configuração auth_service.json existente. Não cria senha, conta ou PIN automático.
O PIN anterior continua igual. Na instalação nova, pede criação/confirmação do PIN
apenas ao solicitar uma operação administrativa. O cancelamento não abre uma
operação protegida. Depois de restaurar, recompõe telas/serviços e descarta grants
anteriores; usa o PIN que estava no backup. Falha ao recompor fecha os recursos.

A pasta original `~/SalvaAiHeadshopV2` e as migrações já instaladas são preservadas.
Não apaga conta antiga ou vínculo antigo do banco: apenas deixa de usá-los no
entrypoint atual. A classe anterior CredentialApplication e seus testes continuam
isolados para compatibilidade histórica; não é a classe usada pelo entrypoint.
Os módulos antigos não são ativados pelo fluxo novo. O ZIP não oferece configurador,
guia ou exemplo de configuração SMTP/e-mail. As versões anteriores do ZIP permanecem.

Melhorias preservadas: busca por iniciais/palavras, nomes completos, Enter nos
formulários, atalhos, promoções, comandas, filtros/histórico, estoque/caixa, despesas,
relatórios, delivery com complemento/troco/pagamento antecipado e acerto detalhado.
Marca operacional SALVA AI HEADSHOP, logo refinada e moto continuam presentes.

Verificações específicas RED→GREEN: abertura nova sem conta/PIN/e-mail; arquivo de
configuração inválido ignorado; conta antiga bloqueada e PIN preservados; restore
sem login e grant anterior rejeitado; PIN solicitado somente na operação protegida;
pasta padrão igual; demo direta e pacote sem configurador de e-mail.
O ensaio integrado de atualização/balcão/comandas/promoção/delivery/troco/acerto/
fechamento/reinício/restore usa o entrypoint público novo, preservando PIN legado.
Testes históricos de acesso usam explicitamente a classe antiga e não substituem
os testes do entrypoint atual.

Comandos:

```sh
xvfb-run -a python3 -m unittest tests_v2.test_direct_access -v
xvfb-run -a python3 -m unittest discover -s tests_v2 -t .
xvfb-run -a python3 -m unittest discover -s tests -t .
python3 -m scripts.build_v2
```

Ensaios feitos sob Linux/Xvfb. Windows nativo e aceite no computador do operador
continuam pendentes; a validação automatizada não é um teste feito em seu computador.
Resultados:247/247 testes da suíte atual (164.027s) e30/30 do legado (0.529s), sem skips ou expected failures. Alvos específicos:18/18 de abertura/PIN/navegação/segurança,15/15 de integração/distribuição/marca/restore e1/1 de operação comercial completa.


Revisão independente do diff desta mudança: nenhum achado Critical/Important/Minor.
Confere a rota pública direta, preservação de banco/PIN, recomposição após restore,
invalidação de grants e distinção explícita entre testes atuais e históricos.
[Captura da abertura direta](validacao-sem-login/abertura.png).

Pacote extraído em caminho com espaços/acentos: conta bloqueada, produto original,
PIN correto e abertura das11telas confirmados em subprocesso fora do checkout.
Configuração antiga inválida não bloqueia; manifesto/arquivos/manual conferidos.
SHA256 do ZIP: `de38d4b4f9108620f38654d5dc024b3263895e35429341b0f60d858b8996e93a`.


[Baixar ZIP sem login](https://raw.githubusercontent.com/renanfreire7-code/salva-ai-/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.4.1-dev_sem_login.zip).
Alteração entregue somente na branch feat/salva-ai-v2; nenhum merge/main/release.
