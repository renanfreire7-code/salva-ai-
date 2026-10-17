# Bar Simples: Acesso e Identidade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a entrada offline do Bar Simples com uma conta por estabelecimento, senha e PIN de três dígitos, preservando instalações existentes.

**Architecture:** Primeiro migrar credenciais sem alterar o segredo antigo; depois implementar cadastro/transição/recuperação atômicos e a sessão em memória. Só construir as telas de operação depois da autenticação. A identidade usa a terceira proposta aprovada com PNGs locais.

**Tech Stack:** Python 3.12+, Tkinter/ttk, SQLite, hashlib/hmac/secrets, unittest; sem novas dependências de execução.

**Spec:** `docs/superpowers/specs/2026-10-17-bar-simples-acesso-atendimento-design.md`

## Global Constraints

- “PIN de exatamente três dígitos”; aceitar zeros iniciais, somente algarismos ASCII; sem PIN padrão.
- “senha com pelo menos oito caracteres, aceitando espaços e sem composição obrigatória”.
- “uma conta por estabelecimento”; sem perfis, serviços online ou senha mestre.
- “Na primeira atualização, exigir o PIN atual de seis dígitos (ou a chave de recuperação existente)”. Não truncar o PIN.
- “contagem de falhas e espera temporária após cinco erros consecutivos”; preservar autorizações de uso único e expiração.
- “Manter a pasta SalvaAiHeadshopV2”; migração aditiva com backup prévio, sem editar migrações existentes.
- “Nome visível Bar Simples, logo Tradicional em verde escuro e terracota”.
- “Controles e mensagens devem caber em 1366×768; Windows 100%/125% requer ensaio nativo”.
- Sem alterar main, merge ou release; trabalhar na branch isolada já usada. Não substituir ZIP atual.

## Review Focus

1. Senhas com espaços nas pontas/Unicode: cadastro e login preservam exatamente o segredo, sem strip silencioso (A2/A3).
2. Falha de escrita após trocar PIN durante a transição: rollback preserva senha/PIN/chave antigos e nenhum cadastro parcial (A2).
3. Relógio regressivo e reinício durante bloqueio: não contornar espera, inclusive em troca de usuário digitado (A2).
4. F1–F12, atalhos de menus e eventos antes de autenticar: não abrir caixa, expor catálogo ou acionar views ocultas (A3).
5. Restaurar backup com credenciais anteriores ou fechar a entrada: sessão anterior não desbloqueia dados restaurados, nenhum arquivo fica bloqueado (A3/A5).

---

## Estrutura e dependências

A1 → A2 → A3; A4 usa a superfície A3; A5 verifica o conjunto. Entregáveis de cada tarefa são testáveis independentemente. O segundo plano é `2026-10-17-bar-simples-atendimento.md`; as credenciais pertencem somente a este plano.

- `migrations/015_establishment_access.sql`: extensão do PIN e tabela de conta única.
- `security/service.py`: política do PIN, autenticação legada e autorizações existentes.
- `security/accounts.py`: conta, senha, transição, bloqueio de login e recuperação.
- `security/models.py`: `LoginSession` opaca, sem guardar senha/PIN.
- `ui/access.py`: formulários de cadastro/login/recuperação/transição.
- `ui/branding.py`, `assets/bar_simples_logo.png`, `assets/bar_simples_icon.png`: identidade compartilhada.
- `bootstrap.py`: ciclo entrada → operação; encerramento e restauração.
- `tests_v2/security_support.py`, `tests_v2/application_support.py`: fixtures explícitas para credencial antiga e aplicação autenticada; sem bypass de produção.

### Task A1: Migração e política do PIN

**Files:** Create `salva_ai_v2/migrations/015_establishment_access.sql`, `tests_v2/security_support.py`, `tests_v2/test_access_upgrade.py`; Modify `salva_ai_v2/security/service.py`, `salva_ai_v2/ui/dialogs.py`, `tests_v2/test_security.py` e fixtures de PIN em `tests_v2/`.

**Interfaces:** Preserve `SecurityService.authorize(pin, action) -> AdminGrant`, `validate`, `consume` e seus contratos. `setup(pin: str) -> str` e `recover(recovery_key: str, new_pin: str) -> str` passam a cadastrar PIN de três dígitos. `SecurityService.pin_length: int` informa3 para cadastro novo ou o comprimento da credencial atual; AdminDialog acompanha essa política já nesta tarefa. Autorização usa `admin_credentials.pin_length` para permitir seis apenas em credencial legada ainda não convertida. `seed_legacy_pin(db, pin='681942') -> str` é helper exclusivo de testes que cria o registro de hash no formato anterior.

- [ ] **Step 1: Escrever regressões.** `test_new_pin_requires_three_ascii_digits`: setup('007') funciona; '07', '0007', '１２３' falham. `test_previous_schema_migration_preserves_six_digit_hash_and_backup`: construir banco até014, seed antigo, upgrade; hash e IDs/saldos iguais, length6, autorizar681942 funciona,681 falha; backup verificado. `test_pin_grant_still_expires_and_is_consumed_once`: manter as assertivas existentes. Atualizar fixtures atuais para681; testes de legado usam o helper, nunca fazem setup novo com seis.
- [ ] **Step 2: RED.** `python3 -m unittest tests_v2.test_access_upgrade tests_v2.test_security -v`; falha esperada na ausência de pin_length/política nova, não erro de import do teste.
- [ ] **Step 3: Implementar.** Migração acrescenta `pin_length INTEGER NOT NULL DEFAULT 6 CHECK(pin_length IN (3,6))`. Tabela `establishment_account` com id único1, username normalizado, salts/hashes/iterations, failures, blocked_until, last_time e revision. Sem senha/PIN em auditoria. `_pin(pin, length=3)` valida ASCII. `authorize` valida usando o comprimento armazenado; setup/recover novos gravam3; prompts setup/recover indicam3 e request usa pin_length para instalações legadas. Fixtures anteriores com recuperação seis são substituídas por testes novos3, preservando cobertura de rotação/chave antiga recusada, não simplesmente removidas.
- [ ] **Step 4: GREEN.** Reexecutar comando alvo e suíte `python3 -m unittest discover -s tests_v2 -t .`; nenhum teste ignorado para acomodar a mudança. Corrigir consumidores de fixtures preservando suas assertivas financeiras.
- [ ] **Step 5: Commit.** `git diff --check`; adicionar arquivos específicos; `git commit -m 'feat: prepara acesso Bar Simples e PIN de tres digitos'`.

### Task A2: Conta e transição atômica

**Files:** Create `salva_ai_v2/security/accounts.py`, `tests_v2/test_accounts.py`; Modify `security/service.py`, `security/models.py`.

**Interfaces:**
- `LoginSession(id: str, revision: int)` dataclass imutável.
- `AccountService(db, security, clock=None)`; `.configured: bool`; `.mode: str` retorna SETUP/TRANSITION/LOGIN.
- `.create(username: str, password: str, pin: str, proof: AdminGrant | None = None) -> str` retorna chave nova; `.login(username: str, password: str) -> LoginSession`; `.validate_session(session) -> None`; `.logout() -> None`.
- `.recover(recovery_key: str, new_password: str, new_pin: str) -> str`; `.remaining_wait() -> int` para mensagem.
- `SecurityService.authorize_recovery(key: str, action: str) -> AdminGrant` permite prova legada alternativa; `replace_pin(pin: str, proof: AdminGrant, action: str) -> str` consome prova e renova chave. Ação da transição: `access.configure`. `SecurityService.remaining_wait() -> int` informa a espera do PIN sem expor segredos.

- [ ] **Step 1: Escrever testes.** `test_single_account_validates_username_password_pin_and_hashes_secrets`: username strip/casefold, vazio falha, senha7 falha,8 aceita, PIN007, segundo cadastro falha e nenhum segredo no dump/audit. `test_password_whitespace_and_unicode_roundtrip`: '  café 42 ' só funciona exatamente assim. `test_transition_requires_existing_pin_or_recovery_proof`: prova de outra ação/forjada/reutilizada falha; prova antiga correta conclui e PIN antigo deixa de valer. `test_transition_failure_rolls_back_credentials`: injetar sqlite error depois da troca do PIN; hashes, chave e modoTRANSITION preservados, conta inexistente. `test_five_failures_wait_survives_restart_and_clock_rollback`: falhas incluindo username inexistente compartilham contador; após quinta espera30s, reinício/retrocesso não libera; cinco erros isolados de login não substituem contador do PIN. `test_recovery_rotates_key_and_invalidates_session_and_grants`: chave anterior falha, senha/PIN novos funcionam, sessão e grants anteriores falham.
- [ ] **Step 2: RED.** `python3 -m unittest tests_v2.test_accounts -v`; falhas por contratos ausentes, com fixture A1 funcionando.
- [ ] **Step 3: Implementar APIs.** PBKDF2-HMAC-SHA256/salts próprios com custo existente600000; hmac.compare_digest. Username1–64 caracteres após strip/casefold; senha nunca strip. Transação externa única engloba criação/troca/rotação e auditoria; validar campos antes de consumir prova. Login segue espera existente: quinta falha30s, duplicação progressiva limitada900s, relógio max(now,last_time). Sessões só em memória, validadas por identidade no registro local + revision atual no banco; logout limpa registro/grants. Recuperação atualiza senha/PIN na mesma transação e renova chave; antes de existir conta, chave antiga só autoriza a transição pelo fluxo de configuração.
- [ ] **Step 4: GREEN.** `python3 -m unittest tests_v2.test_accounts tests_v2.test_access_upgrade tests_v2.test_security -v`; PASS, inclusive rollback e cópia do banco/reinício sem sessão persistida.
- [ ] **Step 5: Commit.** diff--check; `git commit -m 'feat: adiciona conta offline e transicao segura de acesso'` com arquivos específicos.

### Task A3: Entrada protegida e ciclo da aplicação

**Files:** Create `salva_ai_v2/ui/access.py`, `tests_v2/application_support.py`, `tests_v2/test_access_ui.py`; Modify `bootstrap.py`, `ui/dialogs.py`, `ui/keyboard.py`, `ui/audit.py`, `maintenance/restore.py`, `tests_v2/test_bootstrap.py` e fixtures de UI em `tests_v2/`.

**Interfaces:** `Application.accounts: AccountService`; `.authenticated: bool`; `.unlock(session: LoginSession) -> None` valida a sessão antes de construir views/router; `.require_login() -> None` remove operação/atalhos e monta entrada. `AccessView(parent, accounts, security, on_authenticated, on_cancel)` com `.submit() -> bool`, `.inputs: dict`, `.error: StringVar`, `.primary_button`. `RestoreService.on_completed: Callable[[], None] | None` é callback opcional registrado pela Application para require_login após restauração concluída; serviços sem UI continuam sem callback. Helper de teste `build_test_application(data_dir) -> Application` cria/loga com credenciais fictícias e chama unlock real, sem flags de bypass.

- [ ] **Step 1: Escrever testes Tk.** `test_login_setup_transition_recovery_and_show_password`: fluxos três modos, confirmação de senha/PIN, erro não perde usuário, segredo mantido exatamente, confirmação antes de gravar, chave só após commit. `test_enter_focuses_action_before_submitting`: nome→senha→botão, sem autenticar no último campo. `test_operational_views_and_shortcuts_absent_before_login`: `app.views == []`, catálogo/caixa não mapeados; F1 e tentativa unlock(None) não operam. `test_cancel_releases_database_and_instance_lock`: fechar entrada, reconstruir app na mesma pasta sem BusinessError. `test_restore_requires_new_login_for_restored_credentials`: restore invalida sessão, desmonta operação, credenciais do backup definem LOGIN ou TRANSITION. `test_fault_during_unlock_closes_resources`: falha de criação de view não deixa instância aberta.
- [ ] **Step 2: RED.** `PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a python3 -m unittest tests_v2.test_access_ui tests_v2.test_bootstrap -v`; falha em views expostas/ausência da entrada.
- [ ] **Step 3: Implementar.** Inicializar apenas lock/banco/upgrade/segurança/accounts/janela/entrada antes do login; extrair montagem operacional de `_initialize` para unlock sem montar duas vezes. Recuperação de fechamento automática só depois do acesso. Campos de senha próprios preservam espaços; PIN não chama int(). Usar callbacks e erros inline, confirmações separadas, grab/foco sem callbacks pendentes. AdminDialog usa3, transição pergunta comprimento legado6. Restauração final chama on_completed/require_login e encerra callbacks/views antigos antes de reabrir operação. Atualizar testes existentes para helper autenticado; testes de entrada continuam build_application real. Fechamento idempotente mesmo na montagem parcial.
- [ ] **Step 4: GREEN.** Suíte alvo, depois suíte nova completa sob Xvfb e testes de restore/closing_recovery/form_keyboard. `--help` continua sem exigir display/login. Nenhum service exige uma senha em cada consulta: a barreira deste aplicativo local é a sessão/UI, sem alegação de criptografia do banco.
- [ ] **Step 5: Commit.** diff--check; `git commit -m 'feat: protege entrada do Bar Simples com login e recuperacao'`.

### Task A4: Identidade Tradicional

**Files:** Create `ui/branding.py`, `assets/bar_simples_logo.png`, `assets/bar_simples_icon.png`, `tests_v2/test_branding.py`; Modify `ui/access.py`, `ui/app.py`, `ui/theme.py`, `ui/assets.py`, `scripts/demo_v2.py`, `tests_v2/test_navigation.py`.

**Interfaces:** `branding.APP_NAME = 'Bar Simples'`; `branding.load_logo(master, max_size) -> PhotoImage`; `branding.load_icon(master, max_size) -> PhotoImage`; consumir carregador base64 local já existente. Manter ícone de moto no delivery.

- [ ] **Step 1: Escrever testes.** `test_traditional_branding_assets_local_and_bounded`: nome na janela e entrada; assetsPNG com transparência, referências retidas; logo/ícone cabem no limite solicitado; redimensionar não altera arquivo original. `test_access_fields_and_primary_action_fit_1366x768`: geometria da configuração completa e login; SegoeUI no Windows, fonte nativa no Linux. `test_demo_uses_setup_flow_without_real_store_data`: demo inicia isolada sem credencial de produção nem bypass.
- [ ] **Step 2: RED.** Xvfb unittest test_branding/test_navigation/test_access_ui; falha por marca/assets ausentes.
- [ ] **Step 3: Implementar.** Usar imagegen para adaptar a terceira opção da prancha aprovada: logo completa balcão/banquetas/copo e símbolo simplificado coerente, sem trocar o conceito. Preservar prancha original; nada de processamento de imagem por Python. Entrada em duas áreas (marca e formulário), creme/verde/terracota, sem animações. Cabeçalho/ícone sem esticar proporções; aplicação continua offline. Texto de login/erros em português claro, sem detalhes técnicos no fluxo. Atualizar demo para cadastro normal da conta fictícia.
- [ ] **Step 4: GREEN e inspeção agrupada.** Testes alvo; uma rodada visual SETUP/TRANSITION/LOGIN/RECOVERY e cabeçalho em1366×768, um lote de correções e uma confirmação máxima. Não declarar Windows100%/125% verificado por Xvfb.
- [ ] **Step 5: Commit.** diff--check; `git commit -m 'feat: aplica identidade Tradicional do Bar Simples'`.

### Task A5: Integração do acesso

**Files:** Create `tests_v2/test_access_end_to_end.py`; Modify `docs/manual-v2.md`, `docs/validacao-bar-simples.md`.

**Interfaces:** Consome AccountService/Application e seed_legacy_pin definidos acima. Entrega checkpoint autenticável para o plano B, sem trocar versão/ZIP ainda.

- [ ] **Step 1: Escrever teste.** `test_populated_v02_upgrade_login_sensitive_action_restart_recovery_restore`: banco014 com PIN6/produto/saldo/venda; upgrade→prova antiga→conta+PIN007→login→autorizar ação sensível uma vez→reinício exige senha→recuperação rotaciona chave→restaurar backup anterior exige credencial restaurada; IDs/saldos/histórico iguais onde não houve operação autorizada. `test_abandoned_setup_is_retryable`: cancelar sem criar conta ou consumir prova definitivamente; reiniciar retoma.
- [ ] **Step 2: RED.** Xvfb unittest test_access_end_to_end; executar antes de corrigir qualquer falha de integração.
- [ ] **Step 3: Concluir integração e documentação.** Somente ajustes necessários aos testes; manual distingue senha/PIN/chave, atualização autenticada sem reset, ausência de criptografia do banco e limites de recuperação. Registrar decisões/resultados reais; sem marcar teste planejado como aprovado.
- [ ] **Step 4: GREEN.** Suíte nova completa e legado sob Xvfb; diff--check. Falhas novas justificam ampliar verificação; não repetir suítes verdes sem mudança. Revisão final independente pertence a B4 e abrange ambos os planos.
- [ ] **Step 5: Commit.** `git commit -m 'test: valida transicao e recuperacao do acesso Bar Simples'`; seguir plano B com mesmos contratos.

## Autorrevisão do plano

Cobertura: credenciais/migraçãoA1–2; entrada/Enter/atalhos/restauraçãoA3; marca/layoutA4; banco populado e documentaçãoA5. Cinco ReviewFocus vinculados a testes nomeados. Sessão definida em A2 consumida em A3; tabela015 antecede016 do planoB. Fixtures atuais de seis dígitos e views montadas antes do login foram identificadas e têm adaptação explícita, preservando assertivas. Alterações no produto começam após revisão deste plano e do planoB pelo usuário; preferência anterior por execução nativa nesta sessão será preservada, se confirmada na revisão.
