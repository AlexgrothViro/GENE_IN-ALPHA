# Matriz de remediação — Gene-In 2.0 alpha.2

Esta matriz mantém o vínculo entre falhas identificadas, componente responsável, regressão literal e critério de aceite. `Passa em fixture` não equivale a execução científica real.

| Achado / forma | Componente responsável | Regressão literal | Critério de aceite | Estado |
|---|---|---|---|---|
| Agregação perde identidade (Forma 1) | `summarize_read_support.py`, `summarize_coverage.py`, `classify_sample.py` | `test_host_only_support_cannot_promote_target`; `test_support_must_match_reference_category_and_locus` | Métrica somente entra por referência, categoria e locus idênticos | fixture implementada |
| Métrica fora do escopo (Forma 6) | `phylogeny_gate.py` | `test_reference_only_variation_is_not_candidate_information`; `test_informative_sites_are_limited_to_candidate_span` | Colunas fora do span candidato não contam | fixture implementada |
| Rótulo público dissociado do gate (Forma 4) | `evidence_contract.py`, `classify_sample.py` | `test_alpha_policy_rejects_e2_even_when_schema_enum_contains_it` | alpha.2 só emite E1 ou NOT_EVALUABLE | fixture implementada |
| Sem candidatos confundido com ausência (Forma 7) | `classify_sample.py`, `04_extract_hits.py` | `test_zero_filtered_hits_is_no_evidence_not_absence` | outcome explícito, lista vazia e ressalva | fixture implementada |
| Falha científica confundida com resultado | `evidence_contract.py`, `run_state.py` | `test_failed_scientific_stage_is_not_evaluable` | NOT_EVALUABLE preservado no estado | fixture implementada |
| Raiz de evidências divergente | `20_run_pipeline.sh`, `23_run_batch.sh` | `test_custom_evidence_root_reaches_all_child_runs` | raiz resolvida atravessa lote e filhos | teste estrutural implementado; execução Linux pendente |
| Bytes inválidos ocultados | leitores científicos | `test_invalid_utf8_blocks_scientific_artifact` | UTF-8 estrito com falha do estágio | fixture implementada |
| SAM malformado descartado | `summarize_read_support.py` | `test_malformed_sam_blocks_support` | erro com arquivo e linha | fixture implementada |
| Deduplicação não reprodutível | `map_read_support.sh` | `test_umi_dedup_is_reproducible_with_seed` | semente registrada e hashes iguais em ferramenta real | fixture parcial; ferramenta real pendente |
| Perfil BLAST divergente por tamanho | `blast_router.py` | `test_length_routes_to_expected_blast_profile` | todos os chamadores usam o roteador e registram perfil | fixture implementada; ferramenta real pendente |
| Controle tardio sem recálculo | `apply_control_status.py` | `test_failed_controls_recompute_and_demote` | decisão é reconstruída após controles | fixture implementada |
| Padrão doador→receptor | `evaluate_controls.py` | `test_negative_donor_receiver_pattern_blocks_promotion` | promoção bloqueada e doador rastreável | fixture implementada |
| Sucesso parcial | finalizadores e manifesto | `test_success_requires_complete_verified_manifest` | hash, estado por amostra e manifesto íntegros antes de SUCCESS | fixture implementada |
| A1 — ambiente sem lock verificável | `conda-linux-64.lock`, `environment_lock.py`, `runtime_preflight.py` | `test_lockfile_hash_mismatch_blocks_run` | lock explícito com hashes e manifesto divergente bloqueia antes de análise | fixture implementada; execução Linux limpa pendente |
| A2 — índice reaproveitado por timestamp | `13_db_manager.sh`, `index_cache.py` | `test_index_reuse_blocked_on_content_change_same_timestamp` | conteúdo da referência e identidade/versionamento do construtor devem coincidir | fixture implementada; execução com BLAST/Bowtie2 reais pendente |
| A3 — ShellCheck sem gate | `.github/workflows/shellcheck.yml` | execução ShellCheck em todos os `*.sh` | CI bloqueia qualquer warning; sem supressão global | **parcial: gate criado; 60 warnings existentes** |
| A4 — legado fora de staging unificado | `20_run_pipeline.sh` | ainda não há regressão de queda do legado | nenhum artefato legado parcial chega a caminho canônico | **não resolvido; requer migração estrutural do legado** |
| A5 — caminho de saída sem promotor canônico | `evidence_contract.py`, `evidence_dashboard.py`, `export_evidence.py` | `test_no_output_path_bypasses_single_promoter` | dashboard, API e exportador usam a mesma adaptação/validação; JSON bruto é recusado | fixture implementada |
| B1 — cancelamento com falha silenciosa | `ux_dashboard.py`, `run_state.py` | `test_dashboard_reports_cancellation_group_kill_failure_as_failed_not_success` | falha de sinalização torna o job `failed` com `CANCELLATION_FAILED` | fixture implementada; teste de processo real Linux pendente |
| B2 — cache do dashboard | `ux_dashboard.py` | `test_dashboard_no_legacy_cache_bypasses_shadow_mode` | JSON da API entrega `no-store`, `Pragma` e expiração | fixture implementada; navegador real pendente |
| B3 — linguagem de UI | `docs/UI_LANGUAGE_AUDIT.md`, dashboard e exportador | auditoria estática registrada | E1/sem candidatos/não avaliável não viram alegação biológica | revisão estática concluída; revisão visual pendente |
| B4 — método de revisão visual | `docs/UI_LANGUAGE_AUDIT.md` | roteiro de três estados | método está declarado e limitações são públicas | método declarado; execução em navegador pendente |

## Evidência de execução — 2026-07-14

Os testes novos foram executados no worktree atual com `python -m unittest discover -s scripts/tests -p "test_*.py"`: **66 testes, OK**. `python -m compileall -q scripts`, `node --check dashboard/app.js`, `git diff --check` e `bash -n` via Git Bash para os entrypoints alterados também passaram.

O lock foi validado com `python scripts/evidence/environment_lock.py --lockfile conda-linux-64.lock --manifest config/environment_lock.json`: 156 entradas de pacotes e SHA-256 `a916e8c05052269ab89eb6599610f9dcd7818b61233c5c196d623ab316fcd14b`.

ShellCheck 0.11.0 foi executado de verdade sobre todos os scripts rastreados: **58 warnings**, com SC1090=49 e SC2034=9; SC2155 e SC2164 foram corrigidos. Portanto A3 permanece parcial. Não foi usado `bash -n` como substituto de ShellCheck.

Não havia snapshot executável dos testes novos antes desta mudança. A inspeção do `HEAD` anterior confirma os gatilhos estruturais: `13_db_manager.sh:308,362` usava `-ot "$REF_FASTA"`; `runtime_preflight.py` não tinha lockfile; `ux_dashboard.py` continha exceções de cancelamento silenciadas; e `20_run_pipeline.sh:811` copiava diretamente ao destino canônico. Esta evidência histórica não é apresentada como uma execução “antes”; por isso os itens que ainda dependem de Linux, navegador ou migração do legado não são marcados como resolvidos.

## Critérios ainda obrigatórios antes de sair de shadow mode

- Testes ponta a ponta com ferramentas reais em Linux congelado.
- Dados públicos e sintéticos formalmente versionados, incluindo controles e competidores.
- Repetição independente em ambiente limpo.
- Verificação de queda, retry, concorrência e cancelamento.
- Nova auditoria sênior sem bloqueadores.

## Execução real — roteiro de 2026-07-14

### ENV_BASELINE

**Estado: BLOQUEADA_POR_AMBIENTE.** A pré-condição do roteiro não está satisfeita: `wsl.exe --list --quiet` não retornou distribuição Linux; não há remoto Git configurado nem cliente de CI disponível neste worktree. O lock e seu manifesto existem, mas não foram instalados nem aprovados num Linux real. Consequentemente, `runtime_preflight.py` não foi executado contra BLAST+, Bowtie2, samtools, SPAdes/metaSPAdes, UMI-tools, MAFFT e IQ-TREE reais.

Evidência local preservada: `config/environment_lock.json` referencia `conda-linux-64.lock`, com SHA-256 `a916e8c05052269ab89eb6599610f9dcd7818b61233c5c196d623ab316fcd14b` e 156 entradas explícitas. Isto verifica a integridade do artefato, não o ambiente científico resolvido.

### SYNTHETIC_CORE_CASES

**Estado: BLOQUEADA_POR_AMBIENTE.** As quatro execuções ponta a ponta com BLAST+/Bowtie2/samtools reais não foram iniciadas: HOST_chr1 exclusivo, referências virais distintas, locus parcialmente ambíguo e sítios fora do span candidato. Os testes de fixture permanecem evidência de unidade, não execução real.

### CONTROL_SCENARIOS

**Estado: BLOQUEADA_POR_AMBIENTE.** Não foram executados dados reais ou públicos de positivo conhecido, negativos, competidor, host/vetor/contaminante, negativeome, index hopping ou controles falhos. `shadow_mode` permanece obrigatório.

### Fases dependentes de Linux, CI ou navegador

| Fase | Estado | Motivo verificável |
|---|---|---|
| 0 — ambiente | BLOQUEADA_POR_AMBIENTE | sem distribuição Linux provisionada |
| 1 — CI ShellCheck | BLOQUEADA_POR_AMBIENTE | workflow existe, mas não há remoto/provedor configurado para dispará-lo |
| 2 — casos sintéticos reais | BLOQUEADA_POR_AMBIENTE | requer ferramentas Linux reais aprovadas pelo preflight |
| 3 — A1 real | BLOQUEADA_POR_AMBIENTE | requer ambiente Linux do lock |
| 4 — A2 real | BLOQUEADA_POR_AMBIENTE | requer makeblastdb e bowtie2-build reais |
| 5 — A4 real | BLOQUEADA_POR_IMPLEMENTAÇÃO_E_AMBIENTE | staging legado ainda não foi migrado; depois requer SIGKILL Linux |
| 6 — B1 real | BLOQUEADA_POR_AMBIENTE | requer árvore de processos Linux e dashboard em execução |
| 7 — B2 real | BLOQUEADA_POR_AMBIENTE | requer navegador real com aba aberta durante promoção |
| 8 — B4 real | BLOQUEADA_POR_AMBIENTE | requer navegador real e três artefatos de resultado |
| 9 — controles reais | BLOQUEADA_POR_AMBIENTE | requer dados versionados e ferramentas reais |
| 10 — falhas transacionais reais | BLOQUEADA_POR_AMBIENTE | requer execução Linux e injeção controlada de falhas |

Próximo desbloqueio autorizado: provisionar CI Linux real e executar a Fase 0 integralmente a partir do lockfile. Não instalar WSL, publicar o repositório nem disparar CI sem autorização explícita.
