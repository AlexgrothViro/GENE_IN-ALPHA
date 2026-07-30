# Changelog

Todas as mudanças notáveis deste projeto estão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [2.0.0-alpha.2] — Contrato único e contenção em shadow mode

### Corrigido

- O contrato público agora separa estado de execução, outcome da análise e nível de evidência; a política alpha.2 só permite E1 ou NOT_EVALUABLE.
- Suporte e cobertura passaram a preservar referência, categoria, locus, orientação e consultas associadas antes da classificação.
- Métricas de informação passaram a operar somente no span efetivamente coberto pelo candidato.
- Controle de lote recompõe a decisão e bloqueia padrões rastreáveis de transferência entre amostras.
- Leituras científicas usam UTF-8 estrito; entradas SAM estruturalmente inválidas interrompem o estágio.
- O roteador de busca por comprimento é compartilhado por fluxos auxiliares e V2.
- Promoções usam manifesto com hashes, sincronização e `SUCCESS.json` escrito por último.

### Segurança de interpretação

- Artefatos Evidence V2 anteriores ao contrato Alpha.2 são classificados como `LEGACY_INCOMPATIBLE`/`NOT_EVALUABLE`, preservados para auditoria e nunca adaptados automaticamente para E1. Qualquer adaptação excepcional exige comando explícito, identificador e hash da origem.
- ML, variante, linhagem e E4 continuam fora do escopo desta versão.

---

## [1.1.0] — Gene-In 1.1 (2026-05)

### Fase 2 — Revisão e atualização da documentação pública

- `README.md`: título atualizado para **Gene-In 1.1**; nome do diretório na árvore de estrutura corrigido; referência a `docs/DEMO.md` (arquivo removido na Fase 1) eliminada.
- `docs/PAINEL_UX.md`: título histórico do painel atualizado para **Gene-In 1.1**.
- `bundle/README_BUNDLE.md`: título corrigido de "Picornavirus Pipeline" para **Gene-In 1.1**.
- `docs/SCRIPTS_MATRIX.md`: caminhos dos scripts legacy corrigidos (prefixo `scripts/legacy/`); adicionados `01_run_metaspades.sh` e `21_run_advanced_analysis.sh`; contagens do resumo atualizadas (29 ativos, 3 wrappers, 12 legacy).


### Fase 2B — Bloco 2: documentação operacional

- `docs/PAINEL_UX.md` atualizado para reforçar o painel como interface local de verificação de ambiente, DEMO, banco viral, importação de amostras, execução de pipeline, logs e histórico de artefatos.
- `docs/RELEASE_CHECKLIST.md` atualizado para checklist de release técnico, com foco em validação operacional, documentação e segurança de dados.
- `environment.yml` renomeado para `gene-in`, sem remoção de dependências.

---

## [Unreleased] — Correções de infraestrutura Windows/WSL

### Refatorado e protegido

- O filtro de hospedeiro agora prepara e valida o par de FASTQs em staging antes da promoção, preservando saídas anteriores quando a nova geração falha.
- A validação compartilhada de índices Bowtie2 exige os seis componentes de índices `.bt2` ou `.bt2l`; o pipeline principal reutiliza o mesmo contrato.
- Configuração operacional local e referências/índices de hospedeiro foram excluídos do versionamento para evitar exposição de caminhos locais e commits de artefatos com vários gigabytes.

### Corrigido

- **`start_platform.bat`**: adicionado `-ExecutionPolicy Bypass` para contornar política
  restrita do PowerShell; tempo de espera ampliado de 75 para 300 tentativas (~10 min),
  cobrindo o download inicial do ambiente na primeira execução.
- **`bundle/run.bat`**: detecção de distro WSL reformulada ("foolproof"). O script tenta
  primeiro a distribuição padrão (sem `-d`), depois itera sobre nomes comuns
  (Ubuntu, Ubuntu-24.04/22.04/20.04, Debian). Se nenhuma for encontrada, exibe painel
  de erro amigável com instruções passo a passo para instalar o WSL.
- **`bundle/install_wsl.sh`** e **`bundle/run.sh`**: `BUNDLE_DIR` alterado de
  `$ROOT/.bundle` para `$HOME/.gene-in-bundle`. O motor da plataforma agora fica no
  sistema de arquivos nativo do Linux, evitando o erro `cannot copy symlink` do
  Micromamba e a lentidão de ferramentas IO-heavy (ex.: SPAdes) no NTFS (`/mnt/c/…`).
- **`bundle/wait_for_server.ps1`**: substituída a checagem HTTP (`Invoke-WebRequest`)
  por ping direto de socket TCP (`System.Net.Sockets.TcpClient`). Elimina o travamento
  invisível causado pelo motor do Internet Explorer não configurado no Windows.

---



### Fluxo oficial

O projeto tem agora um fluxo oficial único e documentado:

```bash
make test-env
make db DB=ptv
make demo
make run-demo
make test-demo SAMPLE=DEMO
```

Para amostras reais:

```bash
make run SAMPLE=<id> R1=<R1.fastq.gz> R2=<R2.fastq.gz> DB=ptv
```

### Foco científico

- Recuperação e triagem de **fragmentos virais curtos** (20–100 pb) em dados metagenômicos.
- Banco dirigido a **Picornaviridae**, especialmente **Teschovirus A (PTV)**, com suporte
  a outros alvos (Enterovirus G, Sapelovirus A, Senecavirus A, FMDV).
- Classificação de hits em `STRONG`, `MODERATE`, `WEAK_RECOVERABLE`, `REVIEW`.
- Saídas auditáveis: TSV com metadados completos, relatório Markdown, log de execução.

### Organização de scripts

- Scripts do fluxo principal permanecem em `scripts/`.
- Scripts do fluxo avançado anterior (alinhamento, filogenia, extensão de flancos)
  movidos para `scripts/legacy/`.
- Ponto oficial de preparação de banco: `scripts/13_db_manager.sh` (`make db`).
- Ponto oficial de execução: `scripts/20_run_pipeline.sh` (`make pipeline`).

### Documentação

- `README.md` reestruturado com seções: Início rápido, Fluxo oficial, Como preparar banco,
  Como rodar demo, Como interpretar resultados, Limitações atuais.
- `docs/SCRIPTS_MATRIX.md`: tabela de status de todos os scripts (ativo/wrapper/legacy).
- `docs/ARTIFACTS.md`: descrição de todos os artefatos de auditoria.
- `docs/RELEASE_CHECKLIST.md`: checklist para releases futuras.
- `docs/MODO_DE_USO.md` atualizado (removidas referências a scripts legados).

### Makefile

- Novo alvo `clean-safe`: remove apenas temporários e cache, preserva `results/` e `logs/`.
- Novo alvo `clean-all`: limpeza completa com confirmação obrigatória.
- Alvos `clean-safe` e `clean-all` documentados em `make help`.

### Testes mínimos verificados

- `make test-env`: verifica dependências no PATH.
- `make help`: lista todos os alvos disponíveis.
- `make test-demo SAMPLE=DEMO`: valida artefatos após execução do demo.

### Limitações conhecidas

- Não garante montagem de genoma completo.
- Fragmentos curtos (< 50 pb) exigem interpretação cautelosa.
- BLAST permissivo aumenta recuperação, mas exige rastreabilidade (todos os hits são mantidos).
- Resultados dependem de contexto biológico e controles negativos.
- Banco baseado no NCBI público; cobertura varia entre genótipos.

---

## [0.1.0-alpha] – 2026-05

### Adicionado
- `ai/rules/short-fragment-validation.md`: regra de validação de fragmentos virais curtos.
- CLI em `20_run_pipeline.sh` para `--assembler`, `--spades-params`, `--blast-task`, `--blast-word-size` e `--blast-evalue`.
- Suporte a metaSPAdes como montador via `--assembler metaspades`.
- Classificação de hits em `STRONG`, `MODERATE`, `WEAK_RECOVERABLE` e `REVIEW` (`label_hits.py`).
- Campos `evidence_class` e `risk_note` no relatório mínimo (`95_report_minimal.sh`).
- Campos `qlen` e `slen` no formato de saída do BLAST.
- Persistência de `adj_identity.tsv` e `labeled_hits.tsv` em `results/blast/`.
- `benchmark_preliminar.py` (30_): tabela e gráficos de benchmark preliminar.
- Parâmetros BLAST configuráveis: `BLAST_TASK`, `BLAST_WORD_SIZE`, `BLAST_EVALUE`.
- `Makefile`: alvos `pipeline`, `run-demo`, `report`, `demo`, `benchmark-demo`.
- `Makefile`: variáveis `ASSEMBLER`, `SPADES_PARAMS`, `BLAST_TASK`, `BLAST_WORD_SIZE`, `BLAST_EVALUE` repassadas ao pipeline.
- `LICENSE` (MIT).
- `docs/VALIDACAO_CIENTIFICA.md`: guia de validade científica da classificação.
- `docs/TROUBLESHOOTING.md`: guia de resolução de problemas comuns.

### Corrigido
- Escape de `|` em `sseqid` no relatório Markdown (evita quebra de tabela com IDs no estilo `gb|MF170925.1|`).
- Precedência de configuração: CLI > config.env > padrões internos.
- Compatibilidade com SPAdes antigo via apt (aviso sobre `--rnaviral`).

### Pendente
- Testes com `velvet` e `metaspades` em amostras reais.
- Revisão de dados privados antes de tornar o repositório público.

---

## [0.0.1] – 2025 (pré-histórico)

- Estrutura inicial do pipeline de recuperação de PTV/Picornaviridae.
- Scripts básicos de BLAST, Velvet, SPAdes, filtro de hospedeiro e relatório.
