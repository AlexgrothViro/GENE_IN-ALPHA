# Gene-In

O **Gene-In** é um pipeline bioinformático estruturado para recuperar e priorizar fragmentos virais em dados de sequenciamento de alto rendimento provenientes de amostras clínicas ou metagenômicas complexas com baixa carga viral.

---

## 1. Principais Características

*   **Identidade Ajustada:** Algoritmo estatístico que calcula a identidade de sequência ajustada (`adj_identity`), mitigando o viés de alinhamentos muito curtos de alta identidade.
*   **Classificação em 5 Classes Operacionais:** Separação de hits bioinformáticos em categorias de rigor científico (`STRONG`, `STRONG_DIVERGENT`, `MODERATE`, `WEAK_RECOVERABLE`, `REVIEW`).
*   **Modo de Resgate de Leituras (Read-level Rescue):** Ativação automática de busca direta por similaridade em reads individuais (`READ_LEVEL_SIGNAL`) caso os processos de montagem falhem por cobertura insuficiente extrema.
*   **Dashboard Interativo:** Painel web local em Python para parametrização visual, monitoramento de execuções de pipeline em tempo real e visualização de relatórios científicos formatados.

---

## 2. Para quem é?

O Gene-In foi projetado para:
*   Pesquisadores, biólogos e bioinformatas que investigam a virosfera em amostras de NGS de baixa cobertura.
*   Laboratórios de diagnóstico e vigilância epidemiológica veterinária que desejam automatizar pipelines de triagem sem dependência exclusiva de linha de comando.

---

## 3. O que explicitamente NÃO é e NÃO faz?

> [!IMPORTANT]
> **Atenção às Limitações Científicas e de Escopo:**
> *   **NÃO é um software de diagnóstico clínico:** A classificação do Gene-In é puramente bioinformática, baseada em homologia de sequência primária. Não fornece laudos de diagnóstico clínico de infecção viral ativa.
> *   **NÃO confirma viabilidade ou replicação viral:** A presença de leituras ou contigs classificados como `STRONG` ou `MODERATE` indica apenas homologia de sequências de ácidos nucleicos presentes na amostra física e não garante a atividade de replicação ou patogenicidade.
> *   **Exige curadoria e controles científicos:** Resultados obtidos de baixíssima cobertura biológica (como em `WEAK_RECOVERABLE`) podem refletir contaminações cruzadas de laboratório, ruído basal de sequenciamento ou sequências conservadas do hospedeiro. É obrigatório o uso concomitante de controles negativos reais e a validação experimental ortogonal (ex: RT-qPCR).
> *   **Viés do Banco de Referência:** A sensibilidade de detecção está atrelada à diversidade de sequências contidas no banco configurado no pipeline. Bancos incompletos ou desatualizados podem gerar falsos negativos para linhagens virais muito divergentes.

---

## 4. Status de Validação

O Gene-In foi validado com base em dados reais de sequenciamento de alto rendimento públicos correspondentes a picornavírus suínos de interesse depositados publicamente no NCBI SRA (Sequence Read Archive), além de controles negativos e amostras de background.

*   **Especificidade:** Demonstrou alta especificidade analítica e controle de sinais de background no sequenciamento, sem produzir candidatos de alta prioridade em amostras de controle negativo.
*   **Sensibilidade:** Recuperação bem-sucedida de genomas parciais a completos em amostras biológicas positivas contendo baixa a moderada carga viral, com acionamento robusto de cadeia de fallback e resgate de leituras individuais.
*   Diretrizes adicionais para interpretação dos resultados e calibração estão descritas em `docs/VALIDACAO_CIENTIFICA.md`. Detalhes metodológicos e estatísticos complementares da validação científica serão disponibilizados mediante a publicação associada.

---

## 5. Instalação e Uso Rápido

### Requisitos
*   Sistema Linux ou ambiente Windows WSL2 (Ubuntu 22.04 LTS recomendado).
*   Gerenciador de pacotes Conda ou Mamba.

Para instalacao em Windows novo ou computador com permissoes restritas, consulte tambem `docs/GUIA_RAPIDO_WINDOWS.md`, que lista as permissoes de administrador, WSL/Ubuntu, `sudo`, internet e portas locais que precisam estar liberadas.

### Passo a Passo de Configuração
1.  **Instalar dependências via Conda:**
    ```bash
    conda env create -f environment.yml
    conda activate gene-in
    ```
2.  **Preparar bancos de referência (ex: Teschovirus A - ptv):**
    ```bash
    make db DB=ptv
    ```
3.  **Iniciar o Dashboard Web:**
    ```bash
    python3 scripts/ux_dashboard.py
    ```
    Abra no seu navegador o endereço: [http://localhost:8000](http://localhost:8000).

### Execução em Linha de Comando (CLI)
Para controle de granularidade do pipeline:
```bash
# 1. Adicionar FASTQs de entrada
make sample-add ID=teste_ptv R1=data/raw/demo_R1.fastq.gz R2=data/raw/demo_R2.fastq.gz

# 2. Executar pipeline principal com montador spades
make pipeline SAMPLE=teste_ptv ASSEMBLER=spades

# 3. Gerar relatório resumido
make report SAMPLE=teste_ptv
```

---

## 6. Como Interpretar a Saída (Classes Operacionais)

Os hits obtidos pelo pipeline de BLAST contra a referência viral são categorizados e exportados em `results/blast/{SAMPLE}_labeled_hits.tsv` conforme a tabela de evidência a seguir:

| Classe de Evidência | Critério Bioinformático Principal | Significado Científico | Ação Recomendada |
|---|---|---|---|
| `STRONG` | Comp. $\ge 80$ pb, pident $\ge 90\%$, adj_identity $\ge 70\%$, e-value $\le 10^{-10}$ | Forte evidência de homologia viral. Contig longo e bem alinhado. | Priorizar contig para análises filogenéticas detalhadas. |
| `STRONG_DIVERGENT` | Comp. ou qlen $\ge 1000$ pb, aln_cov $\ge 80\%$, $80\% \le$ pident $< 90\%$, e-value $\le 10^{-10}$ | Evidência forte de variante divergente ou nova linhagem. | Priorizar para caracterização molecular e anotação manual. |
| `MODERATE` | Comp. $50-79$ pb, pident $\ge 85\%$, adj_identity $\ge 60\%$, e-value $\le 10^{-5}$ | Evidência intermediária de homologia viral. | Analisar contexto taxonômico e similaridades acessórias. |
| `WEAK_RECOVERABLE` | Comp. $20-49$ pb, pident $\ge 90\%$, bitscore $\ge 35$ | Hits muito curtos, porém idênticos. Risco de falso-positivo. | Exige cuidadosa revisão manual contra bancos gerais para descartar artefatos. |
| `REVIEW` | Não atende aos critérios acima, mas possui sinal residual. | Sinal inconclusivo ou indeterminado. | Revisar alinhamentos brutos para descartar/confirmar homologia parcial. |

---

## 7. Estrutura do Repositório

```text
Gene-In/
+-- Makefile                   # Automação das etapas do pipeline
+-- README.md                  # Este documento
+-- LICENSE                    # Licença pública limitada de uso
+-- environment.yml            # Definição do ambiente Conda/Mamba
+-- config/
│   +-- picornavirus.env.example # Template de variáveis de ambiente
│   +-- targets.json           # Definição de acessões virais padrão
+-- scripts/
│   +-- 00_import_sample.sh    # Script de importação local
│   +-- 20_run_pipeline.sh     # Pipeline principal de execução
│   +-- ux_dashboard.py        # Dashboard web local em Python
│   +-- tests/
│   │   +-- run_smoke_test.sh  # Script de teste de fumaça (smoke test) sintético
│   +-- lib/                   # Bibliotecas Python e Bash compartilhadas
+-- docs/
│   +-- VALIDACAO_CIENTIFICA.md # Diretrizes de validação científica e interpretação
│   +-- TROUBLESHOOTING.md     # Solução de falhas e problemas comuns
│   +-- USABILITY_CHECKLIST.md # Checklist manual de usabilidade do painel web
+-- data/
│   +-- raw/                   # Leituras FASTQ brutas (não versionadas)
│   +-- ref/                   # Referências virais em formato FASTA
+-- results/                   # Resultados gerados (relatórios e estatísticas)
```

---

## 8. Citação e origem acadêmica

O Gene-In foi desenvolvido no contexto de uma pesquisa de mestrado em virologia, com foco na recuperação, organização e priorização reprodutível de fragmentos virais candidatos em dados de sequenciamento.

Se utilizar o Gene-In em trabalhos acadêmicos, cite este repositório e a publicação associada quando disponível.

*Detalhes de citação: pendente.*

---

## 9. Licença

Este projeto é disponibilizado sob licença pública limitada de uso. O Gene-In pode ser utilizado para avaliação acadêmica, uso educacional, pesquisa não comercial, demonstração e testes, conforme os termos descritos no arquivo [LICENSE](LICENSE). Redistribuição, modificação, revenda, sublicenciamento, engenharia reversa ou uso diagnóstico/regulatório não são permitidos sem autorização prévia por escrito.
