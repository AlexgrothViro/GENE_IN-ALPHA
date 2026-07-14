# Checklist de Preparação para Liberação Pública (Release Checklist)

Este checklist descreve as verificações obrigatórias de integridade, privacidade e segurança que devem ser executadas e marcadas antes de qualquer liberação pública real do **Gene-In**.

---

## Verificação de Conteúdo e Higienização

- [x] **Linguagem operacional de processo acadêmico removida:** Todas as referências internas a bancas, qualificações, orientador e capítulos de dissertação foram removidas.
- [x] **Seção de citação deliberada presente:** A seção "Citação e origem acadêmica" está inserida de forma exclusiva no `README.md`, garantindo transparência científica sem misturar com instruções operacionais.
- [x] **Termos sensíveis buscados e tratados:** Buscas minuciosas por `Feevale`, `Spilki` e termos associados foram executadas e as ocorrências removidas de arquivos de código, HTML e estilos.
- [x] **Nenhum caminho absoluto de máquina restante:** Todas as rotas absolutas de máquina pessoal, montagens locais do WSL e atalhos binários locais `.lnk` foram limpos do repositório.
- [x] **Ausência de dados privados e relatórios internos:** O relatório `docs/AUDITORIA_GERAL.md`, a pasta `data/auditoria/` e todos os arquivos de dados brutos e montagem/BLAST da dissertação (`LOW_*`, `POS_*`, `NEG_*`, `BENCH_*`) não estão presentes nesta branch.
- [x] **LICENSE definido:** O projeto utiliza licença pública limitada de uso, sem conflito com licença MIT ou licença pendente.
- [x] **README.md revisado:** A seção 5 de status de validação foi generalizada de forma a resguardar os dados brutos e estatísticas específicas não publicados, mantendo a credibilidade metodológica de validação pública.

---

## Integridade de Código e Testes

- [x] **scripts/tests/run_smoke_test.sh presente:** O script de teste de fumaça sintético foi criado e validado localmente, finalizando com status `PASS` sem qualquer dependência de SRA ou arquivos de dados da matriz de validação.
- [x] **run_full_validation.sh não está presente:** O script privado de regressão completa foi devidamente excluído da branch pública.
- [x] **docs/USABILITY_CHECKLIST.md presente:** O checklist de navegação e tratamento de erros do dashboard foi documentado de forma clara.

---

## Integridade entre Branches

- [x] **Frase sobre "segurança total" corrigida na fonte:** O relatório de auditoria na branch `local/auditoria-geral` foi modificado para substituir a afirmação excessiva sobre injeção de comandos por um aviso defensivo e realista de hardening local.
- [x] **Confirmação de que local/auditoria-geral permanece intacta:** A branch de auditoria privada permaneceu inalterada e resguardada após todas as edições realizadas na branch de preparação pública.
