# Artefatos de Auditoria

Este documento descreve os arquivos gerados pelo Gene-In 1.1 para auditoria, reprodutibilidade e interpretação científica.

---

## Artefatos principais por amostra

Após executar `make pipeline SAMPLE=<id>` ou `make run ...`, os principais artefatos são:

| Arquivo | Descrição |
|---|---|
| `data/assemblies/{SAMPLE}_assembly/contigs.fa` | Contigs montados da amostra. |
| `results/blast/{SAMPLE}_vs_db.tsv` | Hits BLAST brutos. |
| `results/blast/{SAMPLE}_adj_identity.tsv` | Hits com identidade ajustada (`adj_identity`). |
| `results/blast/{SAMPLE}_labeled_hits.tsv` | Artefato histórico de compatibilidade; a classe é `legacy_label`, com teto E1. |
| `results/evidence/runs/{RUN_ID}/sample_evidence.json` | Artefato canônico 2.0: estado de execução, outcome, E1/E2/E3/NOT_EVALUABLE, gates, caveats e proveniência. |
| `results/reports/{SAMPLE}_summary.md` | Relatório final em Markdown. |

---

## Artefatos adicionais em execução via dashboard

Execuções disparadas pelo dashboard podem gerar também:

- `logs/ux_dashboard_*.log`
- `results/runs/<timestamp>_<sample>/run.json`

Esses arquivos ajudam na trilha de auditoria da execução (parâmetros, horário e status).

---

## Contrato de interpretação

O contrato canônico 2.0 separa `execution_status`, `analysis_outcome` e `evidence_level`. Na alpha.2, E2/E3 são inalcançáveis e E4 não existe na saída. Um resultado sem candidatos não representa ausência; uma etapa inválida é `NOT_EVALUABLE`.

Execuções Evidence V2 anteriores à Alpha.2 são artefatos históricos incompatíveis, mesmo que contenham `SUCCESS.json`. O dashboard exige a versão exata do contrato, todos os campos/headers obrigatórios, `artifact_manifest.json` completo, hashes verificáveis e `shadow_mode=true`. Se qualquer requisito falhar, retorna `LEGACY_INCOMPATIBLE` ou `ALPHA2_INVALID` com `NOT_EVALUABLE`, preserva os arquivos e solicita reexecução. Nenhum campo é preenchido retroativamente e nenhuma classe antiga é promovida automaticamente para E1.

Os diretórios `results/evidence/runs/79f201633acf43b9a395c23725d2e0f0` e `results/evidence/runs/8e612a9309d94d8eae8dca0d291af199` devem ser tratados como históricos Alpha.1 e mantidos para auditoria até que as respectivas análises sejam reexecutadas.

As classes históricas de `labeled_hits.tsv` são mantidas somente para leitura de compatibilidade. Elas não constituem níveis públicos e não podem produzir afirmações de presença, ausência, identidade, confirmação, variante ou linhagem.

---

## O que não fica versionado

Por privacidade, volume e reprodutibilidade operacional, normalmente não são versionados:

- `data/raw/` (FASTQs de entrada)
- `data/ref/` (referências baixadas)
- `blastdb/` e `bowtie2/` (índices gerados)
- `results/` (resultados por amostra)
- `logs/` (logs de execução)
