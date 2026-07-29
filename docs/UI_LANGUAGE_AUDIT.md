# Auditoria de linguagem de saída — alpha.2

Método adotado: **revisão estática de código e contratos de dados**. Não foi feita revisão visual em navegador nesta etapa; ela continua obrigatória antes de sair de `shadow_mode`.

Escopo revisto: `dashboard/index.html`, `dashboard/app.js`, `scripts/lib/evidence_dashboard.py`, `scripts/evidence/export_evidence.py` e a rota `/api/evidence/*`.

## Strings de desempenho, confiança e validação

| Arquivo:linha | String/uso | Veredito |
|---|---|---|
| `scripts/lib/evidence_dashboard.py:50` | `TARGET_SPECIFIC`: separação do melhor alinhamento contra competidores segundo parâmetros provisórios | PASS — propriedade operacional; não chama desempenho clínico ou validado |
| `scripts/lib/evidence_dashboard.py:51` | `AMBIGUOUS`: separação competitiva insuficiente | PASS — descreve limitação operacional |
| `scripts/lib/evidence_dashboard.py:52` | `NON_TARGET_BEST`: competidor não alvo com melhor alinhamento | PASS — não afirma identidade |
| `scripts/lib/evidence_dashboard.py:56` | `GENOME_SUPPORTED`: critérios operacionais provisórios, sem confirmação diagnóstica | PASS — ressalva explícita |
| `scripts/evidence/export_evidence.py:33` | aviso de E1 sem presença, ausência, identidade ou confirmação | PASS — limitação explícita |
| `dashboard/app.js:1284` | resumo “evidência computacional experimental; requer revisão e validação complementar” | PASS — não sugere validação concluída |
| `dashboard/index.html:317` | análise complementar “não confirma infecção sozinha” | PASS — limitação explícita |
| `dashboard/index.html:359` | “IQ-TREE disponível (versão detectada)” | PASS — disponibilidade de ferramenta, não desempenho científico |

Não há strings de interface que chamem a métrica operacional de “alta sensibilidade”, “alta especificidade”, “confiável” ou “validada” no sentido clínico/diagnóstico. A ausência é resultado de busca estática nesses arquivos, não de teste de navegador.

| Superfície | Resultado | Evidência |
|---|---|---|
| API e resultado Evidence V2 | Seguro para alpha.2 | entrega somente o promotor canônico; E1 é apresentado como triagem e `SHADOW_ONLY` |
| Exportador de evidência | Seguro para alpha.2 | declaração explícita de que E1 não afirma presença, ausência, identidade ou confirmação |
| Dashboard de evidência | Seguro para alpha.2 | resumo conservador e campos separados de outcome, nível, controles e gates |
| Dashboard legado/análise complementar | Requer revisão visual posterior | texto de navegação não é uma decisão de evidência, mas deve ser verificado no navegador com artefatos reais |

Ocorrências de termos como “positivo”, “negativo”, “detectado” e “confirmação” que permanecem no escopo são restritas a controles, aviso de limitação ou negação explícita de conclusão. Nenhum desses termos pode ser usado para transformar E1 ou `NO_EVIDENCE_RECOVERED` em alegação biológica.

Roteiro pendente de revisão visual: abrir um resultado E1 com candidato, um resultado E1 sem candidatos e um `NOT_EVALUABLE`; confirmar que cada tela mostra `shadow_mode`, outcome, caveats e gates bloqueados, e que não exibe linguagem de presença, ausência, confirmação, variante ou linhagem.

Para cache, o cenário obrigatório é: abrir uma aba do dashboard antes da promoção, mantê-la aberta enquanto o servidor promove o run e confirmar que o polling busca o resultado canônico novo, sem exibir estado legado memorizado. Os cabeçalhos HTTP e `fetch(..., { cache: "no-store" })` são defesas de código; não são substituto desse teste de navegador.
