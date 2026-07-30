# Níveis de teste e reprodutibilidade

Este documento define o significado dos testes do Gene-In. Um nível aprovado
não implica automaticamente aprovação dos níveis seguintes.

| Nível | Comando canônico | O que demonstra | O que não demonstra |
|---|---|---|---|
| Engenharia | `make test` | Contratos, schemas, fixtures sintéticas, mocks, falhas, concorrência, transações e regressões determinísticas | Funcionamento das ferramentas científicas reais ou validade biológica |
| Operacional | `make test-operational` | Ferramentas reais instaladas no host conseguem executar casos sintéticos controlados | Correspondência com o lock, sensibilidade/especificidade científica ou generalização |
| Reprodutibilidade | `make test-reproducible` | Ambiente Conda ativo coincide exatamente com as versões/builds do lock e passa os testes operacionais | Validação científica, calibração de limiares ou saída de `shadow_mode` |
| Validação científica | roteiro formal ainda bloqueado | Benchmark congelado, controles completos, métricas pré-especificadas e repetição independente | Não é substituída por unit tests, mocks ou smokes locais |
| Qualificação de evidência | contrato E1–E4 por execução | O que um resultado individual permite reportar | Não valida o software como um todo; E4 exige confirmação experimental externa |

## Política de skip

- Testes de engenharia podem registrar skips nominais de plataforma, mas o
  total deve ser informado.
- Testes operacionais retornam código `77` quando qualquer ferramenta
  obrigatória está ausente; isso significa **não executado**, nunca `PASS`.
- A suíte reprodutível retorna código `77` quando `CONDA_PREFIX` não está ativo.
- Divergência entre pacote instalado e versão/build do lock é falha, não skip.
- Nenhum skip pode ser convertido em evidência de validação científica.

## Faixa de fragmentos curtos

O benchmark sintético determinístico contém os limites
`20, 29, 30, 49, 50, 79, 80, 99, 100 e 200 bp`. Além da matriz de fronteiras,
os testes de contrato percorrem cada comprimento inteiro de 20 a 100 bp e
verificam:

- roteamento `blastn-short`, dual ou `blastn` conforme a configuração versionada;
- classe `EXPLORATORY_FRAGMENT` para 20–49 bp;
- bloqueio `BELOW_MINIMUM_CANDIDATE_BP` para 20–49 bp;
- teto `E1` e conclusão `SHADOW_ONLY` em Alpha.2;
- ausência de promoção mesmo quando o candidato sintético é alvo-específico,
  mas não possui suporte independente.

Esse teste verifica coerência do código e das fronteiras. Ele não mede taxa de
recuperação, limite de detecção, falso-positivo ou desempenho em amostras reais.

## Dados permitidos

As suítes canônicas usam somente sequências sintéticas determinísticas e
fixtures versionadas. Identificadores excluídos pelo contrato de revisão não
podem ser usados em benchmark, calibração ou validação. Dados operacionais,
privados ou holdout não são abertos automaticamente.

## Registro mínimo de uma execução

O relatório de teste deve informar:

- comando e nível executado;
- sistema operacional e Python efetivo;
- versões ou hashes das ferramentas reais;
- duração, total de testes, falhas e skips;
- hash do lock e resultado da verificação do ambiente ativo;
- declaração explícita de que limiares científicos não foram alterados.
