# Estado de validação do Gene-In 2.0 alpha.2

Este documento separa código implementado, testes com fixtures/mocks e validação com ferramentas científicas reais. A Evidence V2 continua em `shadow_mode=true`; a versão 1.1 permanece oficial e inalterada.

| Área | Implementado | Fixture/mock | Ferramenta real | Estado |
|---|---:|---:|---:|---|
| União de HSPs, identidade e loci | sim | sim | BLAST+ sintético parcial | identidade de referência/categoria/locus preservada |
| Especificidade competitiva | sim | sim | BLAST+ sintético parcial | alvo/competidor na mesma tarefa e banco |
| Preflight do runtime | sim | sim | executado em WSL não qualificado pelo lock | bloqueia V2 quando PyYAML/ferramenta falta |
| Estado e handoff 1.1/V2 | sim | sim | pendente | status oficial e experimental separados |
| Transação de run individual | sim | sim | pendente | staging, manifesto com hash, sincronização e `SUCCESS.json` por último |
| Painel competitivo | sim | parcial | BLAST+ real sintético | painel alvo/host exercitado; ambiente diverge do lock |
| Remapeamento/cobertura | sim | parcial | Bowtie2/samtools parciais | filtro de hospedeiro real exercitado; UMI-tools real permanece pendente |
| Lotes e controles | sim | sim | pendente | RPM e estados de controle sem veredito automático |
| Gates filogenéticos | sim | sim | pendente | somente colunas cobertas pelo candidato; IQ-TREE real pendente |
| Dashboard/API V2 | sim | sim | navegador local | estados válido/incompleto/sem candidatos e downloads verificados |
| Montagem | sim | sim | Velvet/SPAdes/metaSPAdes sintéticos | três montadores executados; versões locais divergem do lock |
| Scripts legados | isolados | sim | pendente | `LEGACY / TEST-ONLY`, sem migração automática |
| Benchmark científico | gerador determinístico | sim | bloqueado | somente fixtures/dados formalmente autorizados |
| Usabilidade | roteiro/interface | pendente | pendente | três perfis ainda precisam testar localmente |

## Verificações executadas neste snapshot

- `make test` executa a suíte de engenharia canônica: testes Python, regressões shell controladas, `bash -n`, `compileall` e `node --check`.
- A execução final do B8 aprovou 154 testes Python no WSL, sem skips, além das regressões shell controladas. A suíte percorre cada comprimento inteiro de 20 a 100 bp.
- As regressões Alpha.2 listadas na matriz de remediação interna passaram em fixtures locais.
- WSL está disponível. Testes operacionais passaram com fastp, Bowtie2, samtools, BLAST+, Velvet, SPAdes e metaSPAdes reais sobre dados sintéticos.
- A suíte operacional aprovou 11 testes de QC/hospedeiro e os smokes reais de BLAST+, Velvet, SPAdes e metaSPAdes, sem skips.
- O preflight local registrou Python 3.12.3, PyYAML 6.0.1, fastp 0.23.4, Bowtie2 2.5.2, samtools 1.19.2, BLAST+ 2.12.0+ e SPAdes/metaSPAdes 3.15.5.
- O lock explícito possui 156 entradas e SHA-256 `a916e8c05052269ab89eb6599610f9dcd7818b61233c5c196d623ab316fcd14b`.
- O ambiente WSL ativo não possui `CONDA_PREFIX` e, portanto, não é qualificado como idêntico ao lock.
- Upload de FASTQ validado com gzip, estrutura, comprimento e pareamento; duplicata retorna conflito.
- Artefatos transacionais rejeitam staging incompleto, cabeçalhos TSV inválidos e JSON V2 incompleto.
- O fixture Alpha.2 completo passa no validador com manifesto e hashes; as duas execuções Alpha.1 históricas são rejeitadas e preservadas para auditoria.
- O legado ganhou caminhos derivados do repositório, workdir isolado padrão e contratos de teste.

## Bloqueios para validação reprodutível e científica

- O WSL e várias ferramentas reais estão disponíveis, mas vieram do ambiente local e divergem das versões/builds do lock.
- `make test-reproducible` abstém-se enquanto não houver `CONDA_PREFIX` com as 156 versões/builds exatas.
- UMI-tools, IQ-TREE, controles completos e filogenia real não foram incluídos na suíte operacional B8.
- O gate ShellCheck completo não concluiu dentro de 184 segundos nesta árvore em `/mnt/c`; os scripts shell do B8 e os testes chamados por eles passaram isoladamente.
- Não foi executado benchmark científico congelado com métricas pré-especificadas nem repetição independente.
- Um repositório Git local foi inicializado na branch `main`; remoto, tag e publicação no GitHub continuam pendentes.
- `environment-linux-64.lock.txt` só deve ser gerado a partir do ambiente Linux efetivamente validado.

## Regra sobre dados operacionais

A execução operacional fora do conjunto científico formal permanece excluída de benchmark, calibração, artigo, dissertação, tabelas finais, relatórios de validação e interpretação científica. As pastas externas inventariadas também não são assumidas como FASTQ válido sem importação, validação e autorização formal.
