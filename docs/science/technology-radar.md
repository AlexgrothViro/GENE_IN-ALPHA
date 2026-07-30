# Radar tecnológico do Gene-In

Registro humano canônico. Uma decisão `testar` ou `observar` não autoriza adoção. Nenhuma atualização é automática; revisão humana é obrigatória. Avaliação inicial: 2026-07-11. Próxima revisão ordinária: 2026-10-11.

## Gate de adoção

Antes de entrar no fluxo oficial, a tecnologia precisa de finalidade documentada, licença compatível, versão/commit fixado, revisão de manutenção/testes/segurança, teste isolado e integrado, benefício mensurável, ausência de mudança silenciosa, fallback explícito, registro no manifesto e explicação no dashboard. Mudanças de evidência exigem aprovação científica.

## Modelo de entrada

`id`; nome; repositório/documentação; versão/tag/commit; datas de avaliação e reavaliação; licença/SPDX; manutenção; problema; benefícios geral e para pequenos fragmentos; ganho científico/operacional; testes/documentação; dependências; Linux/WSL; custo; segurança/abandono; reprodutibilidade; alternativa interna; validação local; decisão; revisores; justificativa.

## RADAR-001 — RO-Crate

- Fonte: https://www.researchobject.org/ro-crate/specification.html
- Versão avaliada: 1.3.0; licença: Apache-2.0; decisão: **testar**.
- Problema: empacotamento interoperável de artefatos e proveniência.
- Benefício para pequenos fragmentos: vincular fragmentos, loci, painel, parâmetros e controles sem alterar a política de evidência.
- Ganho: operacional e de rastreabilidade; nenhum ganho científico presumido.
- Estado: especificação 1.3 publicada e descrita como current long-term release; comunidade e documentação ativas.
- Riscos/custo: JSON-LD e vocabulários adicionam complexidade; risco de pacote excessivo.
- Alternativa interna: `run_state.json`, `provenance.json`, hashes e manifesto do painel.
- Validação: exportador somente leitura, fixture sintético, validação de schema, comparação de hashes e teste de round-trip. Não adotar biblioteca ainda.
- Revisores: técnico e científico pendentes.

## RADAR-002 — BioCompute Object / IEEE 2791

- Fonte: https://docs.biocomputeobject.org/user_guide/
- Versão avaliada: IEEE 2791-2020; licença do schema/implementação a confirmar por componente; decisão: **observar**.
- Problema: descrição estruturada de execuções HTS e domínios de erro.
- Benefício para pequenos fragmentos: possível contrato formal para parâmetros e limites de validade.
- Ganho: proveniência; orientação regulatória não é objetivo atual.
- Riscos/custo: complexidade e adequação regulatória superiores ao necessário no alpha; licenças precisam ser avaliadas por artefato.
- Alternativa interna: schema Evidence V2 e RO-Crate em avaliação.
- Validação: mapear um run sintético sem implementar exportação; decisão posterior.
- Revisores: técnico e científico pendentes.

## RADAR-003 — CWL 1.2 e CWLProv

- Fonte: https://www.commonwl.org/specification/
- Versão avaliada: CWL Standards 1.2.0; licença por componente a confirmar; decisão: **observar**.
- Problema: interoperabilidade de ferramentas de linha de comando e proveniência.
- Benefício para pequenos fragmentos: indireto, via reprodutibilidade do benchmark.
- Ganho: operacional.
- Riscos/custo: migração de shell durante alpha desviaria o foco e poderia alterar comportamento.
- Alternativa interna: entrypoints shell transacionais e contratos Python.
- Validação: apenas comparação de contratos; nenhuma migração no alpha.
- Revisores: técnico pendente; científico não aplicável até afetar execução.

## RADAR-004 — Snakemake

- Fonte: https://snakemake.readthedocs.io/en/stable/
- Versão observada: documentação 9.23.1; licença por release a confirmar; decisão: **observar**.
- Problema: retomada, DAG, ambientes e relatórios portáveis.
- Benefício para pequenos fragmentos: indireto, por testes e repetibilidade.
- Ganho: operacional.
- Riscos/custo: nova linguagem/runtime e migração ampla; nenhuma substituição sem benchmark operacional.
- Alternativa interna: estado de 12 etapas e promoção atômica.
- Validação: protótipo externo de um fixture, sem entrada no núcleo.
- Revisores: técnico pendente.

## RADAR-005 — Nextflow e nf-test

- Fontes: https://www.nextflow.io/docs/latest/ e https://www.nf-test.com/docs/testcases/nextflow_pipeline/
- Versão/commit: não fixado; licença por projeto/release a confirmar; decisão: **observar**.
- Problema: execução reprodutível e testes de pipeline com estado, erro e trace.
- Benefício para pequenos fragmentos: indireto, pela matriz sintética e estabilidade entre repetições.
- Ganho: operacional.
- Riscos/custo: Java/Groovy, migração e sobreposição com arquitetura atual.
- Alternativa interna: `unittest`, executáveis falsos e estado transacional.
- Validação: estudar padrões de assertions e snapshots; não executar ou incorporar no alpha.
- Revisores: técnico pendente.

## RADAR-006 — Galaxy

- Fonte: https://galaxyproject.org/galaxy-project/
- Versão: não aplicável à observação de UX; licença por componente a confirmar; decisão: **observar UX**.
- Problema: acessibilidade, histórico e transparência para pesquisadores sem terminal.
- Benefício para pequenos fragmentos: comunicação clara entre fragmento exploratório, locus e evidência agregada.
- Ganho: operacional/usabilidade.
- Riscos/custo: Galaxy como dependência seria excessivo e deslocaria o escopo.
- Alternativa interna: dashboard Python/HTML/JS local.
- Validação: heurística de UX e testes com três perfis; não incorporar Galaxy.
- Revisores: UX/técnico pendentes.

## RADAR-007 — UMI-tools

- Fonte: https://umi-tools.readthedocs.io/en/stable/reference/dedup.html
- Versão: fixar após ambiente Linux validado; licença: MIT declarada pelo projeto, a confirmar no pacote fixado; decisão: **testar**.
- Problema: deduplicação molecular orientada por UMI.
- Benefício para pequenos fragmentos: distinguir moléculas de duplicação técnica no suporte das reads.
- Ganho: científico potencial, dependente do desenho da biblioteca.
- Estado: documentação descreve deduplicação por coordenada+UMI, `--paired`, pares quiméricos e reads sem mate; comportamento padrão exige avaliação conservadora.
- Riscos/custo: dependências Python/pysam; escolhas aleatórias em empates; defaults para pares quiméricos/órfãos podem não servir ao Gene-In.
- Alternativa interna: deduplicação posicional shotgun, explicitamente não molecular.
- Validação: paired-end, read name/tag, UMI ausente/inválido, quimérico, órfão, seed/repetibilidade e falha. Indisponibilidade deve gerar `UMI_DEDUP_UNAVAILABLE`.
- Revisores: técnico e científico pendentes.

## RADAR-008 — AGENTS.md

- Fonte: https://github.com/openai/agents.md
- Versão: commit deve ser fixado apenas se houver ferramenta consumidora; licença: MIT; decisão: **testar**.
- Problema: comunicar invariantes a agentes de programação.
- Benefício para pequenos fragmentos: impedir promoção silenciosa e mudança não revisada de limiares.
- Ganho: governança operacional.
- Riscos/custo: instruções não são mecanismo de segurança nem substituem testes/revisão.
- Alternativa interna: documentação e revisão humana.
- Validação: auditoria de mudanças assistidas e teste determinístico dos invariantes.
- Revisores: técnico e científico pendentes.

## RADAR-009 — conda-lock

- Fonte: ferramenta local `conda-lock` 4.0.2; decisão: **adotar para reprodutibilidade operacional**.
- Problema: o YAML declarativo não fixa builds nem hashes dos pacotes Linux.
- Uso limitado: gerar `conda-linux-64.lock` explícito e seu manifesto de hash; o preflight bloqueia execuções quando qualquer um divergir.
- Riscos/custo: resolver o ambiente depende de rede e da disponibilidade dos canais; o lock não substitui validação científica em ambiente limpo.
- Validação: teste de adulterar o lock mantendo timestamps, preflight bloqueado e proveniência com hash do lock.

## Gatilhos de revisão

- Antes de nova dependência ou fase; antes de alpha/beta/release; trimestralmente durante desenvolvimento; e imediatamente após alerta de segurança, abandono ou mudança de licença.
