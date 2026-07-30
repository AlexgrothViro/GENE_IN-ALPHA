# Documentação do Gene-In

Índice da documentação técnica e científica do projeto. Para uma visão geral e instalação rápida, veja o [README principal](../README.md) (ou o [README em inglês](../README.en.md)).

## Primeiros passos

| Documento | Conteúdo |
|---|---|
| [`getting-started/instalacao-linux.md`](getting-started/instalacao-linux.md) | Instalação em Linux nativo via micromamba |
| [`getting-started/instalacao-windows.md`](getting-started/instalacao-windows.md) | Instalação no Windows via WSL2 |
| [`getting-started/guia-rapido-windows.md`](getting-started/guia-rapido-windows.md) | Guia rápido de permissões (Windows, WSL, admin, rede) |
| [`getting-started/modo-de-uso.md`](getting-started/modo-de-uso.md) | Manual de uso e execução via linha de comando |
| [`getting-started/painel-ux.md`](getting-started/painel-ux.md) | Painel web (dashboard) de uso local |
| [`getting-started/offline.md`](getting-started/offline.md) | Preparação do modo offline (bundle WSL) |
| [`getting-started/adicionando-hospedeiro.md`](getting-started/adicionando-hospedeiro.md) | Como configurar o filtro de outro hospedeiro |
| [`getting-started/troubleshooting.md`](getting-started/troubleshooting.md) | Solução de problemas comuns |

## Arquitetura e contrato científico

| Documento | Conteúdo |
|---|---|
| [`architecture/escopo-e-invariantes.md`](architecture/escopo-e-invariantes.md) | Objetivo do projeto e limites científicos obrigatórios |
| [`architecture/contrato-evidence-v2.md`](architecture/contrato-evidence-v2.md) | Contrato público Evidence V2 (`execution_status`, `analysis_outcome`, `evidence_level`) |
| [`architecture/arquitetura-e-fluxos.md`](architecture/arquitetura-e-fluxos.md) | Fluxos do pipeline (Gene-In 1.1 e Evidence V2) |
| [`architecture/validacao-e-exclusoes.md`](architecture/validacao-e-exclusoes.md) | Regras de interpretação de status e exclusões |
| [`architecture/terminologia.md`](architecture/terminologia.md) | Termos científicos preferidos e proibidos |
| [`architecture/dashboard-saidas-e-interpretacao.md`](architecture/dashboard-saidas-e-interpretacao.md) | Papel do dashboard e uso das saídas interpretativas |
| [`architecture/artifacts.md`](architecture/artifacts.md) | Artefatos gerados por amostra para auditoria |
| [`architecture/scripts-matrix.md`](architecture/scripts-matrix.md) | Matriz de scripts e pontos de entrada oficiais |

## Validação científica

| Documento | Conteúdo |
|---|---|
| [`science/validacao-cientifica.md`](science/validacao-cientifica.md) | Estado científico e interpretação da classificação |
| [`science/validation-status.md`](science/validation-status.md) | Estado de validação (implementado × fixture × ferramenta real) |
| [`science/e1-activation-decision.md`](science/e1-activation-decision.md) | Decisão de ativação do teto E1 |
| [`science/fontes-cientificas.md`](science/fontes-cientificas.md) | Registro de fontes científicas e operacionais consultadas |
| [`science/technology-radar.md`](science/technology-radar.md) | Radar tecnológico e gate de adoção de dependências |

## Qualidade e testes

| Documento | Conteúdo |
|---|---|
| [`quality/checklist-revisao-codigo.md`](quality/checklist-revisao-codigo.md) | Checklist de revisão de código (contrato, agregação, gates) |
| [`quality/testing-tiers.md`](quality/testing-tiers.md) | Níveis de teste e o que cada um demonstra |
| [`quality/release-checklist.md`](quality/release-checklist.md) | Checklist de publicação pública / release |
| [`quality/usability-checklist.md`](quality/usability-checklist.md) | Checklist manual de usabilidade do dashboard |
| [`quality/usability-test-plan.md`](quality/usability-test-plan.md) | Plano de teste de usabilidade (Evidence V2) |

## Outras referências no repositório

- [`AGENTS.md`](../AGENTS.md) — invariantes para engenharia e revisão.
- [`CHANGELOG.md`](../CHANGELOG.md) — histórico de mudanças do projeto.
- [`bundle/README_BUNDLE.md`](../bundle/README_BUNDLE.md) — pacote de execução rápida (WSL bundle).
- [`scripts/legacy/README.md`](../scripts/legacy/README.md) — scripts legados mantidos para auditoria.

> Notas internas de desenvolvimento, auditorias pontuais e relatórios de estado técnico histórico ficam em `internal/`, fora do controle de versão — não fazem parte desta documentação pública.
