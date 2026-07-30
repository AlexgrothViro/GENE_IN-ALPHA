# B4 — registro de fontes científicas e operacionais

## Registro de busca

- Data: 2026-07-29.
- Pergunta operacional: os perfis BLAST, o limite de resultados e a agregação de HSPs sustentam uma comparação competitiva completa para fragmentos curtos?
- Consultas exatas:
  - `site:ncbi.nlm.nih.gov/books BLAST+ max_target_seqs blastn-short word size 7 command line manual`
  - `Shah Nute Warnow Pop 2019 misunderstood parameter NCBI BLAST max_target_seqs paper`
  - `Camacho 2009 BLAST+ architecture applications BMC Bioinformatics primary paper`
  - `Madden Busby Ye 2019 Reply misunderstood parameter BLAST max_target_seqs 2.8.1 full text`
- Fontes consultadas:
  - [Manual oficial BLAST+, tabela de opções do blastn](https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/table/appendices.T.blastn_application_options/)
  - [Notas oficiais de versão do BLAST+](https://www.ncbi.nlm.nih.gov/sites/books/NBK131777/)
  - [Shah et al., 2019](https://doi.org/10.1093/bioinformatics/bty833)
  - [Madden, Busby e Ye, 2019](https://doi.org/10.1093/bioinformatics/bty1026)
  - [Camacho et al., 2009](https://doi.org/10.1186/1471-2105-10-421)
- Limite de cobertura: não foi localizado nem adotado benchmark independente que estime precisão, recall ou falso-positivo do Gene-In especificamente em 20–49 bp sob baixa prevalência.

## Evidência recuperada

- `[RECUPERADO]` O manual oficial descreve `blastn-short` como otimizado para sequências menores que 30 nt e registra `word_size=7`, recompensa 1, penalidade -3, `gapopen=5` e `gapextend=2`.
- `[RECUPERADO]` As notas oficiais registram que BLAST+ 2.8.1 desativou uma otimização excessiva associada ao problema discutido por Shah et al. e passou a alertar para `max_target_seqs < 5`.
- `[RECUPERADO]` A versão oficial mais recente registrada nas notas é 2.17.0, de 2025-07-22; o lock do projeto fixa 2.17.0, enquanto o teste local deste bloco executou BLAST+ 2.12.0.
- `[RECUPERADO]` Shah et al. demonstraram comportamento dependente da ordem do banco em versões anteriores. A resposta do NCBI delimitou parte do problema como bug corrigido em 2.8.1.
- `[INFERIDO]` Mesmo sem assumir o comportamento histórico nas versões atuais, um relatório limitado a 50 sujeitos não pode demonstrar competição completa quando o painel contém mais de 50 sujeitos qualificáveis. Por isso, o roteador passou a consultar `blastdbcmd -info` e usar como limite efetivo pelo menos o número total de sequências do painel.

## Portão de aplicabilidade

| Dimensão | Evidência recuperada | Resultado | Efeito |
|---|---|---|---|
| Comprimento | O manual cobre diretamente `<30 nt`; não valida recuperação em 30–49 bp nem desempenho biológico. | parcial | Sustenta o perfil técnico, não limiares de decisão. |
| Prevalência | Não informada nas fontes operacionais. | não informado | Não sustenta precisão em baixa prevalência. |
| Métrica | Não há AUPRC, precisão operacional nem falsos positivos absolutos para o Gene-In. | falha para desempenho | Nenhum gate científico foi promovido. |
| Vazamento | Não aplicável à documentação da ferramenta. | não aplicável | Benchmark interno ainda obrigatório. |
| Domínio | Busca local nucleotídeo–nucleotídeo coincide com a tarefa operacional. | passa operacionalmente | Permite corrigir implementação e proveniência. |
| Independência | Documentação do mantenedor e artigos do debate técnico; sem benchmark independente do Gene-In. | L1–L2 operacional | Não valida a escada E1–E4. |
| Operacional | Linux/WSL compatível; 2.12.0 testado, 2.17.0 fixado no lock ainda não executado neste bloco. | parcial | Exige repetição no ambiente bloqueado pelo lock. |

## Decisão

`ADOTAR` apenas as correções de integridade e completude do relatório BLAST dentro do painel fornecido. Não alterar limiares, classes ou teto Alpha.2. A expressão `TARGET_SPECIFIC` continua significando separação computacional perante os competidores efetivamente incluídos e rotulados no painel, não especificidade biológica universal.
