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
| `results/blast/{SAMPLE}_labeled_hits.tsv` | Hits classificados com `evidence_class` e `risk_note`. |
| `results/reports/{SAMPLE}_summary.md` | Relatório final em Markdown. |

---

## Artefatos adicionais em execução via dashboard

Execuções disparadas pelo dashboard podem gerar também:

- `logs/ux_dashboard_*.log`
- `results/runs/<timestamp>_<sample>/run.json`

Esses arquivos ajudam na trilha de auditoria da execução (parâmetros, horário e status).

---

## Classes de evidência (classificação operacional)

A classificação em `results/blast/{SAMPLE}_labeled_hits.tsv` segue os critérios abaixo (compatíveis com `scripts/label_hits.py`):

### `STRONG`

- `length >= 80`
- `pident >= 90`
- `adj_identity >= 70`
- `evalue <= 1e-10`

### `STRONG_DIVERGENT`

- `length >= 1000` ou `qlen >= 1000`
- `aln_cov >= 0.80`
- `80 <= pident < 90`
- `evalue <= 1e-10`

### `MODERATE`

- `50 <= length < 80`
- `pident >= 85`
- `adj_identity >= 60`
- `evalue <= 1e-5`

### `WEAK_RECOVERABLE`

- `20 <= length < 50`
- `pident >= 90`
- `bitscore >= 35`
- exige revisão manual

### `REVIEW`

- todos os demais casos

> `risk_note` é um alerta de cautela para interpretação, e não um erro de execução.

---

## O que não fica versionado

Por privacidade, volume e reprodutibilidade operacional, normalmente não são versionados:

- `data/raw/` (FASTQs de entrada)
- `data/ref/` (referências baixadas)
- `blastdb/` e `bowtie2/` (índices gerados)
- `results/` (resultados por amostra)
- `logs/` (logs de execução)
