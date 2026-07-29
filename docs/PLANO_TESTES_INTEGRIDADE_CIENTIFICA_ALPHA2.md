# Plano de testes, integridade e qualificação científica — Gene-In 2.0 alpha.2

**Data:** 2026-07-16  
**Escopo:** versão `2.0.0-alpha.2`, Evidence V2 em `shadow_mode`; Gene-In 1.1 permanece a versão oficial.  
**Objetivo:** produzir evidência rastreável de que a nova versão funciona no ambiente real e medir, sem extrapolação, seus limites científicos.

## 1. Veredito antes de testar

**A versão pode iniciar validação operacional, mas ainda não está qualificada para sair de `shadow_mode` nem para emitir conclusão biológica.**

Os testes unitários e de contrato demonstram comportamento de software. A qualidade científica só poderá ser discutida após execução ponta a ponta, controles adequados, repetição independente e benchmark próprio congelado. Mesmo então, a alpha.2 só pode emitir `E1` ou `NOT_EVALUABLE`; E1 é evidência computacional exploratória e não demonstra presença, identidade, linhagem, variante ou infecção.

## 2. Estado de partida

| Item | Estado canônico informado | Implicação para o plano |
|---|---|---|
| Versão | `2.0.0-alpha.2` | Registrar commit e hashes antes de executar. |
| Evidence V2 | `shadow_mode` | Não alterar limiares, níveis ou a linguagem pública durante os testes. |
| Gene-In 1.1 | Oficial e preservado | Falha da V2 não pode substituir ou apagar o resultado da 1.1. |
| WSL e ferramentas principais | Disponíveis e funcionais | Executar os testes reais no WSL e salvar todos os logs. |
| PyYAML | Confirmado em `/usr/bin/python` | Verificar também o Python que o pipeline/bundle realmente usará. |
| UMI-tools | Ausente | Iniciar com `umi_mode=none`; não validar bibliotecas com UMI até suprir a dependência. |
| Node.js | Ausente | O painel Python pode ser exercitado, mas `node --check dashboard/app.js` fica bloqueado. |
| ShellCheck | Executado, com pendências | Tratar qualquer warning como falha do gate até correção ou justificativa local auditável. |
| Testes Python | Contagem a confirmar | Gerar um log reproduzível; não repetir números históricos sem a saída correspondente. |
| Execução real, repetibilidade, dashboard e benchmark | Pendentes/bloqueados | São os gates que impedem qualificação científica. |
| Ferramentas sidecar | Apenas planejadas | Não as usar como dependência, evidência ou critério de aceite desta versão. |

## 3. Regras de integridade que não podem ser flexibilizadas

1. Use apenas fixtures sintéticas, controles públicos ou dados formalmente autorizados.
2. Execute a validação em uma cópia identificável do código. Se o worktree estiver alterado, registre o diff; não chame o resultado de *release candidate* sem snapshot.
3. Mantenha staging e destino no mesmo sistema de arquivos. `SUCCESS.json` deve existir somente após a validação completa e a promoção atômica.
4. Registre data, commit, comandos, versões, hashes de banco/painel e cada arquivo de entrada.
5. Para cada teste, declare antes: o que deve passar, o que deve falhar e qual artefato comprova o resultado.
6. Não considere o exit code do fluxo 1.1 como aprovação da V2: o pipeline foi projetado para preservar a 1.1 quando a Evidence V2 falha.
7. Não use dados operacionais não autorizados para benchmark, calibração, artigo, dissertação ou alegação científica.

## 4. Fase 0 — congelar a fotografia e criar o dossiê de execução

Execute no WSL, na raiz do repositório. Substitua o caminho se o checkout estiver em outro local.

```bash
cd ~/Gene-In-stability

export VALIDATION_ID="alpha2-$(date -u +%Y%m%dT%H%M%SZ)"
export VALIDATION_DIR="logs/validation/${VALIDATION_ID}"
mkdir -p "$VALIDATION_DIR"

git status --short | tee "$VALIDATION_DIR/git-status.txt"
git rev-parse HEAD | tee "$VALIDATION_DIR/git-commit.txt"
git diff --check | tee "$VALIDATION_DIR/git-diff-check.txt"
git diff --name-only | tee "$VALIDATION_DIR/git-modified-files.txt"
cp VERSION "$VALIDATION_DIR/VERSION"
sha256sum conda-linux-64.lock config/environment_lock.json config/evidence_v2.yaml \
  | tee "$VALIDATION_DIR/core-inputs.sha256"
```

**Aceite:** existe um diretório de validação com commit, estado do worktree, versão e hashes. Se `git status --short` não estiver vazio, o relatório deve declarar que a validação é do worktree identificado, não de uma release imutável.

## 5. Fase 1 — ambiente real, lock e pré-flight

Esta fase confirma o Python efetivo, o lockfile e as ferramentas usadas na V2. Ela não instala nada automaticamente.

```bash
set -o pipefail

bash scripts/00_check_env.sh \
  2>&1 | tee "$VALIDATION_DIR/01-check-env.log"

python3 scripts/evidence/environment_lock.py \
  --lockfile conda-linux-64.lock \
  --manifest config/environment_lock.json \
  2>&1 | tee "$VALIDATION_DIR/02-lock-validation.log"

python3 scripts/evidence/runtime_preflight.py \
  --config config/evidence_v2.yaml \
  --assembler spades \
  --umi-mode none \
  --require-command blastn \
  --require-command bowtie2 \
  --require-command samtools \
  --lockfile conda-linux-64.lock \
  --lock-manifest config/environment_lock.json \
  --json-out "$VALIDATION_DIR/runtime-preflight.json" \
  2>&1 | tee "$VALIDATION_DIR/03-runtime-preflight.log"

if [[ -x bundle/env/bin/python ]]; then
  bundle/env/bin/python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)' \
    2>&1 | tee "$VALIDATION_DIR/04-bundle-python.log"
else
  printf '%s\n' 'Bundle Python não encontrado neste checkout; verificação pendente.' \
    | tee "$VALIDATION_DIR/04-bundle-python.log"
fi
```

**Aceite:** `runtime-preflight.json` contém `"valid": true`, o lock é válido e o log identifica o executável Python usado.  
**Bloqueios explícitos:**

- Se a biblioteca tiver UMI, não use `umi_mode=none` como substituto da validação UMI; instale/aprove UMI-tools e repita o pré-flight com o modo correto.
- Se o Python do bundle não tiver PyYAML, a V2 deve permanecer bloqueada mesmo que `/usr/bin/python` funcione.
- Não execute `make deps` ou scripts de instalação sem uma decisão documentada de dependências; isso altera o ambiente e não é uma verificação neutra.

## 6. Fase 2 — testes de software e análise estática

### 6.1 Testes Python com contagem reproduzível

```bash
set -o pipefail
python3 -m unittest discover -s scripts/tests -p 'test_*.py' \
  2>&1 | tee "$VALIDATION_DIR/10-python-unittest.log"
test "${PIPESTATUS[0]}" -eq 0

python3 -m compileall -q scripts \
  2>&1 | tee "$VALIDATION_DIR/11-python-compileall.log"
test "${PIPESTATUS[0]}" -eq 0
```

O log de `unittest` passa a ser a fonte canônica da contagem, duração e resultado. Não registrar apenas “passou”.

### 6.2 Shell

```bash
set -o pipefail
while IFS= read -r script; do
  bash -n "$script"
done < <(git ls-files '*.sh') \
  2>&1 | tee "$VALIDATION_DIR/12-bash-n.log"
test "${PIPESTATUS[0]}" -eq 0

shellcheck --severity=warning $(git ls-files '*.sh') \
  > "$VALIDATION_DIR/13-shellcheck.log" 2>&1
shellcheck_rc=$?
printf 'shellcheck_exit_code=%s\n' "$shellcheck_rc" \
  | tee "$VALIDATION_DIR/13-shellcheck-status.txt"
test "$shellcheck_rc" -eq 0
```

**Aceite:** `bash -n` e ShellCheck retornam zero. Warnings não devem ser escondidos por supressão global. Caso exista uma exceção inevitável, ela precisa ser local, justificada e revisada antes de se considerar o gate concluído.

### 6.3 JavaScript e painel

Com Node.js ausente, registre o gate como **BLOQUEADO**, sem marcar como aprovado:

```bash
command -v node || printf '%s\n' 'BLOCKED: Node.js ausente; node --check não executado.' \
  | tee "$VALIDATION_DIR/14-node-check.log"
```

Após a instalação autorizada do Node.js, execute:

```bash
node --check dashboard/app.js \
  2>&1 | tee "$VALIDATION_DIR/14-node-check.log"
```

## 7. Fase 3 — smoke test real e integridade da 1.1

O alvo `make smoke-test` prepara banco e referência; ele só é reprodutível se a referência, o banco e suas versões estiverem congelados no dossiê. Não trate um download corrente como referência científica fixa.

```bash
set -o pipefail
make test-env \
  2>&1 | tee "$VALIDATION_DIR/20-test-env.log"
test "${PIPESTATUS[0]}" -eq 0

make smoke-test \
  2>&1 | tee "$VALIDATION_DIR/21-smoke-test.log"
test "${PIPESTATUS[0]}" -eq 0
```

Depois do smoke test, arquive hashes da referência, dos índices e dos outputs gerados. A confirmação mínima é: FASTA, banco BLAST, índice Bowtie2, execução de `blastn` e sintaxe dos scripts críticos válidos.

**Ressalva:** esse smoke test demonstra operacionalidade básica. Ele não testa controles de lote, painel competitivo completo, repetibilidade científica nem a qualidade de uma chamada viral.

## 8. Fase 4 — Evidence V2 ponta a ponta com painel competitivo

Esta é a fase que valida o contrato V2 com ferramentas reais. Não use somente um banco alvo; o painel precisa conter as seis categorias exigidas:

- `TARGET_VIRUS`;
- `NEAR_NON_TARGET_VIRUS`;
- `HOST`;
- `VECTOR_ADAPTER`;
- `KNOWN_CONTAMINANT`;
- `SYNTHETIC_SEQUENCE`.

Construa o painel somente com FASTAs versionados/autorizados. Exemplo estrutural:

```bash
export PANEL_ID="${VALIDATION_ID}-competitive"

bash scripts/24_build_competitive_db.sh \
  --panel-id "$PANEL_ID" \
  --source TARGET_VIRUS=/caminho/congelado/target.fa \
  --source NEAR_NON_TARGET_VIRUS=/caminho/congelado/near_non_target.fa \
  --source HOST=/caminho/congelado/host.fa \
  --source VECTOR_ADAPTER=/caminho/congelado/vector_adapter.fa \
  --source KNOWN_CONTAMINANT=/caminho/congelado/contaminants.fa \
  --source SYNTHETIC_SEQUENCE=/caminho/congelado/synthetic.fa \
  2>&1 | tee "$VALIDATION_DIR/30-build-competitive-panel.log"

export PANEL_ROOT="ref/evidence_panels/panels/${PANEL_ID}"
sha256sum "$PANEL_ROOT/panel.fa" "$PANEL_ROOT/labels.tsv" "$PANEL_ROOT/panel_manifest.json" \
  | tee "$VALIDATION_DIR/31-competitive-panel.sha256"
```

Use uma entrada sintética ou pública autorizada e rode o fluxo com a V2 explicitamente habilitada:

```bash
export EVIDENCE_V2=true
export EVIDENCE_ROOT="results/evidence-validation/${VALIDATION_ID}"
export EVIDENCE_COMPOSITE_DB="$PANEL_ROOT/blast/panel"
export EVIDENCE_SUBJECT_LABELS="$PANEL_ROOT/labels.tsv"
export EVIDENCE_PANEL_FASTA="$PANEL_ROOT/panel.fa"
export EVIDENCE_PANEL_INDEX="$PANEL_ROOT/bowtie2/panel"
export EVIDENCE_UMI_MODE=none
export EVIDENCE_RUN_ID="${VALIDATION_ID}-positive"

make run SAMPLE=POS_SYNTHETIC \
  R1=/caminho/autorizado/POS_SYNTHETIC_R1.fastq.gz \
  R2=/caminho/autorizado/POS_SYNTHETIC_R2.fastq.gz \
  DB=ptv ASSEMBLER=spades \
  2>&1 | tee "$VALIDATION_DIR/32-v2-positive.log"
```

**Não use apenas o retorno de `make run` como aceite.** Confira o estado e os artefatos V2:

```bash
RUN_DIR="$EVIDENCE_ROOT/runs/$EVIDENCE_RUN_ID"
test -s "$RUN_DIR/SUCCESS.json"
test -s "$RUN_DIR/artifact_manifest.json"
test -s "$RUN_DIR/sample_evidence.json"
test -s "$RUN_DIR/provenance.json"

python3 scripts/evidence/validate_run_artifacts.py --dir "$RUN_DIR" \
  2>&1 | tee "$VALIDATION_DIR/33-v2-artifact-validation.log"

python3 - "$RUN_DIR/sample_evidence.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
assert value["shadow_mode"] is True
assert value["reported_conclusion"] == "SHADOW_ONLY"
assert value["evidence_level"] in {"E1", "NOT_EVALUABLE"}
print({key: value[key] for key in ("execution_status", "analysis_outcome", "evidence_level", "reported_conclusion")})
PY
```

**Aceite:** `SUCCESS.json` foi escrito, a validação de artefatos passou, o manifesto é íntegro e a saída pública continua `SHADOW_ONLY`. Um sinal positivo sintético ainda é, nesta versão, no máximo E1.

## 9. Fase 5 — matriz científica mínima

Execute cada cenário em execução separada, com `run_id`, painel, banco e hashes próprios. Para cada linha, salve o relatório V2, `sample_evidence.json`, `provenance.json`, `artifact_manifest.json`, `SUCCESS.json`, logs e uma ficha de resultado esperado.

| Cenário | Resultado esperado | O que invalida o teste |
|---|---|---|
| Positivo sintético conhecido | Evidência recuperada, sem promoção acima de E1 | Resultado sem proveniência, painel incompleto ou linguagem de presença/identidade. |
| Negativo de extração/biblioteca/corrida | Sem promoção; alerta/controle coerente | Interpretar lista vazia como ausência biológica. |
| Sequência de hospedeiro | Não pode ser promovida como alvo viral | Métrica de suporte do hospedeiro elevar candidato viral. |
| Vetor/adaptador/contaminante | Especificidade bloqueada ou competidor melhor | Sinal técnico ser apresentado como evidência viral. |
| Competidor viral próximo | `AMBIGUOUS` ou `NON_TARGET_BEST` quando aplicável | Alvo ser rotulado específico sem margem competitiva. |
| Fragmento fora do span informativo | Gate filogenético bloqueado | Sítios apenas das referências inflarem a conclusão. |
| Falta de PyYAML, banco ou índice | `NOT_EVALUABLE`/falha documentada; sem `SUCCESS.json` | Artefato parcial promovido como execução concluída. |
| Cancelamento/falha injetada | Estado falho/cancelado; execução anterior preservada | Processo órfão, estado `done` indevido ou promoção parcial. |

Para controles de lote, inclua padrão de potencial doador→receptor, negativeome, dados de host/vetor/contaminante e metadados de corrida. Uma razão amostra/controle altera apenas `control_status`; não confirma contaminação nem identifica agente.

## 10. Fase 6 — repetibilidade, transações e dashboard

### Repetibilidade

1. Reexecute o mesmo cenário em novo `run_id`, no mesmo ambiente congelado.
2. Compare hashes de entradas, configuração, painel, banco e versões de ferramentas.
3. Compare outcomes, gates, candidatos, status de especificidade, cobertura e controles. Diferenças devem ser explicadas antes de aceitar o teste.
4. Repita em ambiente Linux limpo ou CI, a partir do lockfile, sem reutilizar cache ou staging da primeira execução.

### Falhas transacionais

Injete falhas controladas em pelo menos uma etapa antes da promoção e verifique:

- não há `SUCCESS.json` no staging nem no destino final;
- o estado da execução é `failed` ou `cancelled`, nunca `done`;
- a execução válida anterior permanece legível;
- BAM e BAI, quando existentes, passam em `samtools quickcheck`;
- não restam arquivos temporários no diretório promovido.

### Dashboard

Com o servidor local em execução, faça revisão visual dos três estados: E1 com candidato, E1 sem candidatos e `NOT_EVALUABLE`. Em cada tela, confirme:

- `shadow_mode`, outcome, caveats e gates bloqueados estão visíveis;
- não aparece linguagem de presença, ausência, confirmação, variante ou linhagem;
- a aba aberta antes de uma promoção busca o resultado canônico novo, sem cache legado;
- cancelamento, erro e artefato incompleto são compreensíveis e não aparentam sucesso.

O teste visual pode ser realizado sem Node.js; porém a verificação estática de `dashboard/app.js` continua pendente até a instalação autorizada do Node.

## 11. Fase 7 — qualidade científica e benchmark

**Veredito de aplicabilidade atual: NÃO APLICÁVEL para liberar mudança científica.** Ainda não há benchmark próprio, congelado e reproduzível no regime de uso do Gene-In.

Antes de calibrar limiar, selecionar montador, habilitar E2/E3 ou alegar desempenho, defina e congele:

1. população-alvo, prevalência esperada e custo de falsos positivos/falsos negativos;
2. dados públicos/sintéticos autorizados, banco, taxonomia e data de corte;
3. unidade independente antes de fragmentar: genoma, espécie, amostra e projeto;
4. holdouts espécie-, gênero-, família- e temporalmente independentes; split aleatório não serve para congelar limiar;
5. negativeome de hospedeiro, microbioma, reagentes, ambiente, vetores e contaminantes;
6. cenários de index hopping e de baixa cobertura;
7. faixas de comprimento: 20–49, 50–79, 80–149, 150–299, 300–499 e ≥500 pb;
8. AUPRC, precisão, recall, F1 e falsos positivos absolutos nos pontos operacionais; AUROC é complementar;
9. repetibilidade, estabilidade de montagem/filogenia e comportamento OOD;
10. regras de abstenção e todos os gates não avaliáveis.

Para 20–79 pb, ML deve permanecer abstido; não usar desempenho de contigs longos para validar fragmentos curtos. Se algum método de ML for avaliado a partir de 150 pb, ele permanece feature auxiliar E1, com calibração por comprimento, avaliação OOD, curva risco–cobertura e validação externa.

## 12. Critério de encerramento

| Nível de aceite | Condição |
|---|---|
| Integridade de software | Fases 0–3 passam, sem falha oculta no ShellCheck e com logs/versões/hashes preservados. |
| Integridade V2 | Fases 4 e 6 passam: painel completo, artefatos válidos, promoção atômica, falhas contidas e V1.1 preservada. |
| Usabilidade | Dashboard visual e acessibilidade passam nos três estados obrigatórios. |
| Qualidade científica para shadow mode | Fase 5 passa com controles e repetição, mas a saída continua E1/`SHADOW_ONLY`. |
| Elegibilidade para discutir promoção futura | Fase 7 concluída com benchmark próprio, independência, prevalência e revisão científica documentadas. Isso exige nova decisão formal; não é efeito automático deste plano. |

## 13. Entregáveis obrigatórios

Ao final, mantenha um único diretório de dossiê contendo:

- identificação da versão, commit e estado do worktree;
- logs de ambiente, lock, preflight, testes Python, `bash -n`, ShellCheck e Node (ou bloqueio);
- hashes de referência, banco, painel competitivo, configuração e entradas;
- artefatos V2 por cenário, incluindo `SUCCESS.json` e manifesto;
- matriz de resultados esperado/observado, desvios, causa, correção e reteste;
- resultado da revisão visual;
- parecer técnico-científico final, assinado por responsável humano, que mantenha ou não o `shadow_mode`.

## 14. Próxima ação recomendada

Comece pelas Fases 0 e 1. Se o pré-flight da Evidence V2 passar com o Python efetivo e o lock, execute a Fase 2 e corrija o ShellCheck antes de investir em dados de controle. Depois construa o painel competitivo com fontes congeladas e rode os três primeiros cenários da Fase 5: positivo sintético, negativo e competidor próximo.

Nenhum passo deste plano autoriza mudança de limiar, promoção de E1, saída de `shadow_mode` ou uso de dados não autorizados.
