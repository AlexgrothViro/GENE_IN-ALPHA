# Estado de validação do Gene-In 2.0 alpha.2

Este documento separa código implementado, testes com fixtures/mocks e validação com ferramentas científicas reais. A Evidence V2 continua em `shadow_mode=true`; a versão 1.1 permanece oficial e inalterada.

| Área | Implementado | Fixture/mock | Ferramenta real | Estado |
|---|---:|---:|---:|---|
| União de HSPs, identidade e loci | sim | sim | pendente | identidade de referência/categoria/locus preservada |
| Especificidade competitiva | sim | sim | pendente | alvo/competidor na mesma tarefa e banco |
| Preflight do runtime | sim | sim | pendente | bloqueia V2 quando PyYAML/ferramenta falta |
| Estado e handoff 1.1/V2 | sim | sim | pendente | status oficial e experimental separados |
| Transação de run individual | sim | sim | pendente | staging, manifesto com hash, sincronização e `SUCCESS.json` por último |
| Painel competitivo | sim | parcial | pendente | BLAST/Bowtie2 reais ainda não validados neste host |
| Remapeamento/cobertura | sim | parcial | pendente | métricas por candidato; Bowtie2, samtools e UMI-tools reais pendentes |
| Lotes e controles | sim | sim | pendente | RPM e estados de controle sem veredito automático |
| Gates filogenéticos | sim | sim | pendente | somente colunas cobertas pelo candidato; IQ-TREE real pendente |
| Dashboard/API V2 | sim | sim | estado legado verificado localmente | `LEGACY_INCOMPATIBLE`/`NOT_EVALUABLE` renderizado sem erros de console |
| Scripts legados | isolados | sim | pendente | `LEGACY / TEST-ONLY`, sem migração automática |
| Benchmark científico | gerador determinístico | sim | bloqueado | somente fixtures/dados formalmente autorizados |
| Usabilidade | roteiro/interface | pendente | pendente | três perfis ainda precisam testar localmente |

## Verificações executadas neste snapshot

- 73 testes Python determinísticos aprovados neste host.
- As regressões Alpha.2 listadas em `docs/REMEDIATION_MATRIX.md` passaram em fixtures locais.
- `py_compile` dos módulos Python e `node --check dashboard/app.js` aprovados.
- `bash -n` aprovado para 49 scripts rastreados com Git Bash; ShellCheck e execução Linux/WSL real continuam pendentes.
- Preflight executado com o Python efetivo do dashboard: identificou PyYAML ausente e `spades.py` ausente, gerando relatório JSON inválido para impedir a V2.
- Upload de FASTQ validado com gzip, estrutura, comprimento e pareamento; duplicata retorna conflito.
- Artefatos transacionais rejeitam staging incompleto, cabeçalhos TSV inválidos e JSON V2 incompleto.
- O fixture Alpha.2 completo passa no validador com manifesto e hashes; as duas execuções Alpha.1 históricas são rejeitadas e preservadas para auditoria.
- O legado ganhou caminhos derivados do repositório, workdir isolado padrão e contratos de teste.

## Bloqueios para validação Linux/WSL

- Não há distribuição WSL instalada neste host; ShellCheck e execução Linux real continuam pendentes.
- O Python nativo não possui PyYAML; não foi instalado automaticamente nem foi criado ambiente falso.
- BLAST+, Bowtie2, samtools, SPAdes/metaSPAdes, UMI-tools e IQ-TREE reais não foram declarados validados neste host.
- Um repositório Git local foi inicializado na branch `main`; remoto, tag e publicação no GitHub continuam pendentes.
- `environment-linux-64.lock.txt` só deve ser gerado a partir do ambiente Linux efetivamente validado.

## Regra sobre dados operacionais

A execução operacional fora do conjunto científico formal permanece excluída de benchmark, calibração, artigo, dissertação, tabelas finais, relatórios de validação e interpretação científica. As pastas externas inventariadas também não são assumidas como FASTQ válido sem importação, validação e autorização formal.
