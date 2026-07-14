# Diretrizes de Validação Científica e Interpretação de Resultados

Este documento estabelece as bases teóricas, as limitações metodológicas e os critérios biológicos que orientam a validação científica dos fragmentos recuperados pelo pipeline **Gene-In 1.1**.

---

## 1. O Desafio de Fragmentos Curtos em Baixa Carga Viral

Em amostras clínicas ou ambientais com baixa carga viral, o material genético do vírus de interesse pode se encontrar altamente fragmentado e em baixa concentração relativa se comparado ao material celular do hospedeiro e da microbiota acompanhante. Em metagenômica clínica, filtros rígidos de montagem frequentemente descartam leituras individuais ou contigs de pequeno comprimento para evitar falsos positivos.

Contudo, para vírus de genoma reduzido (como os picornavírus), trechos curtos de sequenciamento contêm informações filogenéticas cruciais (como regiões do gene VP1). O Gene-In atua de forma sensível na recuperação desses fragmentos.

**O perigo biológico:** Fragmentos curtos (especialmente entre 20 e 49 pb) possuem menor complexidade estatística. Isso significa que a probabilidade de alinhamento ao acaso com regiões do hospedeiro, outros microrganismos ou contaminantes ambientais é significativamente maior. Portanto, a identificação baseada exclusivamente em homologia de fragmentos pequenos exige interpretação cautelosa e validação experimental complementar.

---

## 2. Níveis de Evidência e Classificação Operacional

Para organizar o processo de curadoria, o pipeline agrupa os contigs e fragmentos em cinco classes de evidência operacional. **Atenção:** Estes níveis não representam diagnósticos definitivos, mas sim categorias de priorização analítica.

| Classe | Comprimento (pb) | pident (%) | adj_identity (%) | e-value | bitscore | Significado Técnico |
|---|---:|---:|---:|---:|---:|---|
| `STRONG` | `>= 80` | `>= 90` | `>= 70` | `<= 1e-10` | — | **Forte evidência de homologia:** Alta similaridade e cobertura de alinhamento. Adequada para análises de posicionamento filogenético. |
| `STRONG_DIVERGENT` | `>= 1000` (ou alinhamento) | `80–89` | (cobertura `>= 80%`) | `<= 1e-10` | — | **Variante divergente forte:** Contig longo com excelente cobertura de alinhamento mas identidade moderada. Candidato forte a variante divergente. |
| `MODERATE` | `50–79` | `>= 85` | `>= 60` | `<= 1e-5` | — | **Evidência sugestiva:** Tamanho ou identidade moderados. Deve ser analisada em conjunto com o contexto clínico/biológico da amostra. |
| `WEAK_RECOVERABLE` | `20–49` | `>= 90` | — | — | `>= 35` | **Evidência fraca recuperável:** Alta identidade em região muito curta. Alto risco de falso positivo. Exige curadoria manual obrigatória. |
| `REVIEW` | Demais casos | — | — | — | — | **Revisão obrigatória:** Hits com parâmetros fora dos limiares estabelecidos. Devem ser inspecionados para identificar homologia parcial ou artefatos. |

---

## 3. A Métrica Operacional `adj_identity`

O Gene-In calcula e reporta a métrica `adj_identity` (Identidade Ajustada) para refinar a classificação de similaridade:

\[\text{adj\_identity} = \text{pident} \times \left( \frac{\text{aln\_len}}{\text{qlen}} \right)\]

Onde:
*   `pident` (\% de identidade de nucleotídeos) representa a proporção de bases idênticas no alinhamento.
*   `aln_len` (comprimento do alinhamento) é o número de posições alinhadas.
*   `qlen` (comprimento total da query) é o tamanho total da sequência gerada pelo pipeline.

**Nota Científica:** A `adj_identity` é uma **métrica operacional interna do pipeline** que atua como um fator de ponderação da identidade de sequência em relação à cobertura física do alinhamento. Ela impede que uma sequência curta com 100\% de identidade local receba prioridade se o alinhamento cobrir apenas uma fração mínima do contig gerado. **Ela não deve ser descrita em publicações ou artigos científicos como uma métrica universal ou padronizada da literatura**, mas sim explicitada como um critério bioinformático operacional próprio do fluxo do Gene-In.

---

## 4. Evidência, Sugestão e Confirmação

Para fins acadêmicos e publicação de resultados, o pesquisador deve rigorosamente distinguir três níveis de conclusão:

1.  **Evidência Compatível (Bioinformática):** Indica apenas que o algoritmo identificou uma sequência de nucleotídeos na amostra que apresenta homologia estatisticamente significativa com o banco de referência fornecido.
2.  **Resultado Sugestivo:** Quando múltiplos contigs classificados como `STRONG` ou `MODERATE` mapeiam regiões distintas do genoma do patógeno alvo, fortalecendo a hipótese de presença viral na amostra.
3.  **Confirmação Biológica/Clínica:** A confirmação definitiva de infecção viral exige necessariamente a convergência com dados clínicos, isolamento viral, detecção de antígenos ou amplificação por métodos independentes de referência (como RT-qPCR ou sequenciamento Sanger direcionado). O pipeline bioinformático isolado não confirma infecção.

---

## 5. Protocolo de Controle Experimental Recomendado

Qualquer análise de baixa carga viral é extremamente sensível a contaminações cruzadas e ruídos ambientais. Portanto, para validar cientificamente os achados, recomenda-se:

*   **Controle Negativo de Extração e Sequenciamento (Mock):** Processar paralelamente uma amostra sem material genético viral. Hits de similaridade viral detectados no controle negativo indicam contaminação sistemática ou falhas de I/O de dados, invalidando os resultados de baixa carga da mesma corrida.
*   **Controle Positivo (Benchmark):** Uso de um controle com carga controlada do vírus alvo para verificar a sensibilidade de recuperação física do pipeline e calibração das taxas de k-mer e parâmetros de montagem.

---

## 6. Reprodutibilidade e Registro de Metadados do Banco

A sensibilidade do pipeline é diretamente influenciada pelo banco de dados de referência utilizado. Para garantir a reprodutibilidade da metodologia de análises e publicações científicas, deve-se **documentar detalhadamente**:

*   **Data exata de download** das referências virais.
*   **Queries de busca** utilizadas no NCBI ou em outras fontes (ex: filtros taxonômicos).
*   **Tamanho total do banco** (número de sequências e volume total de nucleotídeos).
*   **Critérios de curadoria** aplicados para inclusão/exclusão de sequências do banco customizado.

Bancos direcionados (ex: compostos exclusivamente por um sorotipo específico) aumentam a sensibilidade para aquele alvo, mas introduzem viés sistemático de mapeamento e podem falhar na triagem de variantes divergentes.

---

## 7. Diretrizes para Apresentação de Resultados Bioinformáticos

Ao redigir a seção de resultados e discussão de relatórios ou publicações, recomenda-se adotar as seguintes práticas:

*   **Tabelas de Hits:** Apresente os hits estruturados incluindo: identificador do contig, comprimento (pb), `pident`, `e-value`, cobertura do alinhamento e a classificação de evidência operacional (`STRONG`, `MODERATE`, etc.). Explicite no texto de suporte que a classificação é operacional.
*   **Linguagem Defensiva:** Evite afirmações definitivas como "o pipeline detectou infecção por PTV na amostra". Prefira formulações mais precisas, como: "o pipeline recuperou contigs com homologia de sequência compatível com *Teschovirus A*".
*   **Validação Filogenética:** Apresente árvores filogenéticas inferidas (ex: pelo IQ-TREE 2) a partir dos contigs selecionados juntamente com as referências, exibindo claramente o suporte de ramos (valores de bootstrap) e delimitando a região genômica correspondente (ex: VP1).
