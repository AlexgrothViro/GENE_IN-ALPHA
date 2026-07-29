# Gene-In

O **Gene-In** é um pipeline bioinformático estruturado para recuperar e priorizar fragmentos virais em dados de sequenciamento de alto rendimento provenientes de amostras clínicas ou metagenômicas complexas com baixa carga viral.

---

## 1. Principais Características

*   **Identidade Ajustada:** Algoritmo estatístico que calcula a identidade de sequência ajustada (`adj_identity`), mitigando o viés de alinhamentos muito curtos de alta identidade.
*   **Contrato público de evidência:** `E1 | E2 | E3 | NOT_EVALUABLE`, com `E2/E3` bloqueados na versão `2.0.0-alpha.2` e E4 nunca emitido pelo software. As cinco classes históricas existem somente como `legacy_label`, com teto E1.
*   **Modo de Resgate de Leituras (Read-level Rescue):** Ativação automática de busca direta por similaridade em reads individuais (`READ_LEVEL_SIGNAL`) caso os processos de montagem falhem por cobertura insuficiente extrema.
*   **Dashboard Interativo:** Painel web local em Python para parametrização visual, monitoramento de execuções de pipeline em tempo real e visualização de relatórios científicos formatados.

---

## 2. Para quem é?

O Gene-In foi projetado para:
*   Pesquisadores, biólogos e bioinformatas que investigam a virosfera em amostras de NGS de baixa cobertura.
*   Equipes de pesquisa e vigilância que desejam automatizar triagem computacional não diagnóstica, com revisão humana e controles independentes.

---

## 3. O que explicitamente NÃO é e NÃO faz?

> [!IMPORTANT]
> **Atenção às Limitações Científicas e de Escopo:**
> *   **NÃO é um software de diagnóstico clínico:** A classificação do Gene-In é puramente bioinformática, baseada em homologia de sequência primária. Não fornece laudos de diagnóstico clínico de infecção viral ativa.
> *   **E1 não afirma presença ou ausência viral:** leituras, contigs e classes históricas registram somente candidatos de homologia nas condições avaliadas.
> *   **Exige curadoria e controles científicos:** Resultados obtidos de baixíssima cobertura biológica (como em `WEAK_RECOVERABLE`) podem refletir contaminações cruzadas de laboratório, ruído basal de sequenciamento ou sequências conservadas do hospedeiro. É obrigatório o uso concomitante de controles negativos reais e a validação experimental ortogonal (ex: RT-qPCR).
> *   **Viés do Banco de Referência:** A sensibilidade de detecção está atrelada à diversidade de sequências contidas no banco configurado no pipeline. Bancos incompletos ou desatualizados podem gerar falsos negativos para linhagens virais muito divergentes.

---

## 4. Status de validação

A versão `2.0.0-alpha.2` está em `shadow_mode`. Testes unitários e sintéticos verificam contratos e regressões específicas, mas não demonstram corretude científica ponta a ponta. A saída de `shadow_mode` exige benchmark público/sintético congelado, execução real das ferramentas em Linux, controles completos, repetição independente e nova auditoria sem bloqueadores.

Resultados publicados por terceiros não substituem o benchmark próprio e congelado deste projeto. O estado detalhado e as limitações estão documentados em `docs/VALIDATION_STATUS.md` e na matriz de remediação.

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

## 6. Como interpretar a saída

O artefato canônico é `sample_evidence.json`. Uma execução válida sem candidatos usa `analysis_outcome=NO_EVIDENCE_RECOVERED`, `evidence_level=E1`, lista vazia e ressalva explícita; isso não significa ausência viral. Falha científica ou artefato inválido usa `NOT_EVALUABLE`.

### Compatibilidade de execuções anteriores à Alpha.2

Resultados Evidence V2 gerados antes de `2.0.0-alpha.2` não satisfazem retroativamente o contrato atual. Eles permanecem preservados para auditoria, mas o dashboard os identifica como `LEGACY_INCOMPATIBLE`, com outcome `NOT_EVALUABLE`, e não exibe seus rótulos como evidência Alpha.2. Para obter um resultado válido, é necessário reexecutar a análise com a versão atual. Não existe promoção automática desses artefatos para E1.

As execuções locais `79f201633acf43b9a395c23725d2e0f0` e `8e612a9309d94d8eae8dca0d291af199` são exemplos históricos Alpha.1: seus arquivos originais devem ser mantidos, e as análises precisam ser reexecutadas para produzir colunas, documento de evidência e manifesto Alpha.2 completos.

`results/blast/{SAMPLE}_labeled_hits.tsv` é um artefato legado de compatibilidade. Seus rótulos não são níveis públicos e nunca podem ultrapassar E1:

| Classe de Evidência | Critério Bioinformático Principal | Significado Científico | Ação Recomendada |
|---|---|---|---|
| `STRONG` | Comp. $\ge 80$ pb, pident $\ge 90\%$, adj_identity $\ge 70\%$, e-value $\le 10^{-10}$ | Forte evidência de homologia viral. Contig longo e bem alinhado. | Priorizar contig para análises filogenéticas detalhadas. |
| `STRONG_DIVERGENT` | Regra histórica de homologia | `legacy_label`; não chama variante ou linhagem. | Revisão exploratória E1. |
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
