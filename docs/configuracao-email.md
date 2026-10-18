# Configurar recuperação por e-mail

O atendimento/login habitual continuam offline. Cadastro/recadastro com e-mail e
recuperação precisam de internet, de um projeto Supabase configurado e de envio
real habilitado. A instalação não envia códigos antes dessa configuração.

1. No painel oficial https://supabase.com/dashboard, crie ou escolha um projeto.
2. Em Authentication, habilite Email e configure o template de acesso por e-mail
   para conter `{{ .Token }}`: esse é o código numérico, não apenas um link.
3. Configure Email OTP expiration em600 segundos. Preserve os limites de envio e
   verificação do provedor. O aplicativo também limita reenvios e tentativas.
4. Configure SMTP/remetente autorizado no painel do Supabase para uso real. O
   remetente padrão é restrito aos membros da equipe do projeto e serve a testes;
   não garante envio a qualquer e-mail cadastrado. Confira limites/custos do serviço.
5. Copie a URL HTTPS do projeto e a chave **publishable** (ou anon pública legada).
   Não use service_role, sb_secret, senha de conta ou senha SMTP no configurador.
6. Extraia o pacote e execute CONFIGURAR_EMAIL.bat. Informe apenas URL/chave pública.
   O arquivo auth_service.json será salvo em ~/SalvaAiHeadshopV2. Nenhum produto,
   venda, senha ou PIN é alterado por essa configuração.
7. No programa, confirme o recebimento real de um código no seu endereço e conclua
   o fluxo de confirmação. Testes simulados não comprovam envio real de e-mails.

Depois de vinculado um e-mail, o projeto não pode ser trocado silenciosamente:
o identificador desse projeto faz parte da comprovação de acesso. A configuração
pública não contém dados comerciais nem credenciais de envio. Guarde segredos do
remetente somente no painel do serviço. Nunca compartilhe códigos/PIN/senhas no chat.

Configuração ausente ou falha de rede não impede login com credenciais já cadastradas.
Não apague o banco para corrigir configuração. A recuperação por e-mail troca somente
usuário/senha; o PIN administrativo atual é mantido. Para redefinir o acesso de uma
conta antiga ainda sem e-mail, o programa exige também validar o PIN atual localmente.

Referências oficiais:
https://supabase.com/docs/guides/auth/auth-email-passwordless
https://supabase.com/docs/guides/auth/auth-smtp
