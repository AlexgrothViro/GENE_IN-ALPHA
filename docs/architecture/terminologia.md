# Terminologia científica

## Usar

- fragmento viral candidato;
- sequência viral candidata;
- evidência molecular compatível;
- similaridade com sequência viral de referência;
- classificação operacional;
- triagem bioinformática;
- recuperação de fragmentos;
- interpretação conservadora;
- validação complementar;
- requer revisão manual;
- não foram recuperadas evidências classificáveis;
- resultado não avaliável;
- especificidade competitiva;
- suporte nas reads;
- cobertura não redundante;
- loci independentes;
- caveat;
- abstenção.

## Evitar ou proibir sem evidência externa apropriada

- confirmou presença;
- vírus presente;
- diagnóstico definitivo;
- detecta automaticamente;
- identificação garantida ou inequívoca;
- elimina falsos positivos;
- exclui a presença de vírus;
- substitui validação laboratorial;
- determina o agente etiológico;
- comprova infecção ou causalidade;
- genoma completo, sem suporte de extensão e cobertura;
- variante confirmada;
- pipeline superior, sem benchmark justo.

## Substituições

| Evitar | Preferir |
|---|---|
| “O pipeline confirmou o vírus.” | “O pipeline recuperou fragmentos candidatos com similaridade a sequências virais de referência.” |
| “Não havia vírus.” | “Não foram recuperadas evidências classificáveis nas condições analisadas.” |
| “A análise deu negativo.” | “A análise válida resultou em `NO_EVIDENCE`; isso não exclui material pouco abundante ou divergente.” |
| “A execução falhou e não encontrou vírus.” | “A execução foi `NOT_EVALUABLE`; nenhuma conclusão científica pode ser emitida.” |
| “Fragmento positivo de 30 bp.” | “Fragmento exploratório de 30 bp, insuficiente isoladamente para promoção.” |
| “O dashboard validou o resultado.” | “O dashboard exibiu o resultado canônico e seus gates.” |

## Regra para revisão de mensagens

Auditar strings de:

- API;
- dashboard;
- CLI;
- relatórios;
- logs;
- exceções;
- testes snapshot;
- documentação.

Uma mensagem cientificamente incorreta é defeito de produto, mesmo que o cálculo esteja correto.

