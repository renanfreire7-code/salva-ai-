# SDD ledger — plan: docs/superpowers/plans/2026-10-17-bar-simples-recuperacao-email.md
BASE89f61bf; branch feat/salva-ai-v2; spec/plan approved; native execution already chosen.
Ruling: reuse existing isolated cloud checkout — user preference and onboarding guidance — cost: isolation depends on supplied checkout.
Ruling: cloud skill execution helpers not locally available; use equivalent briefs/log/ledger outside checkout — cost: manual orchestration.
Pre-flight E1→E2: config/VerifiedIdentity/NetworkRunner types coherent; callbacks main-thread and provider never reads DB.
Pre-flight E2→E3: proof consumed in DB transaction before credentials mutation; memory invalidation only after outer commit, rollback retains proof.
Pre-flight E3→E4: AccountService optional emails/backups keeps legacy API; new wizard uses proof methods, login stays offline.
Pre-flight E4→E5: configure script/public JSON/example added explicitly to ZIP; extracted suite excludes independent diagnostic and packager only, full checkout includes all.
Task E1: started; brief read; before implementation tests must fail.
Baseline:210/210 sob Xvfb; E1 complete — módulos ausentes RED e resposta token_type nula RED→GREEN; alvo7/7, configurador --help e diff--check aprovados. Nenhum envio real: configuração Supabase ausente na máquina.
Task E2: started; brief read next.
Task E1: complete (89f61bf..bb3f836, target7/7, baseline210/210).
Task E2: Ruling: add verify_after to challenge metadata — provider429 must throttle verification independently from ordinary resend60 — cost: one additive internal column, no external API change.

Task E2 complete: challenges, replay/revision/rollback/clock/rate limits; 23/23 targeted and legacy access tests passed.

Task E3 complete: 23/23 account/security tests, transaction rollback/proof retry and preserved PIN; commit169e9b8 (later E4 integration factors legacy creation to avoid precommit grant invalidation).

Task E4 complete: 34/34 targeted Tk/access/branding/navigation/keyboard tests; one grouped visual inspection of4modes at1260x680 and1366x768, no clipping found. Native Windows/DPI not tested. Creation helper now clears grants only after successful outer transaction.

Task E5: integration2/2, distribution2/2 PASS. Full checkout and extracted suites running; legacy30/30 PASS. Activation remains externally pending (no Supabase project). Final reviewer may inspect committed implementation while these suites run; no passing claim for unfinished suites.

Final review: fresh reviewer gpt-6-astra high, range39a6927..0fd1f59; no Critical/Important. No fix pass needed.
Final: minor (deferred): local SQLite error during asynchronous send/verify callback may leave wizard busy with no error; Back remains available, credentials unchanged. Future regression: abort VERIFIED write after valid OTP, assert error/busy reset/no proof then fresh-code retry.
Final: Ruling: real Supabase/template/SMTP/remote policy not judged — deliver code with email activation explicitly pending and require real receipt before operational acceptance — cost if wrong: undelivered or mismatched codes.
Final: Ruling: native Windows100%/125% and operator acceptance not judged — retain those explicit acceptance checks; Xvfb proves only tested geometry — cost if wrong: platform-specific layout/behavior defects.
Final: Ruling: suite outcomes left to parent — require completed checkout/extracted/legacy outputs before delivery — cost if wrong: unnoticed regression.
Final: Ruling: historical code before39a6927 outside fresh review — preserve previous work and run broad regression suites; feature-focused review is not a new audit of historical code — cost if wrong: pre-existing defects remain outside this audit.

Task E5: complete local validation — full checkout241/241 (283.071s), integration2/2 (11.988s; includes additional atomic/restart test added during full discovery), legacy30/30 (1.631s), extracted236/236 (259.966s). No skipped/expected failures. Manifest170 entries and sources/manual/guide match final ZIP; public config absent and real mail not activated. Additional bounded confirmation capture checks unchanged authenticated delivery/sales branding; no cosmetic edits. Remote delivery next.

Task E5: complete (local code/package/review/delivery). Push1c7363f succeeded, remote HEAD exact, ZIP HTTP200 SHA256b40f9822712b7cb5e94c1776c117aec5ac1541adafc2e4f8610dd3f84f7b568e. Activation/Windows/operator acceptance remain external prerequisites, not claimed complete. Finishing skill uses already-authorized branch push; no new integration menu required. Records copied to docs/validacao-email before deleting this plan-owned scratch directory.
