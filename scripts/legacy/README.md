# Scripts Legacy

> **LEGACY / TEST-ONLY:** estes scripts não têm os gates de evidência da V2,
> não sustentam benchmark, artigo, dissertação ou conclusão científica nova.
> O fluxo avançado usa diretórios isolados em `results/legacy/` por padrão e
> não executa `make test`, não reconstrói bancos e não remove resultados
> compartilhados. Dependências ausentes devem produzir falha explícita.

Para testes controlados, defina `LEGACY_WORK_DIR` para um diretório temporário
e forneça entradas e banco já validados. Nenhum dado exploratório antigo,
incluindo execuções operacionais fora do conjunto formal, pode ser promovido a
evidência de validação.

Scripts do fluxo avançado anterior ao pipeline atual (`v1.0.0`).

Esses scripts **não fazem parte do fluxo oficial** e não são chamados pelo `Makefile` principal.
Estão preservados aqui para referência e possível reutilização futura.

## Conteúdo

| Script | Função original |
|---|---|
| `run_ptv_advanced.sh` | Fluxo avançado completo de PTV (fluxo anterior ao `20_run_pipeline.sh`) |
| `align_ptv_fragments.sh` | Alinhamento múltiplo de fragmentos PTV com MAFFT |
| `align_ptv_region.sh` | Alinhamento de região específica de PTV |
| `tree_ptv_fragments_iqtree.sh` | Árvore filogenética de fragmentos (requer IQ-TREE) |
| `tree_ptv_region_iqtree.sh` | Árvore filogenética de região (requer IQ-TREE) |
| `extend_plan.py` | Planejamento de extensão de flancos na referência |
| `emit_extend_fasta.py` | Emissão de FASTA de regiões de flanco |
| `sim_reads_clean.py` | Simulação de reads sintéticos de flanco |
| `collect_ptv_contigs.py` | Coleta de contigs PTV de assemblies |
| `build_ptv_region_fasta.py` | Construção de FASTA de regiões PTV |
| `emit_ptv_hit_fragments.py` | Emissão de fragmentos a partir de hits BLAST |
| `merge_report.py` | Mesclagem de relatórios de múltiplos runs |

## Como usar (se necessário)

Antes de usar qualquer script deste diretório, verifique se as dependências estão instaladas
(`mafft`, `iqtree` ou `iqtree2`) e ajuste os caminhos conforme necessário.

Consulte `docs/SCRIPTS_MATRIX.md` para a visão completa de todos os scripts do projeto.
