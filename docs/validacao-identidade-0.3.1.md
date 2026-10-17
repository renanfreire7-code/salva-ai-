# Identidade da entrada e do estabelecimento — 0.3.1-dev

Solicitação: usar Bar Simples apenas na entrada e manter SALVA AI HEADSHOP
na operação, com a logo anterior refinada.

- Cadastro, login e recuperação: Bar Simples, logo tradicional e ícone do balcão.
- Após autenticar: SALVA AI HEADSHOP no título e cabeçalho, logo do estabelecimento
  no canto direito e no ícone da janela. Ao voltar ao login, a marca da entrada retorna.
- Logo do estabelecimento refinada a partir do PNG anterior por edição de imagem,
  mantendo personagem, composição, cores e lettering; original preservado.
- Moto do delivery mantida; exportações passam a sugerir SALVA_AI_HEADSHOP no nome.
- Sem alteração de banco, caminho dos dados, credenciais ou regras comerciais.

Regressão de identidade falhou com o título antigo após login; teste de distribuição
falhou com o nome do pacote anterior. Após corrigir, os20 testes direcionados de
marca, navegação, geometria, acesso e distribuição passaram. O teste do pacote
extrai o ZIP em caminho com espaços/acentos, cria a conta e confere a marca após login.

Inspeção visual única em Tk/Linux/Xvfb, janela1260×680 na tela1366×768:
entrada, balcão e delivery. Marca correta, cabeçalho legível, ações visíveis e
moto preservada. Sem nova rodada cosmética ou revisão delegada.
Windows nativo100%/125% e aceite do operador permanecem pendentes.

A mensagem antiga do rodapé após login, já registrada na validação0.3.0,
permanece como pequeno ajuste adiado; esta mudança trata somente da identidade.

Verificação final:202/202 testes da suíte tests_v2 aprovados, sem skips ou falhas.
Manifesto dos158 arquivos conferido; código e manual do ZIP idênticos ao checkout.
Arquivo: `dist/Bar_Simples_0.3.1-dev.zip`.
SHA-256: `ca2a0f1aaf1085f9726d5d20dde3128e2a9fd15809e9292773ad5c76dfdb315f`.
