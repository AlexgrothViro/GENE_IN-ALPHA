# Manual do Usuário e Guia de Execução

Este manual descreve em detalhes como configurar, executar e analisar os resultados do pipeline **Gene-In 1.1** a partir da linha de comando, distinguindo os cenários de teste controlado (demo) e aplicação prática com amostras reais.

---

## 1. Verificação Prévia do Ambiente

Antes de iniciar qualquer análise, certifique-se de que o ambiente de execução e suas dependências científicas estejam configurados corretamente:

```bash
# Executa os scripts de diagnóstico de ambiente
make test-env

# Instala/atualiza as dependências científicas locais
make deps
```

---

## 2. Execução com o Modo Demo (Sintético)

O modo de demonstração serve para validar o pipeline e certificar-se de que todas as etapas de montagem e triagem estão funcionando conforme o esperado, utilizando leituras sintéticas baseadas no próprio genoma de referência.

```bash
# 1. Gerar os arquivos FASTQ sintéticos do demo (salvos em data/raw/DEMO_R1.fastq.gz e data/raw/DEMO_R2.fastq.gz)
make demo

# 2. Configurar o banco de dados viral padrão (PTV)
make db DB=ptv

# 3. Executar o pipeline completo na amostra DEMO
make run-demo

# 4. Validar a presença de todas as saídas esperadas
make test-demo SAMPLE=DEMO
```

---

## 3. Execução com Amostra Real

Para analisar dados de sequenciamento reais (FASTQ) gerados em laboratório:

### Opção A: Execução em Comando Único (Staging + Execução)
Esta abordagem automatiza todo o processo em um único comando:

```bash
make run SAMPLE=<identificador_amostra> \
  R1=/caminho/reads_R1.fastq.gz \
  R2=/caminho/reads_R2.fastq.gz \
  DB=ptv
```

### Opção B: Controle Passo a Passo (Manual)
Indicado para depuração e controle individual de cada etapa:

```bash
# 1. Staging: Registra os arquivos de leitura no diretório de trabalho data/raw
make sample-add ID=<id> R1=<caminho/R1.fastq.gz> R2=<caminho/R2.fastq.gz>

# 2. Preparação do Banco de Referência
make db DB=ptv

# 3. Execução das Etapas do Pipeline (Montagem + Triagem BLAST)
make pipeline SAMPLE=<id>

# 4. Geração do Relatório Resumido
make report SAMPLE=<id>
```

---

## 4. Escolha do Montador de Contigs

O Gene-In suporta Velvet, SPAdes e metaSPAdes. O pipeline permite configurar parâmetros de k-mer adequados a cada montador para gerenciar a sensibilidade e a fragmentação:

```bash
# Executar com Velvet (montador padrão)
make pipeline SAMPLE=<id> ASSEMBLER=velvet

# Executar com SPAdes
make pipeline SAMPLE=<id> ASSEMBLER=spades

# Executar com metaSPAdes (indicado para metagenômica complexa)
make pipeline SAMPLE=<id> ASSEMBLER=metaspades
```

*Nota:* No Velvet, os parâmetros de k-mer são controlados localmente no pipeline. No SPAdes/metaSPAdes, o pipeline adota montagem multi-k utilizando os k-mers configurados em `config/picornavirus.env`.

---

## 5. Configuração e Criação de Bancos de Referência

O pipeline pode utilizar perfis de bancos pré-configurados ou bancos customizados definidos pelo pesquisador.

### Uso de Bancos Padrão (Catálogo Pré-configurado)
O Gene-In inclui um catálogo de alvos virais definidos no arquivo `config/targets.json`. Para construir ou atualizar qualquer um deles:

```bash
make db DB=ptv         # Porcine teschovirus A
make db DB=evg         # Enterovirus G
make db DB=psv         # Sapelovirus A
make db DB=svv         # Senecavirus A
make db DB=fmdv        # Foot-and-mouth disease virus

# Listar todos os perfis cadastrados
make db-list
```

### Práticas Recomendadas para Preparação de Bancos Customizados
Ao criar um banco direcionado para novos alvos virais, siga estas diretrizes:
1.  **Curadoria de Sequências:** Obtenha os arquivos FASTA contendo sequências completas ou representativas do táxon de interesse a partir de fontes curadas (como NCBI RefSeq ou VIPR).
2.  **Exclusão de Falsos Alvos:** Certifique-se de remover sequências que contenham contaminantes biológicos conhecidos ou adaptadores de sequenciamento para evitar hits espúrios.
3.  **Documentação de Metadados:** Salve a lista de números de acesso (Accession Numbers) e registre a data de download e o tamanho do arquivo FASTA.

---

## 6. Interpretação dos Relatórios e Saídas

Após a conclusão da execução, os resultados relevantes encontram-se estruturados nos seguintes arquivos:

*   **`results/reports/{SAMPLE}_summary.md`**: Contém a tabela final resumida de hits identificados e classificados por similaridade, além de estatísticas básicas de montagem.
*   **`results/blast/{SAMPLE}_labeled_hits.tsv`**: tabela histórica de compatibilidade; suas classes são `legacy_label` e têm teto público E1. O artefato canônico é `sample_evidence.json`.
*   **`results/blast/{SAMPLE}_adj_identity.tsv`**: Resultados contendo os cálculos da métrica de identidade ajustada (`adj_identity`).

> **Resultados anteriores à Alpha.2:** execuções Evidence V2 antigas são preservadas para auditoria, mas aparecem como `LEGACY_INCOMPATIBLE`/`NOT_EVALUABLE`. Elas não são convertidas automaticamente. Reexecute a análise com `2.0.0-alpha.2` para gerar os TSVs, `sample_evidence.json`, manifesto e `SUCCESS.json` compatíveis.

### Cuidados e Critérios Críticos Antes de Reportar Resultados:
*   **Diferença entre Triagem e Confirmação:** Lembre-se sempre de que os hits identificados representam similaridade sequencial e homologia provável, nunca um diagnóstico clínico conclusivo.
*   **Revisão Obrigatória de Fragmentos Curtos:** Fragmentos marcados como `WEAK_RECOVERABLE` ou `REVIEW` devem ter seus alinhamentos brutos examinados manualmente (por exemplo, inspecionando os valores de cobertura e e-value no arquivo `results/blast/{SAMPLE}_vs_db.tsv`) para descartar homologia não-específica ou contaminação biológica.
*   **Validação por Controles:** Não publique ou reporte resultados de amostras sem verificar se o controle negativo da corrida de sequenciamento está livre de hits semelhantes do mesmo vírus.
