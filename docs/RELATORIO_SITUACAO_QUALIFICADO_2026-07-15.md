# Relatório de situação qualificado — Gene-In 2.0 e família de skills

**Data da qualificação:** 2026-07-15  
**Atualização canônica:** 2026-07-15, informada pelo responsável pelo projeto.  
**Escopo:** texto de retomada fornecido pelo usuário, estado local do repositório, skills instaladas e evidência externa sobre a escolha do montador.  
**Base examinada:** worktree local, sem garantia de corresponder a um commit imutável.

## 1. Veredito executivo

**APROVADO COM RESSALVAS como memorando operacional de retomada.** O texto original organiza bem a história recente, identifica pendências acionáveis e preserva a cautela sobre validação real.

**NÃO APTO como registro de validação científica, auditoria encerrada ou fotografia reprodutível do projeto.** O texto mistura fatos verificados, memória de conversas, inferências e decisões pendentes; não informa a data de corte nem o commit; usa números de linha frágeis; e formula a conclusão sobre Velvet com força maior do que a evidência aplicável ao Gene-In permite.

| Dimensão | Qualificação | Justificativa |
|---|---|---|
| Organização | forte | As duas trilhas e as pendências estão claramente separadas. |
| Utilidade para retomada | forte | O texto indica decisões e próximos passos concretos. |
| Rastreabilidade | parcial | Há arquivos e alguns pontos de código, mas faltam commit, data de corte, comandos e evidências anexas. |
| Separação entre fato e hipótese | parcial | Expressões como “pode já estar em uso” e “benchmarks convergem” aparecem junto de estados operacionais. |
| Atualidade | parcial | Parte do texto já foi superada pelo estado atual das skills e pela documentação do repositório. |
| Qualidade científica | parcial | A cautela geral é adequada, mas a transferência da literatura sobre montadores não passa integralmente pelo regime do Gene-In. |

## 2. Evidência recuperada nesta qualificação

- [RECUPERADO] O worktree declara a versão `2.0.0-alpha.2` e contém alterações rastreadas, além de arquivos ainda não rastreados. Portanto, esta fotografia não é um snapshot imutável e não deve ser tratada como release.
- [RECUPERADO — estado canônico informado] WSL está disponível e funcional; as ferramentas principais foram detectadas; PyYAML foi confirmado em `/usr/bin/python`; o Python do bundle ainda requer verificação; UMI-tools e Node.js estão ausentes.
- [RECUPERADO — estado canônico informado] `bash -n` foi aprovado. ShellCheck foi executado, com achados funcionais e documentais ainda pendentes.
- [RECUPERADO — estado canônico informado] O número exato de testes Python deve ser estabelecido por log reproduzível. A execução real ponta a ponta, a repetibilidade e a revisão visual do dashboard permanecem pendentes; o benchmark científico continua bloqueado.
- [RECUPERADO] A Evidence V2 permanece em `shadow_mode`; a documentação exige Linux congelado, ferramentas reais, dados públicos/sintéticos versionados, repetição independente e nova auditoria antes de qualquer saída desse modo.
- [RECUPERADO] A matriz registra **58** achados do ShellCheck no texto de evidência, mas a linha A3 ainda informa **60**. `docs/VALIDATION_STATUS.md` ainda informa **61 testes**, enquanto a matriz menciona **66** como registro histórico.
- [INFERIDO] Até haver log reproduzível, esses números devem ser tratados como históricos e não como estado canônico de aprovação.

## 3. Estado consolidado — Trilha A: família de skills

| Item | Estado qualificado em 2026-07-15 | Evidência e ação |
|---|---|---|
| Analisar fragmentos virais curtos | **CONSTRUÍDA, COM INCONSISTÊNCIA CIENTÍFICA ABERTA** | [RECUPERADO] A skill está instalada. `SKILL.md`, testes e checklists ainda usam abstenção abaixo de **80 pb**, enquanto `references/reference.md` afirma que o menor comprimento diretamente estudado para DeepVirFinder foi **150 pb**. A correção 80→150 pb não foi aplicada. |
| Auditor de código de pipelines virais | **NÃO LOCALIZADA COMO SKILL INDEPENDENTE** | [RECUPERADO] Não há diretório instalado com esse papel no escopo consultado. A skill de análise viral possui um checklist de auditoria de pipeline, mas isso não comprova que a skill auditora proposta foi construída. Registrar como “não localizada”, não como “inexistente”. |
| Suporte científico | **CONSTRUÍDA E INSTALADA** | [RECUPERADO] A skill `verificar-literatura-e-ferramentas` está instalada e contém as travas RECUPERADO/LEMBRADO/INFERIDO, o portão de aplicabilidade e a classificação L1–L4. O relatório original está desatualizado neste ponto. |
| Corretora | **PENDENTE** | [RECUPERADO] Não foi localizada uma skill corretora instalada nem um meta-prompt correspondente no escopo consultado. O modo descrito continua sendo apenas uma decisão de desenho. |

### Decisão recomendada para a Trilha A

1. Corrigir a política de ML da primeira skill de forma consistente em `SKILL.md`, checklists e testes, preservando a distinção entre análise exploratória e chamada.
2. Decidir se a auditoria continuará incorporada à skill de análise ou se será separada numa skill própria; evitar duas fontes normativas divergentes.
3. Só então escrever a skill corretora, porque ela dependerá do contrato estável do auditor.

## 4. Estado consolidado — Trilha B: Gene-In 2.0 alpha.2

### 4.1 O que está confirmado

- [RECUPERADO — estado canônico informado] Há testes Python executados, mas a contagem e o resultado canônicos ainda devem ser ancorados em log reproduzível.
- [RECUPERADO] A política alpha.2 limita a saída pública da Evidence V2 a E1 ou `NOT_EVALUABLE` e mantém a versão 1.1 como oficial.
- [RECUPERADO] A matriz separa corretamente fixture/mock de validação com ferramenta real.
- [RECUPERADO] A1, A2, A5, B1 e B2 têm implementação e regressões locais, mas ainda possuem validações reais pendentes.
- [RECUPERADO] B3 possui revisão estática; B4 e a parte visual de B2 continuam pendentes em navegador real.

### 4.2 Correção material do relatório original

**O ambiente deixou de ser o bloqueador de disponibilidade, mas a validação real ainda não foi executada.**

- [RECUPERADO — estado canônico informado] WSL está funcional e as ferramentas principais foram detectadas; ainda faltam UMI-tools, Node.js e a verificação do Python do bundle.
- [RECUPERADO] A1, A2, B1, B2, B4 e os testes integrados requerem execução Linux/CI/navegador real e evidência persistida.
- [RECUPERADO] A4 continua explicitamente `BLOQUEADA_POR_IMPLEMENTAÇÃO_E_AMBIENTE`: falta migrar o legado para staging unificado antes que um teste real de queda possa ser conclusivo.
- [INFERIDO] A prioridade agora é executar e registrar a Fase 0 no ambiente já disponível; isso não fecha A4 nem substitui trabalho de engenharia.

### 4.3 Três achados ainda sem linha própria na matriz

| Achado | Estado recuperado | Linha que deve ser adicionada |
|---|---|---|
| Estabilidade filogenética entre métodos, referências, reamostragem e recombinação | [RECUPERADO] `phylogeny_gate.py` verifica comprimento, sítios informativos, painel balanceado, outgroup, complexidade e suspeita de quimera; não verifica estabilidade entre métodos/reamostragens nem incompatibilidade por recombinação. | Componente: `phylogeny_gate.py`; regressões novas para topologias/placements instáveis e janelas recombinantes; aceite: bloquear interpretação quando a conclusão não for estável. |
| Proveniência por execução | [RECUPERADO] `write_provenance.py` registra hash do config, artefatos fornecidos e executáveis/ferramentas. Não registra de forma explícita o comando completo normalizado de cada estágio nem garante o hash de todos os bancos usados. | Componente: `write_provenance.py` e chamadores; regressão para banco/binário/comando por estágio; aceite: reproduzir exatamente identidade de inputs e invocações. |
| Composição mínima do painel competitivo | [RECUPERADO] `finalize_panel.py` exige seis categorias, valida FASTA/rótulos e índices e promove atomicamente. A matriz, porém, não contém linha própria nem regressão nominal para esse contrato. | Componente: `finalize_panel.py`; regressões para categoria ausente, rótulo divergente e índice incompleto; aceite: nenhum painel incompleto pode receber `SUCCESS.json`. |

### 4.4 Busca sem painel competitivo simultâneo

- [RECUPERADO] O fluxo principal ainda pode entrar na Evidence V2 com um BLAST já produzido contra o banco configurado, sem `--composite-db` e sem rótulos de sujeitos.
- [RECUPERADO] Nesse caminho, os hits ficam sem categoria competitiva; `competitive_hits.py` produz `NOT_EVALUATED`/`NO_NON_TARGET_COMPETITOR`, e `classify_sample.py` mantém o gate `competitive_specificity` bloqueado.
- [INFERIDO] A questão não é totalmente *moot*: já existe um gate de contenção, portanto não há justificativa para promover especificidade; porém falta tornar o caminho competitivo uma pré-condição explícita e testada para qualquer versão além do shadow E1. A matriz deve registrar esse contrato sem depender de um número de linha que muda a cada edição.

## 5. Qualificação da alegação sobre Velvet

### Veredito de aplicabilidade

**PARCIAL ao regime do Gene-In. Decisão recomendada: PILOTAR, não ADOTAR nem REJEITAR por literatura externa.**

| Dimensão | Evidência recuperada | Resultado |
|---|---|---|
| Comprimento | Estudos consultados avaliam montagem de reads Illumina e recuperação de genomas/contigs, não a decisão operacional sobre fragmentos candidatos de 20–100 pb do Gene-In. | parcial |
| Prevalência/cobertura | Há cenários de baixa cobertura e abundância desigual, mas as comunidades e distribuições não reproduzem o ponto operacional do Gene-In. | parcial |
| Métrica | Os trabalhos medem montagem, contig, cobertura genômica e/ou vírus recuperados; não medem o custo de falsos positivos do contrato E1 no Gene-In. | parcial |
| Vazamento | Não é a dimensão central dos benchmarks de montagem examinados; transferência para calibração do Gene-In não foi demonstrada. | não informado para o objetivo do projeto |
| Domínio | Há evidência em viromas, metagenomas e RNA viral, mas parte importante usa fagos/DNA, comunidade microbiana ou consenso de vírus já caracterizados. | parcial |
| Independência | Há comparações independentes de Velvet, MetaVelvet, SPAdes e metaSPAdes. | candidato a L3 |
| Operacional | Versão, manutenção, licença e custo atual das ferramentas não foram auditados nesta qualificação. | não verificado |

### Síntese conservadora

- [RECUPERADO] Roux et al. observaram melhor recuperação de genomas virais em baixa cobertura com IDBA-UD, MEGAHIT e metaSPAdes do que com MetaVelvet em comunidades virais simuladas. Fonte primária consultada em 2026-07-15: [PeerJ 5:e3817](https://pmc.ncbi.nlm.nih.gov/articles/PMC5610896/).
- [RECUPERADO] O artigo do próprio MetaVelvet mostrou que o Velvet, um montador de genoma único, falhou em reconstruir espécies de baixa abundância em um benchmark metagenômico simulado. Por ser resultado dos autores da extensão, este achado permanece L2 isoladamente. Fonte consultada em 2026-07-15: [Nucleic Acids Research — MetaVelvet](https://pmc.ncbi.nlm.nih.gov/articles/PMC3488206/).
- [RECUPERADO] Uma comparação independente de montagem para descoberta viral encontrou resultados dependentes do conjunto e da métrica; Velvet foi rápido e chegou a recuperar alguns sinais não compartilhados por outros montadores, embora produzisse os menores contigs no conjunto descrito. Isso contradiz a formulação de “convergência” absoluta contra Velvet. Fonte consultada em 2026-07-15: [Journal of Computational Biology, DOI 10.1089/cmb.2017.0008](https://journals.sagepub.com/doi/10.1089/cmb.2017.0008).
- [RECUPERADO] Em uma avaliação de montagem de vírus de RNA, SPAdes recuperou frações genômicas muito maiores que Velvet nos exemplos apresentados, mas o objetivo era reconstrução de consenso de vírus conhecidos, não triagem metagenômica de fragmentos raros. Fonte consultada em 2026-07-15: [PeerJ 9:e12129](https://pubmed.ncbi.nlm.nih.gov/34567846/).
- [INFERIDO] A literatura sustenta a preocupação com Velvet como padrão para cobertura irregular/baixa abundância, mas não autoriza escolher outro montador principal para o Gene-In sem benchmark próprio.

### Benchmark mínimo antes de mudar o montador padrão

Comparar Velvet, SPAdes e metaSPAdes com os mesmos reads, recursos e bancos, usando dados sintéticos/públicos versionados e estratificação por abundância e cobertura. Medir, no mínimo:

1. recuperação de candidatos e perda de alvos conhecidos;
2. distribuição de comprimento dos contigs e fração de reads incorporada;
3. quimeras, montagem incorreta e ambiguidade após busca competitiva;
4. estabilidade entre repetições e parâmetros;
5. tempo, memória, falhas e reprodutibilidade;
6. efeito final no contrato E1, sem usar N50 isoladamente como critério de escolha.

## 6. Ordem de retomada recomendada

### P0 — preservar contenção e produzir evidência reproduzível

1. Manter `shadow_mode=true` e a versão 1.1 como oficial.
2. Criar um snapshot identificável do alpha.2 — commit, tag interna ou manifesto de arquivos e hashes — antes de novas rodadas de validação.
3. Gerar e preservar o log reproduzível dos testes Python; corrigir as divergências históricas de 61 versus 66 testes e 58 versus 60 achados do ShellCheck.
4. Executar a Fase 0 no WSL funcional, verificando o Python do bundle e registrando a ausência de UMI-tools e Node.js como pré-condições ou falhas explícitas.

### P1 — fechar bloqueios de engenharia e matriz

5. Implementar a migração de staging do legado para resolver a parte de engenharia de A4.
6. Adicionar as três linhas ausentes à matriz, cada uma com regressão nominal e critério de aceite.
7. Registrar explicitamente que especificidade competitiva não avaliada bloqueia qualquer promoção futura além do shadow E1.

### P2 — decisões científicas e de arquitetura

8. Executar os casos sintéticos e controles com ferramentas reais.
9. Realizar o benchmark comparativo de montadores; somente então documentar a decisão sobre o padrão.
10. Corrigir a skill de fragmentos virais e estabilizar o contrato da auditoria antes de criar a skill corretora.

## 7. Pendências que exigem decisão humana

- Definir onde serão preservados os logs, manifestos e resultados da execução no WSL/CI já disponível.
- Aprovar o desenho do benchmark de montadores e os dados públicos/sintéticos permitidos.
- Decidir se a auditoria de pipeline será uma skill independente ou uma responsabilidade da skill de análise viral.
- Aprovar tecnicamente a mudança da política de ML de 80 para 150 pb antes de alterar a skill instalada.

## 8. Ressalvas

- A qualificação não aprova a correção científica nem a saída de `shadow_mode`.
- A aprovação de `bash -n` e a detecção de ferramentas não substituem uma execução ponta a ponta com artefatos e logs reproduzíveis.
- UMI-tools e Node.js continuam ausentes no estado canônico; a verificação do Python do bundle também permanece aberta.
- O resultado do ShellCheck é canonicamente “executado, com pendências”; sua contagem exata deve ser reconciliada com a saída arquivada.
- A busca externa foi focal, não exaustiva. Não foram auditadas nesta etapa versões atuais, licenças, manutenção ou requisitos operacionais dos montadores.
