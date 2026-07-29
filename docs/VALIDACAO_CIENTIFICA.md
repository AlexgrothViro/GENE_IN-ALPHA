# Estado científico e interpretação — Gene-In 2.0

## Estado atual

O Gene-In `2.0.0-alpha.2` opera exclusivamente em `shadow_mode`. A saída pública usa um contrato único com três dimensões independentes:

| Dimensão | Valores |
|---|---|
| Execução | `queued`, `running`, `done`, `warning`, `blocked`, `failed`, `cancelled` |
| Outcome | `EVIDENCE_RECOVERED`, `NO_EVIDENCE_RECOVERED`, `NOT_EVALUABLE` |
| Nível | `E1`, `E2`, `E3`, `NOT_EVALUABLE` |

Nesta versão, E2 e E3 existem no schema, mas são estruturalmente inacessíveis. E4 não é emitido pelo software.

## Regras de comunicação

- E1 registra somente evidência computacional exploratória; não afirma presença, ausência, identidade, confirmação, variante ou linhagem.
- Uma execução válida sem candidatos usa `NO_EVIDENCE_RECOVERED`, lista vazia e ressalva explícita. Isso não demonstra ausência.
- Falha de execução, artefato inválido ou etapa científica incompleta usa `NOT_EVALUABLE`.
- Rótulos históricos são expostos apenas como `legacy_label`, em adaptador de leitura, sempre com teto E1.
- Variantes e ML não integram o Gene-In 2.0.

## Requisitos para qualquer promoção futura

Uma eventual habilitação de E2/E3 exige, no mínimo:

- métricas associadas à mesma referência, categoria e locus do candidato;
- painel competitivo completo, versionado e com hash;
- controles, avaliação de sinais compartilhados e rastreio entre amostras;
- cobertura e suporte por candidato, sem agregação global;
- informação filogenética limitada ao span efetivamente coberto;
- benchmark próprio, congelado e reproduzível;
- execução ponta a ponta em ferramentas reais, repetição independente e auditoria sem bloqueadores.

Testes com fixtures ou mocks verificam somente contratos de software. Eles não substituem execução real nem validação científica.
