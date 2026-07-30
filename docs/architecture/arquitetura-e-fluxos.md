# Arquitetura e fluxos

## Baselines

### Gene-In 1.1

Fluxo histórico/estável de montagem, BLAST, métricas locais, classes operacionais e relatório. Serve para compatibilidade e documentação pública, mas não define sozinho a arquitetura científica da Evidence V2.

Pontos históricos:

- entrada FASTQ pareada;
- QC e filtro opcional do hospedeiro;
- Velvet, SPAdes ou metaSPAdes;
- BLASTn/`blastn-short`;
- `adj_identity`;
- classes operacionais locais;
- TSV, Markdown e logs.

### Evidence V2 / 2.0.0-alpha.2

Camada experimental que agrega evidência, aplica gates, separa estados e produz artefatos científicos estruturados. É a referência para revisar código novo.

## Fluxo lógico esperado

1. Preflight valida ambiente e dependências.
2. Uma execução recebe identidade própria e diretório temporário.
3. Entradas, configuração, banco e ferramentas têm proveniência registrada.
4. QC, montagem/resgate e busca por similaridade geram artefatos intermediários.
5. HSPs são agregados sem redundância.
6. Especificidade competitiva, reads, cobertura, controles e loci são avaliados.
7. Gates versionados definem o resultado V2 ou a abstenção.
8. Artefatos são validados antes da promoção atômica.
9. Dashboard e relatórios apenas apresentam o resultado canônico.

## Sidecars e análises auxiliares

Ferramentas auxiliares devem executar em transação independente após a Evidence V2. Elas podem exibir, validar ou sintetizar artefatos, mas não:

- modificar o diretório científico já validado;
- recalcular a decisão canônica;
- promover evidência;
- transformar achado auxiliar em conclusão pública.

Host screening, filogenia, variantes, recombinação e síntese interpretativa devem ser tratados como consumidores/sidecars com estados e limitações próprios.

## Preflight conhecido

O preflight deve verificar, conforme o modo configurado:

- Python correto e PyYAML;
- BLAST+;
- Bowtie2;
- samtools;
- fastp;
- montador selecionado;
- UMI-tools quando solicitado;
- IQ-TREE quando filogenia for elegível.

Uma dependência ausente deve produzir erro explícito ou limitação formal prevista pela política. Não deve causar fallback silencioso.

## Transacionalidade

- Diretório de trabalho por `run_id`.
- Logs exclusivos por execução.
- Cancelamento alcança o grupo de processos.
- Validação de schema e artefatos antes da promoção.
- `rename` atômico quando suportado.
- Execução anterior válida preservada até o novo sucesso.
- Falha parcial não aparece como execução concluída.
- Concorrência não mistura arquivos de duas execuções.
