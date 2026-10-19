# Revisão antes da apresentação — 0.4.3-dev

Data: 19/10/2026. Escopo: corrigir a confirmação e a apresentação de erro da restauração de backup, verificar a abertura direta e entregar um pacote identificado para demonstração.

## Causa e correção

`RestoreService.apply()` reconstrói a interface pelo callback de conclusão, inclusive quando uma substituição iniciada falha. Essa reconstrução destrói as janelas de auditoria e backup. A interface tentava mostrar o sucesso ou o erro usando uma dessas janelas já destruídas.

A confirmação agora usa a janela principal. Depois da restauração bem-sucedida, o aplicativo encerra e libera banco e bloqueio de instância, mesmo se a apresentação do aviso falhar. As ações do centro de backup podem apresentar erros na janela principal por meio do parâmetro opcional `error_parent` de `View.act`; demais chamadas mantêm seu comportamento anterior.

Não há alteração de esquema, PIN, conta, diretório de dados ou regras financeiras. A abertura pública continua direta, sem login/e-mail. A mudança deve ser instalada como atualização do programa, preservando os dados existentes.

## Evidências

- Teste pelo botão real de restauração falhou antes da correção: a confirmação recebia uma janela destruída.
- Um segundo teste reproduziu o mesmo defeito na exibição de erro após falha simulada de gravação.
- Quatro testes de interface passam: sucesso e reabertura com o snapshot; cancelamento sem substituir; erro de gravação com dados originais preservados e reabertura; falha da própria mensagem final com recursos ainda liberados.
- Grupo de restauração, interface e acesso direto: **13/13 aprovados**.
- Suíte completa atual: **258/258 aprovados**, 179,771 s, sem skips ou expected failures.
- Regressão do legado: **30/30 aprovados**, 0,570 s.
- Distribuição: extração e abertura real com Tk em pasta com espaços/acentos, manifesto e ausência de banco/caches, verificadas pela suíte.
- Pacote: 171 arquivos no manifesto, ZIP íntegro e todos os hashes internos conferidos.

Comandos usados na raiz:

```sh
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a -s '-screen 0 1366x768x24' python3 -m unittest discover -s tests_v2 -t . -v
PATH=/workspace/.cloud-setup/x11/usr/bin:$PATH xvfb-run -a python3 -m unittest discover -s tests -t . -v
python3 scripts/build_v2.py
```

O comando legado inicialmente executado sem `-t .` falhou na resolução dos módulos `app`/`core`; foi corrigido para o comando documentado acima e os 30 testes executaram com sucesso.

## Entrega e limite prático

Arquivo: `dist/Bar_Simples_0.4.3-dev_sem_login.zip`.
SHA256: `532c4458051bd2420f5edec303bc3d4ef15f978858624bb4a97bb7a8dcc260f2`.

Foram atualizados os manuais PDF de instalação e uso e criado um roteiro curto em `docs/roteiro-apresentacao.md`. Os PDFs 0.4.2 permanecem como histórico, e o ZIP anterior não foi substituído.

A validação técnica foi em Linux/Xvfb. Criação de atalho, ausência real de console, escala e usabilidade precisam de ensaio no Windows do proprietário. Esta revisão é adequada para apresentação e piloto acompanhado; não equivale a comprovar operação exclusiva em produção. Entrega na branch de desenvolvimento, sem merge em main ou release.
