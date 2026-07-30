# Validação, benchmark e exclusões

## Regra de interpretação do status

Não confundir:

- testes unitários passando;
- execução operacional ponta a ponta;
- qualificação científica;
- saída de `shadow_mode`;
- validação experimental externa.

Cada afirmação precisa indicar ambiente, commit, versão da política, fixtures/dados, data e limitações.

## Estado conhecido que exige cautela

A documentação enviada da 1.1 registra testes mínimos (`make test-env`, `make help`, `make test-demo`) e uma matriz histórica de validação. Isso não qualifica automaticamente a Evidence V2.

Em auditorias posteriores da Alpha.2 foram relatados conjuntos extensos de testes, mas o estado não deve ser resumido como “aprovado”: houve falhas de permissão entre Windows/WSL e, na auditoria WSL mais recente registrada, defeitos de engenharia mantiveram o veredito reprovado.

Defeitos relatados que precisam ser confirmados no HEAD antes de qualquer conclusão:

1. falha do montador possivelmente ignorada em `scripts/20_run_pipeline.sh`;
2. `|| true` mascarando falha de exportação em `scripts/95_report_minimal.sh`;
3. problema de backticks/heredoc em `scripts/21_run_advanced_analysis.sh`;
4. workflow de ShellCheck falhando;
5. `docs/science/validation-status.md` desatualizado;
6. limpeza de BLAST com `ignore_errors` silencioso.

Esses itens são pistas de revisão, não afirmação de que ainda existem no código atual.

## Exclusões obrigatórias

- `2323`: amostra exploratória; não usar em análise científica, benchmark, critérios de validação, artigo ou dissertação.
- `81554` e `81555`: não usar nos novos testes/benchmarks definidos para a Alpha.2.
- Não reutilizar esses casos como positivos ocultos, fixtures “sintéticas” derivadas ou critérios de calibração.

## Requisitos já definidos para novos testes operacionais

- usar amostras inéditas e dados públicos aprovados;
- exercitar pelo menos quatro bancos virais válidos;
- realizar pelo menos dois rebuilds reais de banco;
- exercitar SPAdes, metaSPAdes e Velvet;
- manter fixtures limítrofes sintéticas para comprimentos e gates;
- testar promoção e bloqueio em ambos os sentidos;
- testar falhas parciais, cancelamento, repetibilidade e concorrência;
- testar que fragmentos `20–49 bp` permanecem exploratórios;
- testar HSPs sobrepostos, loci repetidos, baixa complexidade, competidores e controles.

## Matriz histórica

A matriz histórica do projeto utilizou 14 amostras e 42 execuções, com SPAdes como matriz principal e comparações com metaSPAdes e Velvet. Ela é evidência histórica da versão anterior e não deve ser apresentada como validação científica completa da Alpha.2.

## Critério de saída

Uma revisão só pode recomendar avanço quando:

- defeitos críticos estão corrigidos e testados;
- `docs/science/validation-status.md` corresponde ao commit auditado;
- gates positivos e negativos foram exercitados;
- ambiente real Linux/WSL foi validado;
- nenhum resultado legado foi promovido silenciosamente;
- o teto Alpha.2 continua respeitado;
- limitações e abstenções aparecem corretamente no dashboard e nos artefatos.
