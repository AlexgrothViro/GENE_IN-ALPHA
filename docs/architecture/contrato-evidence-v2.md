# Contrato Evidence V2

## Dimensões canônicas

### `execution_status`

Descreve se a execução terminou tecnicamente: por exemplo, concluída, falhou, bloqueada ou cancelada. Não declara evidência biológica.

### `analysis_outcome`

- `RECOVERED`: foram recuperadas evidências computacionais classificáveis.
- `NO_EVIDENCE`: a análise foi válida, mas não recuperou evidências classificáveis.
- `NOT_EVALUABLE`: a execução ou um gate crítico não permitiu uma conclusão científica válida.

`analysis_outcome` registra recuperação computacional, não aprovação de promoção. Um
candidato retido pode ter `promotion_status=BLOCKED`; nesse caso seus motivos devem
permanecer explícitos. Fragmentos de `20–49 bp` podem produzir
`EVIDENCE_RECOVERED` para fins de rastreabilidade, mas permanecem
`candidate_class=EXPLORATORY_FRAGMENT` e nunca ficam elegíveis isoladamente.

### `evidence_level`

- `E1`: evidência computacional inicial compatível, com todos os gates exigidos para E1 documentados.
- `E2`: nível superior, acessível apenas quando todos os gates versionados de E2 estiverem comprovados.
- `E3`: nível superior, acessível apenas quando todos os gates versionados de E3 estiverem comprovados.
- `E4`: confirmação experimental externa; não é emitida pelo software.
- `NOT_EVALUABLE`: não foi possível avaliar validamente.

### Estado da Alpha.2

- `shadow_mode=true`
- `reported_conclusion=SHADOW_ONLY`
- teto científico: `E1` ou `NOT_EVALUABLE`
- `E2`, `E3` e `E4`: estruturalmente inacessíveis

## Agregação esperada

O raciocínio não deve terminar em uma linha BLAST. A hierarquia é:

`HSP → contig/read → locus → referência/táxon → amostra`

A revisão deve procurar:

- fusão correta de HSPs sobrepostos;
- cobertura não redundante;
- contagem de loci independentes sem duplicar a mesma região;
- suporte nas reads e diversidade de posições/templates;
- especificidade competitiva contra não alvos, hospedeiro, vetor e contaminantes;
- controles positivos e negativos;
- proveniência e caveats;
- abstenção quando os requisitos não são atendidos.

## Regras negativas indispensáveis

- Um fragmento exploratório isolado não promove E1.
- Candidato bloqueado não desaparece do artefato: classe, status e motivos de bloqueio permanecem auditáveis.
- Vários HSPs da mesma região não viram vários loci.
- Repetição do mesmo fragmento não equivale a evidências independentes.
- Controle negativo compatível pode bloquear promoção.
- Falha do controle positivo pode invalidar o lote.
- Ambiguidade competitiva deve ser preservada, não convertida em especificidade.
- Falha crítica V2 resulta em `NOT_EVALUABLE`, nunca em `NO_EVIDENCE`.
- Dashboard, relatório e camadas interpretativas não podem recalcular nem elevar o nível canônico.

## Campos cuja presença deve ser auditada

- versão da política;
- versão do pipeline;
- `run_id`, amostra e lote;
- `shadow_mode`;
- status, outcome e evidence level;
- gates, caveats e motivos de bloqueio;
- controles, cobertura, especificidade e proveniência;
- hashes de entradas/configurações quando aplicável;
- manifesto e versão do banco;
- versões das ferramentas;
- `adaptation_id` quando houver adaptação;
- orientação do candidato;
- lista de artefatos validados.
