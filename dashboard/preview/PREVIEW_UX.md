# Gene-In — Preview de UX (estático)

Protótipo navegável da nova jornada guiada do dashboard. **Não altera o dashboard funcional.**
Roda 100% offline, sem backend e sem CDN. Todos os dados são fictícios (a amostra 2323 não é usada).

Branch: `ux/dashboard-guided-preview` · Sem commit/push (aguardando sua autorização).

---

## 1. Como abrir localmente (sem internet)

Basta **abrir o arquivo no navegador** — não precisa de servidor:

- Dê duplo-clique em `dashboard/preview/index.html`, ou
- Arraste `index.html` para uma aba do navegador, ou
- Menu do navegador → Abrir arquivo → selecione `index.html`.

Os scripts são carregados como `<script>` clássicos (sem ES modules), então funcionam via `file://` sem servidor. Se preferir servir por HTTP: `python3 -m http.server` dentro de `dashboard/preview/` e acesse `http://localhost:8000`.

**Como explorar:** use o seletor **"Estado simulado"** na faixa escura do topo para alternar entre os 11 cenários. A navegação principal (Início, Nova análise, Resultados, Histórico, Evidence V2) e o botão **"Ir"** do assistente de próxima ação também percorrem as telas.

---

## 2. Arquivos criados

Todos novos, dentro de `dashboard/preview/` (nada fora dessa pasta foi tocado):

| Arquivo | Papel |
|---|---|
| `index.html` | Estrutura semântica única (SPA estática): faixa do preview, cabeçalho/nav, barra de contexto, área de telas, modal. |
| `preview.css` | Tokens centralizados em `:root` (cores, espaçamentos, raios) + componentes. Paleta herdada do dashboard atual. |
| `mock-data.js` | Dados fictícios, catálogo central de rótulos/estados (linguagem conservadora) e os 11 cenários. Separado da lógica visual. |
| `preview.js` | Roteamento de telas, wizard, barra de contexto, assistente de próxima ação, gate visual, modal acessível. Sem rede. |
| `PREVIEW_UX.md` | Este documento. |

Nenhum arquivo existente foi modificado. Nenhuma biblioteca externa foi necessária (logo, nada a vendorizar para offline).

---

## 3. Mapa de telas e componentes

```
Faixa do preview (seletor dos 11 estados)      ← exclusiva do preview
Cabeçalho + navegação principal
Barra de contexto persistente                  ← ambiente · banco · amostra · execução · Evidence V2
└── Assistente "próxima ação recomendada"      ← determinístico, por estado

Telas:
  • Início           → 4 ações (Nova análise = principal, Continuar, Demonstração, Histórico)
  • Nova análise     → Wizard de 6 etapas com stepper (aria-current) + Anterior/Próximo
       1 Verificar ambiente   2 Banco viral   3 Importar amostra
       4 Configurar análise   5 Revisar       6 Executar
       └── modo simples ↔ Configuração avançada (mesma config, sem fluxos separados)
       └── gate visual: botão Executar desabilitado com o motivo quando faltam pré-requisitos
  • Revisar          → resumo com "corrigir" que leva de volta à etapa
  • Execução         → etapas em tempo real, tempo decorrido (real, sem ETA inventada),
                       log resumido + detalhes técnicos, cancelar, erro explicado
  • Resultados       → 6 camadas (estado operacional → resultado → evidência/limitações →
                       controles/cobertura/especificidade → fragmentos candidatos → artefatos)
  • Histórico        → unidades por execução, busca e filtros, parâmetros em modal, artefatos
  • Evidence V2      → tarja âmbar, badge "Experimental — shadow mode", 1.1 separado das
                       dimensões experimentais, fragmentos 20–49 pb só como exploratórios

Modal acessível (foco preso, Esc fecha, foco restaurado) — usado em "Parâmetros".
```

### Estados de execução distintos (nunca sinônimos)
`Em execução` · `Execução concluída` · `Nenhuma evidência recuperada` · `Não avaliável` · `Falha operacional` · `Execução cancelada` · `Sucesso parcial (lote)` — cada um com badge e cor próprios (âmbar só para atenção/experimental; vermelho só para falha).

---

## 4. Comparação: interface atual × proposta

| Aspecto | Dashboard atual | Preview proposto |
|---|---|---|
| Ponto de entrada | Abre direto em abas com muitos formulários empilhados | Tela inicial com 4 ações e "Nova análise" como principal |
| Fluxo | Seções soltas, ordem implícita | Wizard de 6 etapas com stepper e Anterior/Próximo |
| Onde estou / o que falta | Não explícito | Barra de contexto + assistente de próxima ação |
| Pré-requisitos | Botão executa e o erro vem do backend | Gate visual: botão bloqueado com o motivo antes de rodar |
| Simples vs. avançado | Campos técnicos sempre visíveis | Divulgação progressiva; mesma config nos dois modos |
| Resultados | Report + tabela, tudo junto | 6 camadas separando operação, ciência e artefatos |
| Estados do resultado | "SUCESSO/FALHA" | 7 estados distintos; falha ≠ não avaliável ≠ nenhuma evidência |
| Histórico | Cartões com botões | Unidades com busca/filtros e parâmetros consultáveis |
| Evidence V2 | Badge "alpha" + avisos | Tarja âmbar dedicada + separação clara do 1.1 |
| Linguagem | Mistura "validação", "detecção" | Conservadora: fragmento candidato, classificação operacional |
| Acessibilidade | Parcial (aria-live em alguns campos) | Foco visível, stepper com aria-current, modal com foco preso, HTML semântico |

---

## 5. Mudanças que, na integração, exigirão o backend (`ux_dashboard.py`)

Estas dependem de dados/endpoints reais e **não** estão no preview além da simulação visual:

1. **Estado do ambiente = preflight real**: hoje o `/api/config/environment` sinaliza sobretudo a existência de `environment.yml`. Será preciso um endpoint que rode a verificação de ferramentas (à la `00_check_env.sh`) e retorne o status por dependência.
2. **Barra de contexto persistente**: o banco ativo e a amostra hoje vivem só no cliente. Convém um endpoint de "estado da sessão" para sobreviver a recarregamentos.
3. **Assistente de próxima ação**: a lógica é determinística no cliente, mas depende de campos de estado confiáveis vindos do backend (ambiente, banco, job atual, validação do índice).
4. **Camadas de resultado** (controles, cobertura/breadth, especificidade, outcome): exigem que o backend exponha essas métricas de forma estruturada (parte já existe no Evidence V2; padronizar para o 1.1).
5. **Estados distintos** (nenhuma evidência × não avaliável × falha): o backend precisa diferenciar esses desfechos explicitamente, não apenas `exit_code`.
6. **Histórico com busca/filtros e "ver parâmetros"**: requer que cada run persista metadados consultáveis (amostra, banco, modo, parâmetros efetivos).
7. **Tempo decorrido**: mostrado a partir do início real do job (sem inventar ETA/percentual).

## 6. Mudanças puramente visuais (sem backend)

Podem migrar para o dashboard funcional apenas com front-end:

- Tela inicial com 4 ações e hierarquia visual.
- Stepper e navegação Anterior/Próximo do wizard.
- Divulgação progressiva (simples ↔ avançado) reusando os campos atuais.
- Gate visual de pré-requisitos (usando o estado que o cliente já conhece).
- Reorganização dos resultados em camadas.
- Tarja/borda âmbar e badge do Evidence V2.
- Padronização de rótulos e da linguagem científica conservadora.
- Tokens de CSS centralizados, foco visível, semântica e foco de modal.

---

## 7. Decisões de UX, limitações e pontos que precisam da sua aprovação

**Decisões tomadas**
- Âmbar reservado a atenção/experimental; vermelho só para falha/ação perigosa; azul-petróleo como cor principal — estilo sóbrio, sem gradientes decorativos.
- "Relatório de Validação Filogenética" → **"Análise filogenética complementar"**.
- Nenhuma ação desabilitada sem explicar o motivo (o gate sempre lista o que falta).
- Sem porcentagem/ETA inventados; apenas tempo decorrido real.

**Limitações do preview**
- Uploads de arquivo estão desativados (sem backend).
- Métricas (cobertura, identidade, etc.) são ilustrativas.
- Sem capturas de tela automáticas: a extensão do Chrome não estava conectada neste ambiente. Posso gerá-las depois, se você conectar.

**Pontos que dependem da sua aprovação antes da integração**
1. Nomenclatura final dos 7 estados e dos rótulos científicos (seção 3).
2. Ordem e conteúdo das 6 camadas de resultado.
3. Quais parâmetros ficam no modo simples vs. avançado.
4. Se o histórico deve mesmo ganhar busca/filtros na primeira fase.
5. Escopo do preflight de ambiente (quais dependências verificar e como exibir).

> Próximo passo sugerido: você abre o preview, valida visualmente e me diz o que ajustar. Só depois da sua aprovação eu mexo no front-end real e no `ux_dashboard.py`.
