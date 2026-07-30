# Dashboard, saídas e interpretação

## Papel do dashboard

O dashboard é uma interface local para:

- preflight;
- importação e organização de amostras/lotes;
- configuração guiada;
- início, acompanhamento e cancelamento de execuções;
- histórico;
- logs;
- visualização e download de artefatos.

Ele não é autoridade científica. Deve consumir a decisão canônica da Evidence V2.

## Estados que precisam permanecer distintos

- execução: em fila, executando, concluída, bloqueada, falhou, cancelada;
- outcome: `EVIDENCE_RECOVERED`, `NO_EVIDENCE_RECOVERED`, `NOT_EVALUABLE`;
- evidência: `E1` ou `NOT_EVALUABLE` em Alpha.2;
- conclusão reportada: `SHADOW_ONLY`;
- gates, caveats, controles e limitações.

## Saídas esperadas

O código atual deve ser comparado com schemas e contratos versionados no repositório. Entre os artefatos esperados estão:

- evidência por fragmento;
- evidência por locus;
- cobertura;
- evidência por amostra em JSON;
- relatório interpretativo;
- `run.json`;
- logs;
- manifesto/proveniência;
- artefatos auxiliares de sidecars.

Nomes exatos e obrigatoriedade devem vir do contrato da versão executada, não deste resumo.

## Integridade de botões e downloads

- Cada botão deve ter destino real, autorização e tratamento de erro.
- “Baixar resultado” deve apontar para artefato validado, não working file.
- Um erro de geração deve impedir que o botão sugira sucesso.
- O usuário deve saber se o arquivo é 1.1, V2 experimental ou sidecar.
- A interface deve explicar por que um resultado está `NOT_EVALUABLE`.
- Ações incompatíveis com `shadow_mode` não podem parecer disponíveis.

## Regras para camadas interpretativas

Qualquer camada que resuma, explique ou reorganize artefatos deve:

- permanecer subordinada ao `sample_evidence.json` canônico;
- apontar para o arquivo e campo que sustentam cada afirmação;
- preservar caveats, gates, controles e bloqueios;
- não classificar fragmentos, recalcular gates ou elevar `E1` para `E2/E3/E4`;
- declarar quando a informação solicitada não existe no artefato-fonte.

## Pendências de fechamento registradas

- auditoria visual e de integridade do dashboard;
- auditoria das saídas;
- verificação do direcionamento dos botões;
- teste de cancelamento real;
- alinhamento entre APIs existentes e ações visíveis.
