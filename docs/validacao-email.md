# Validação — acesso por e-mail, 0.4.0-dev

Status: implementação em validação. **Envio real não ativado**: o operador ainda
não tem projeto Supabase. Nenhum e-mail foi enviado e nenhum código real foi aceito
nesta execução. A recuperação operacional no computador do usuário depende dessa
ativação e do ensaio real. Não substituir/apagar o banco para contornar o cadastro.

## Comportamento entregue

Entrada Bar Simples; operação SALVA AI HEADSHOP, com logo refinada e moto no delivery.
Login e operação offline. Cadastro novo confirma e-mail e cria conta/PIN; recadastro
excepcional de conta sem e-mail exige PIN atual e backup verificado, mantendo o PIN.
Recuperação por e-mail redefine usuário/senha e preserva o PIN. Vínculo inclui e-mail,
UID e projeto confirmado pelo endpoint autenticado do Supabase, sem confiar em
user_metadata. Códigos, tokens, senhas e segredos SMTP não são persistidos.

A atualização017 é aditiva e cria backup antes da migração. Dados continuam em
`~/SalvaAiHeadshopV2`, sem mudar para a pasta vazia da versão0.2 sem login.
Respostas tardias após cancelar/restaurar/fechar não geram confirmação aproveitável.
Uma falha local após OTP mantém credenciais anteriores e permite repetir a prova
válida no mesmo processo; depois de reiniciar exige outro código.

## Verificação reproduzível

No checkout, com Python3.12/Tk e Xvfb:

```bash
python3 -m unittest tests_v2.test_email_config tests_v2.test_email_provider
xvfb-run -a python3 -m unittest discover -s tests_v2 -t .
xvfb-run -a python3 -m unittest discover -s tests -t .
python3 -m scripts.build_v2
```

Testes usam somente identidades, produtos e transportes fictícios. O adapter real
fica distribuído sem modo de teste. O ZIP contém manifesto SHA256, configuração
pública vazia de exemplo, configurador e guia; não inclui banco, cache, testes,
configuração ativa, service_role ou segredo SMTP.

Verificações específicas: validação de respostas/autenticidade, limite de tamanho,
429, erro de rede, espera persistida e relógio atrasado; prova opaca e consumo
atômico; erro SQLite/backup/PIN, sessões antigas; runner separado do Tk/SQLite;
conta antiga offline; operações comerciais após recadastro/recuperação e restore.

Inspeção visual agrupada SETUP/TRANSITION/ENROLL/RECOVER, com erro e reenvio,
em1260×680 e1366×768 sob Xvfb: controles sem corte. Nenhum redesenho cosmético
adicional. [Capturas](validacao-email/entrada-xvfb.png).

A suíte extraída recebe os testes por fora do artefato e exclui apenas
`test_distribution` (empacotador não distribuído) e `test_access_diagnostic`
(ferramenta separada). Ambos permanecem na suíte completa do checkout.

Resultados: suíte principal241/241 (283.071s), integração2/2 (11.988s),
legado30/30 (1.631s), pacote extraído236/236 (259.966s), distribuição2/2.
Sem skips/expected failures. Um dos testes integrados foi acrescentado durante a
execução da suíte principal e foi confirmado pelo alvo integrado e pela suíte
extraída atualizada. São242 testes descobertos no checkout atual, todos cobertos
pela combinação dessas execuções; não se afirma uma execução única de242.
Manifesto de170 arquivos, fontes/manual/guia idênticos ao checkout.
Confirmação visual adicional das operações existentes, sem alteração cosmética:
[delivery e balcão](validacao-email/operacao-xvfb.png).

## Decisões de execução

- Reusar checkout isolado da nuvem, conforme escolha anterior e orientação de
  onboarding. Custo se inadequado: isolamento depende do checkout fornecido.
- Helpers das skills não existem localmente; usar briefs/ledger/logs equivalentes
  fora do checkout. Custo: coordenação manual.
- Acrescentar verify_after aos desafios:429 deve limitar conferência além do
  reenvio. Custo: uma coluna interna aditiva, sem mudança na API externa.

## Pendências externas

Criar projeto no painel Supabase, habilitar Email/template com `{{ .Token }}`,
OTP de seis dígitos com expiração600s, configurar SMTP/remetente autorizado, salvar
somente URL/chave pública pelo configurador e confirmar recebimento no endereço do
operador. O remetente padrão limita destinatários a membros da equipe e não é uma
configuração de envio geral. Não compartilhar senhas/PIN/códigos/segredos no chat.

Windows nativo100%/125%, recebimento real e aceite do operador ainda pendentes.
Consulte [configuração](configuracao-email.md). Não houve merge, release ou mudança
na branch main; somente a branch de desenvolvimento e seu ZIP específico.

## Revisão independente

Revisor com contexto novo, gpt-6-astra, diff39a6927..0fd1f59: os cinco focos do
plano foram examinados. Nenhuma falha Critical/Important encontrada. A identidade
vem de /user autenticado, provas e credenciais compartilham transação, cancelamento
invalida callbacks, espera persiste e o login usual permanece local.

Minor adiado: erro SQLite dentro do callback assíncrono de envio/verificação pode
escapar sem liberar o estado ocupado do assistente. Os botões Confirmar/Reenviar
ficam desabilitados; Voltar continua disponível e as credenciais anteriores são
preservadas. O revisor reproduziu com trigger abortando a gravação VERIFIED. Uma
correção futura deve testar erro visível, busy limpo, ausência de prova e novo envio.
Não foi aplicado lote de correções: não houve achados Critical/Important.

Decisões sobre itens não julgados pelo revisor:

- Envio/template/SMTP/política remota: manter ativação externa pendente e exigir
  recebimento real antes do aceite. Custo se errado: códigos não entregues/incompatíveis.
- Windows/DPI/operador: manter ensaios pendentes, sem extrapolar Xvfb. Custo: defeitos
  específicos da plataforma podem permanecer.
- Suítes completas: conferir resultados concluídos sob responsabilidade do executor
  antes de entregar. Custo se errado: regressões despercebidas.
- Histórico anterior a39a6927: preservar trabalho anterior e testar regressões; a
  revisão desta evolução não reaudita todo o código histórico. Custo: defeitos
  preexistentes fora do escopo da revisão podem permanecer.


## Entrega verificada

Branch feat/salva-ai-v2 enviada sob autorização anterior, sem merge/main/release.
Download do ZIP retornou HTTP200 e SHA256 idêntico ao artefato local:
`b40f9822712b7cb5e94c1776c117aec5ac1541adafc2e4f8610dd3f84f7b568e`.
HEAD remoto conferido após push; nenhum ZIP anterior foi removido/substituído.

[Baixar0.4.0-dev](https://raw.githubusercontent.com/renanfreire7-code/salva-ai-/refs/heads/feat/salva-ai-v2/dist/Bar_Simples_0.4.0-dev.zip)

Próximo passo externo: criar conta/projeto Supabase e configurar o remetente pelo
guia. O recebimento real e o aceite no computador do operador continuam pendentes.
