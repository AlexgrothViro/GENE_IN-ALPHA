# Registro de contribuição assistida por IA

## 2026-07-14 — revisão para preparação do repositório Git

- Ferramenta: Codex, assistência de engenharia por IA.
- Escopo: segurança do versionamento, validação compartilhada de índices Bowtie2 e promoção transacional dos FASTQs do filtro de hospedeiro.
- Arquivos afetados: `.gitignore`, `scripts/lib/host_filter.sh`, `scripts/03_filter_host.sh`, `scripts/20_run_pipeline.sh`, `scripts/tests/test_host_filter.py`, `CHANGELOG.md` e este registro.
- Testes executados: testes Python determinísticos, `compileall`, `bash -n` com Git Bash e verificação sintática JavaScript; ferramentas científicas reais continuam fora deste teste.
- Limiares científicos: não foram alterados; `HOST_MIN_ALIGNMENT_RATE` e todas as classes/políticas científicas foram preservados.
- Shadow mode e conclusão oficial 1.1: preservados.
- Revisão humana: pendente antes do envio ao GitHub e de qualquer validação científica.

## 2026-07-13 — estabilização da Evidence V2

- Ferramenta: Codex, assistência de engenharia por IA.
- Escopo: preflight do runtime, estados 1.1/V2, promoção transacional, dashboard/API, agregação de HSPs/loci, controles, revisão isolada do legado e testes determinísticos.
- Arquivos afetados: `scripts/evidence/`, `scripts/22_run_evidence_v2.sh`, `scripts/20_run_pipeline.sh`, `scripts/23_run_batch.sh`, `scripts/ux_dashboard.py`, `scripts/lib/evidence_dashboard.py`, `dashboard/`, `scripts/legacy/`, `scripts/tests/` e documentação de validação.
- Testes executados: 39 testes Python, compilação Python e verificação sintática JavaScript aprovadas; validação Linux/WSL ainda pendente.
- Limiares científicos: não foram alterados; continuam provisórios e em calibração.
- Shadow mode e conclusão oficial 1.1: preservados.
- Revisão humana: pendente antes de qualquer ativação científica ou adoção tecnológica.
