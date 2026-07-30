# Checklist de revisão de código

## 1. Contrato científico

- [ ] `execution_status`, `analysis_outcome`, `evidence_level` e `reported_conclusion` estão separados.
- [ ] Alpha.2 emite apenas `E1` ou `NOT_EVALUABLE`.
- [ ] `E2`, `E3` e `E4` são inacessíveis.
- [ ] Falha crítica produz `NOT_EVALUABLE`.
- [ ] `NO_EVIDENCE` só ocorre após análise tecnicamente válida.
- [ ] Fragmentos de `20–49 bp` não promovem conclusão isoladamente.
- [ ] Classes legadas não são confundidas com E1–E4.

## 2. Agregação e gates

- [ ] HSPs sobrepostos são unidos.
- [ ] Cobertura é não redundante.
- [ ] Loci repetidos não são contados como independentes.
- [ ] Suporte nas reads é deduplicado conforme a política.
- [ ] Especificidade competitiva preserva `AMBIGUOUS`.
- [ ] Controles bloqueiam ou limitam quando necessário.
- [ ] Proveniência, caveats e motivos de abstenção são completos.

## 3. Erros e transações

- [ ] Nenhuma falha crítica é mascarada por `|| true`.
- [ ] Não há `ignore_errors` ou `except Exception` convertendo falha em sucesso.
- [ ] Exit codes de montadores e ferramentas são propagados.
- [ ] Outputs temporários não substituem resultados válidos antes da validação.
- [ ] Falha parcial não gera relatório de sucesso.
- [ ] Cancelamento encerra processos filhos e registra estado coerente.
- [ ] Execuções concorrentes não compartilham diretórios mutáveis.

## 4. Configuração e reprodutibilidade

- [ ] Precedência de configuração é explícita e testada.
- [ ] Política e parâmetros possuem versão/hash.
- [ ] Banco possui manifesto, accessions/data e identidade.
- [ ] Versões das ferramentas são registradas.
- [ ] Runs históricos não são reclassificados silenciosamente.
- [ ] `adaptation_id` e orientação do candidato são obrigatórios quando aplicável.

## 5. Segurança e privacidade

- [ ] FASTQs, dados privados, caminhos pessoais e resultados reais não estão versionados.
- [ ] Logs não expõem informações sensíveis desnecessárias.
- [ ] IDs de amostra são validados contra path traversal e colisões.
- [ ] Uploads/caminhos do dashboard são validados.
- [ ] Comandos shell evitam interpolação insegura e globbing acidental.
- [ ] Limpezas são restritas, explícitas e recuperáveis quando possível.

## 6. Dashboard e API

- [ ] A interface não usa linguagem diagnóstica.
- [ ] Estados operacionais não são apresentados como evidência.
- [ ] Botões apontam para APIs/artefatos corretos.
- [ ] Só artefatos validados podem ser baixados como finais.
- [ ] Ações incompatíveis com `shadow_mode` ficam ocultas ou bloqueadas.
- [ ] Lote e amostra não são confundidos.
- [ ] 409/503 e falhas de polling têm mensagens úteis.
- [ ] Caminhos customizados e cancelamento real são testados.

## 7. Testes

- [ ] Unitários cobrem limites imediatamente abaixo/no/acima dos thresholds.
- [ ] Testes de contrato cobrem liberação e bloqueio.
- [ ] Fixtures são sintéticas, pequenas e determinísticas.
- [ ] Há testes de integração em Linux/WSL com ferramentas reais.
- [ ] SPAdes, metaSPAdes e Velvet são exercitados no escopo aprovado.
- [ ] Rebuilds e bancos múltiplos são verificados.
- [ ] Testes não usam `2323`, `81554` ou `81555`.
- [ ] O relatório de testes identifica commit, ambiente, skipped e falhas.

## Formato recomendado para achados

Para cada achado, registrar:

- severidade: `P0`, `P1`, `P2` ou `P3`;
- arquivo e linha;
- comportamento observado;
- risco técnico/científico;
- evidência reproduzível;
- correção mínima sugerida;
- teste de regressão necessário;
- impacto sobre validação e `shadow_mode`.

