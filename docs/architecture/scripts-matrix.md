# Matriz de Scripts e Pontos de Entrada

Este documento organiza os pontos de entrada, wrappers e scripts internos do
**Gene-In 1.1**. O objetivo e reduzir ambiguidade operacional: usuarios finais
devem seguir os pontos oficiais; scripts internos continuam documentados para
manutencao e auditoria tecnica.

## 1. Pontos de Entrada Oficiais

| Entrada | Uso recomendado | Status |
|---|---|---|
| `INSTALAR_GENEIN.bat` | Instalacao inicial no Windows/WSL para usuario final. | **Oficial Windows** |
| `ABRIR_GENEIN.bat` | Abertura rotineira do painel local no Windows. | **Oficial Windows** |
| `./install_linux.sh` | Instalacao inicial em Linux nativo. | **Oficial Linux** |
| `./run_linux.sh` | Abertura rotineira do painel local em Linux nativo. | **Oficial Linux** |
| `Makefile` | Execucao CLI avancada (`make demo`, `make db`, `make pipeline`, `make ux`). | **Oficial CLI** |

## 2. Wrappers Necessarios

| Arquivo | Funcao | Status |
|---|---|---|
| `start_platform.bat` | Wrapper Windows para iniciar a plataforma pela rota do bundle. | **Wrapper** |
| `Atualizar Gene-In.bat` | Atualizacao/recriacao do ambiente WSL/bundle. | **Wrapper** |
| `Remover Gene-In.bat` | Remocao assistida do ambiente local do Gene-In. | **Wrapper** |
| `bundle/run.bat` | Ponte Windows -> WSL para comandos do Gene-In. | **Wrapper interno** |
| `bundle/run.sh` | Wrapper Linux/WSL que ativa o ambiente isolado e chama `make`. | **Wrapper interno** |
| `bundle/install_wsl.sh` | Instalacao do ambiente micromamba no WSL. | **Wrapper interno** |
| `bundle/install_wsl_dependencies.sh` | Instalacao de pacotes basicos do Ubuntu quando ausentes. | **Wrapper interno** |
| `bundle/wait_for_server.ps1` | Aguarda o servidor local do dashboard responder no Windows. | **Wrapper interno** |

## 3. Nucleo do Pipeline

Estes scripts compoem o fluxo cientifico principal. O usuario normalmente os
aciona via `Makefile`, dashboard ou wrappers oficiais.

| Script | Funcao principal | Status |
|---|---|---|
| `scripts/20_run_pipeline.sh` | Orquestrador principal do pipeline. | **Ativo / nucleo** |
| `scripts/13_db_manager.sh` | Gerencia download, preparo e indexacao de bancos. | **Ativo / nucleo** |
| `scripts/run_assembly_router.sh` | Seleciona e executa o montador configurado. | **Ativo / nucleo** |
| `scripts/01_run_velvet.sh` | Montagem com Velvet. | **Ativo / nucleo** |
| `scripts/01_run_spades.sh` | Montagem com SPAdes. | **Ativo / nucleo** |
| `scripts/01_run_metaspades.sh` | Montagem com metaSPAdes. | **Ativo / nucleo** |
| `scripts/02_qc_fastp.sh` | Controle de qualidade opcional com fastp. | **Ativo** |
| `scripts/03_filter_host.sh` | Remocao de leituras do hospedeiro com Bowtie2. | **Ativo / nucleo** |
| `scripts/02_run_blast.sh` | Busca BLAST contra banco viral. | **Ativo / nucleo** |
| `scripts/adj_identity.py` | Calcula identidade ajustada dos hits BLAST. | **Ativo / nucleo** |
| `scripts/label_hits.py` | Classifica hits em classes operacionais de evidencia. | **Ativo / nucleo** |
| `scripts/04_extract_hits.py` | Extrai sequencias de hits prioritarios. | **Ativo / nucleo** |
| `scripts/06_export_hit_contigs.py` | Exporta contigs classificados para FASTA. | **Ativo** |
| `scripts/95_report_minimal.sh` | Gera relatorio resumido em Markdown. | **Ativo / nucleo** |

## 4. Scripts Auxiliares Ativos

| Script | Funcao principal | Status |
|---|---|---|
| `scripts/00_check_env.sh` | Diagnostica dependencias e ambiente isolado. | **Ativo** |
| `scripts/00_fix_wsl.sh` | Corrige CRLF e permissoes comuns em WSL. | **Ativo** |
| `scripts/00_import_sample.sh` | Importa FASTQ para `data/raw`. | **Ativo** |
| `scripts/12_stage_sample.sh` | Staging alternativo de FASTQ via `make sample-add`. | **Ativo** |
| `scripts/10_fetch_ptv_fasta.sh` | Baixa FASTA de referencia PTV. | **Wrapper tecnico** |
| `scripts/10_build_custom_db.sh` | Constroi banco customizado a partir de FASTA local. | **Wrapper tecnico** |
| `scripts/10_build_viral_db.sh` | Constroi bancos a partir de `config/targets.json`. | **Wrapper tecnico** |
| `scripts/11_prepare_host_reference.sh` | Prepara referencia e indice Bowtie2 de hospedeiro configuravel. | **Ativo** |
| `scripts/11_download_sus_scrofa.sh` | Wrapper de retrocompatibilidade para preparar Sus scrofa. | **Wrapper** |
| `scripts/12_validate_host_index.sh` | Valida indice Bowtie2 de hospedeiro para scripts e dashboard. | **Ativo / utilitario** |
| `scripts/22_run_assembly_only.sh` | Executa somente montagem para comparacao/diagnostico. | **Ativo auxiliar** |
| `scripts/filter_rescue_reads.py` | Filtra candidatos em nivel de leitura resgatada. | **Ativo auxiliar** |
| `scripts/04_extract_short_fragments.py` | Extrai fragmentos curtos para revisao. | **Ativo auxiliar** |
| `scripts/05_blast_short_fragments.sh` | BLAST de fragmentos curtos. | **Ativo auxiliar** |
| `scripts/05_ptv_enriched_run.sh` | Fluxo enriquecido especifico para PTV. | **Ativo auxiliar** |
| `scripts/06_ptv_postprocess.py` | Pos-processamento especifico de PTV. | **Ativo auxiliar** |
| `scripts/lib/common.sh` | Funcoes shell compartilhadas. | **Biblioteca interna** |
| `scripts/lib/logging_utils.py` | Funcoes de logging para scripts Python. | **Biblioteca interna** |

## 5. Dashboard Local

| Script | Funcao principal | Status |
|---|---|---|
| `scripts/ux_dashboard.py` | Interface web local para execucao guiada, upload, historico, logs e configuracao. | **Ativo auxiliar** |

O dashboard nao e o nucleo cientifico do Gene-In. Ele e uma camada operacional
local que chama o mesmo pipeline usado pela CLI. Por concentrar API local,
upload, jobs, historico e configuracao em um unico arquivo, deve ser mantido
com cautela e e candidato natural a refatoracao futura em modulos menores.

## 6. Validacao, Demo e Empacotamento

| Script | Funcao principal | Status |
|---|---|---|
| `scripts/97_make_demo_fastq.py` | Gera reads sinteticas para teste demonstrativo. | **Ativo / demo** |
| `scripts/90_smoke_test.sh` | Smoke test do ambiente e componentes essenciais. | **Ativo / teste** |
| `scripts/91_verify_demo_outputs.sh` | Verifica artefatos esperados do demo. | **Ativo / teste** |
| `scripts/tests/run_test_suite.sh` | Separa suítes de engenharia, operacional e reprodutível; ponto canônico de `make test*`. | **Ativo / teste canônico** |
| `scripts/tests/verify_locked_runtime.py` | Compara o ambiente Conda ativo com todas as versões/builds do lock. | **Ativo / qualificação de runtime** |
| `scripts/tests/run_smoke_test.sh` | Smoke alternativo legado, dependente de PTV/rede e fora de `make test`. | **Legacy operacional** |
| `scripts/30_benchmark_preliminar.py` | Compara resultados preliminares entre montadores. | **Ativo / validacao** |
| `scripts/98_build_bundle_wsl.sh` | Monta pacote bundle para distribuicao WSL. | **Ativo / release** |
| `scripts/99_test_bundle_wsl.sh` | Testa integridade do bundle WSL. | **Ativo / release** |
| `scripts/99_install_deps.sh` | Instalador tecnico de dependencias do ambiente local. | **Ativo / suporte** |

## 7. Experimental e Legacy

| Script | Funcao principal | Status |
|---|---|---|
| `scripts/21_run_advanced_analysis.sh` | Analises pos-pipeline com MAFFT/IQ-TREE/FastTree. | **Experimental** |
| `scripts/legacy/align_ptv_fragments.sh` | Alinhamento multiplo de fragmentos PTV. | **Legacy** |
| `scripts/legacy/align_ptv_region.sh` | Alinhamento de regiao especifica de PTV. | **Legacy** |
| `scripts/legacy/tree_ptv_fragments_iqtree.sh` | Arvore filogenetica de fragmentos. | **Legacy** |
| `scripts/legacy/tree_ptv_region_iqtree.sh` | Arvore filogenetica de regiao. | **Legacy** |
| `scripts/legacy/run_ptv_advanced.sh` | Orquestrador antigo do fluxo avancado. | **Legacy** |
| `scripts/legacy/extend_plan.py` | Planejamento antigo de extensao de flancos. | **Legacy** |
| `scripts/legacy/emit_extend_fasta.py` | Emissao antiga de FASTA de flancos. | **Legacy** |
| `scripts/legacy/sim_reads_clean.py` | Simulacao antiga de reads sinteticos de flanco. | **Legacy** |
| `scripts/legacy/collect_ptv_contigs.py` | Coleta antiga de contigs PTV. | **Legacy** |
| `scripts/legacy/build_ptv_region_fasta.py` | Construcao antiga de FASTA de regioes PTV. | **Legacy** |
| `scripts/legacy/emit_ptv_hit_fragments.py` | Emissao antiga de fragmentos a partir de BLAST. | **Legacy** |
| `scripts/legacy/merge_report.py` | Mesclagem antiga de relatorios. | **Legacy** |

Scripts legacy permanecem preservados apenas como historico tecnico. Eles nao
fazem parte do fluxo oficial, nao devem ser usados em tutoriais de usuario
final e podem ser removidos em uma versao futura se nao houver justificativa
metodologica para sua manutencao.
