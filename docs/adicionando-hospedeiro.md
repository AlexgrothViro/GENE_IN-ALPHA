# Adicionando outro hospedeiro ao Gene-In

O filtro de hospedeiro remove reads que alinham contra um indice Bowtie2 antes da montagem e do BLAST viral. O comportamento padrao continua sendo `Sus scrofa`, mas o mesmo fluxo pode usar outro hospedeiro ou ser desativado quando a amostra ja foi filtrada fora do Gene-In.

## Variaveis principais

Edite `config/picornavirus.env` ou envie as variaveis pelo ambiente antes de executar o pipeline.

```bash
HOST_FILTER_ENABLED=true
HOST_NAME="Sus scrofa"
HOST_ACCESSION="GCF_000003025.6"
HOST_INDEX_PREFIX="${REPO_ROOT}/ref/host/sus_scrofa_bt2"
```

`HOST_FILTER_ENABLED` controla se o Bowtie2 sera chamado. Use `false` para pular completamente a etapa.

`HOST_NAME` e o rotulo exibido nos logs e no dashboard.

`HOST_ACCESSION` e o accession RefSeq/GenBank usado por `scripts/11_prepare_host_reference.sh` para baixar a referencia pelo NCBI Datasets.

`HOST_INDEX_PREFIX` e o prefixo do indice Bowtie2, sem a extensao `.bt2` ou `.bt2l`.

## Preparar uma referencia

Depois de ajustar as variaveis, rode:

```bash
bash scripts/11_prepare_host_reference.sh
```

O script baixa o genoma pelo NCBI Datasets, valida checksums quando o manifesto esta disponivel e constroi o indice Bowtie2 no prefixo definido por `HOST_INDEX_PREFIX`.

Para forcar a reconstrucao de um indice existente:

```bash
HOST_REBUILD_INDEX=true bash scripts/11_prepare_host_reference.sh
```

O Bowtie2 escolhe automaticamente entre indice `.bt2` de 32 bits e `.bt2l` de 64 bits conforme o tamanho da referencia. Nao e necessario configurar isso manualmente no Gene-In.

## Exemplo com outro hospedeiro

Exemplo usando bovino como hospedeiro:

```bash
HOST_FILTER_ENABLED=true
HOST_NAME="Bos taurus"
HOST_ACCESSION="GCF_002263795.3"
HOST_INDEX_PREFIX="${REPO_ROOT}/ref/host/bos_taurus_bt2"
```

Depois:

```bash
bash scripts/11_prepare_host_reference.sh
bash scripts/20_run_pipeline.sh --sample minha_amostra --assembler spades --kmer 31
```

No dashboard, escolha `Indice Bowtie2 customizado`, informe `Bos taurus` como nome e `ref/host/bos_taurus_bt2` como prefixo.

## Usar sem filtro de hospedeiro

Use o modo sem filtro quando os FASTQs ja foram pre-filtrados por outro pipeline, quando o hospedeiro biologico e desconhecido ou quando voce quer testar o impacto da filtragem na sensibilidade do resgate viral.

No config:

```bash
HOST_FILTER_ENABLED=false
```

Ou no dashboard, selecione `Sem filtro de hospedeiro`.

Nesse modo o pipeline nao chama Bowtie2 e segue para a montagem com as reads da etapa anterior.
