# Escopo e invariantes

## Objetivo do Gene-In

O Gene-In é uma plataforma local de pesquisa para recuperação, agregação, triagem, rastreabilidade e interpretação conservadora de fragmentos virais candidatos em dados de NGS/metagenômica, sobretudo em cenários de baixa carga, alta proporção de material do hospedeiro ou montagem incompleta.

O eixo biológico é `Picornaviridae`, especialmente PTV/Teschovirus A, EV-G, PSV e SVA. A arquitetura pode analisar outros vírus pequenos quando bancos, controles e políticas apropriados estiverem versionados.

## Limites científicos obrigatórios

- Não é software diagnóstico.
- Similaridade por BLAST não confirma presença, infecção, causalidade ou atividade viral.
- Fragmentos de `20–49 bp` são exploratórios e nunca podem, isoladamente, promover identificação, detecção ou resultado positivo.
- `adj_identity` é apenas métrica auxiliar; não substitui identidade, cobertura, especificidade competitiva, suporte nas reads, controles ou coerência biológica.
- Resultados dependem do banco, da qualidade das reads, do hospedeiro, dos controles e da política científica versionada.
- E4 depende de confirmação experimental externa e nunca é emitido pelo software.
- Ausência de evidência classificável não exclui material viral pouco abundante, divergente ou mal representado no banco.

## Invariantes de engenharia

- Preservar a compatibilidade histórica da versão 1.1 sem permitir que ela contamine a decisão V2.
- Tratar estado operacional e força científica como dimensões independentes.
- Não promover runs legados automaticamente. Legado incompatível deve ser explicitamente marcado e não avaliado pela V2.
- Versionar políticas, parâmetros, bancos, ferramentas e adaptações. Mudanças criam nova identidade e não reclassificam runs antigos silenciosamente.
- Não alterar limiares, classes, tetos ou linguagem científica sem aprovação técnica e científica documentada.
- Outputs devem ser transacionais: escrever em área temporária, validar, promover atomicamente e preservar a última execução válida em caso de falha.
- Falhas de montagem, exportação, cobertura, controles ou serialização que afetem a conclusão devem bloquear sucesso científico.
- Nunca mascarar falhas críticas com `|| true`, `ignore_errors`, exceções genéricas ou valores padrão que pareçam válidos.
- Dados privados, FASTQs e resultados reais não devem entrar no repositório público ou em fixtures.
- Testes unitários e de contrato devem usar fixtures sintéticas determinísticas; testes operacionais podem usar dados públicos aprovados.

## Separações que a revisão deve preservar

- classes locais/legadas (`STRONG`, `MODERATE`, `WEAK` ou `WEAK_RECOVERABLE`, `REVIEW`, `STRONG_DIVERGENT`);
- níveis de evidência científica (`E1–E4`);
- `execution_status`;
- `analysis_outcome`;
- `reported_conclusion`;
- achados auxiliares/sidecars;
- confirmação externa.

