/* =====================================================================
   Gene-In · Preview de UX — LÓGICA VISUAL (estática, offline)
   Sem framework, sem build, sem CDN. Consome apenas GENEIN_MOCK.
   Responsabilidades: roteamento de telas, wizard, barra de contexto,
   assistente determinístico de próxima ação, gate visual de pré-requisitos,
   modal acessível. Nenhuma chamada de rede.
   ===================================================================== */
(function () {
  "use strict";
  var M = window.GENEIN_MOCK;
  var L = M.LABELS;

  /* ---------------- helpers ---------------- */
  function h(tag, attrs, children) {
    var e = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") e.className = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else if (k.indexOf("on") === 0 && typeof attrs[k] === "function") e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] === true) e.setAttribute(k, "");
      else if (attrs[k] !== false && attrs[k] != null) e.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c == null) return;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return e;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function badge(execKey) {
    var s = L.execState[execKey] || L.execState.idle;
    return h("span", { class: "badge " + s.badge, text: s.text });
  }

  /* ---------------- estado da aplicação ---------------- */
  var State = {
    scenarioKey: M.SCENARIO_ORDER[0],
    screen: "home",
    wizardStep: 0,
    wizardDone: [],
    ctx: {},
    form: {
      db: "", sample: "", assembler: "velvet", kmer: 31,
      hostFilter: "sus_scrofa", hostPrefix: "", hostValidated: false,
      skipQC: false, mode: "simple",
    },
    exec: null,
    result: null,
  };

  var root; // container principal de telas
  var elapsedTimer = null;

  /* ---------------- carregar cenário ---------------- */
  function loadScenario(key) {
    var sc = M.SCENARIOS[key];
    State.scenarioKey = key;
    State.screen = sc.screen;
    State.wizardStep = sc.wizard.current;
    State.wizardDone = sc.wizard.done.slice();
    State.ctx = Object.assign({}, sc.context);
    State.exec = sc.exec ? JSON.parse(JSON.stringify(sc.exec)) : null;
    State.result = sc.result ? Object.assign({}, sc.result) : null;
    // Deriva formulário a partir do contexto (mesma config para simples/avançado)
    State.form.db = sc.context.db || "";
    State.form.sample = sc.context.sample || "";
    State.form.hostValidated = State.form.hostFilter !== "custom";
    render();
  }

  /* ---------------- barra de contexto persistente ---------------- */
  function envChip() {
    var map = {
      unknown: { t: "Não verificado", cls: "" },
      ok:      { t: "Verificado (preflight)", cls: "" },
      fail:    { t: "Com pendências", cls: "" },
    };
    var e = map[State.ctx.env] || map.unknown;
    return chip("Ambiente", e.t);
  }
  function chip(label, value, experimental) {
    return h("div", { class: "context-chip" + (experimental ? " context-chip--experimental" : "") }, [
      h("span", { class: "context-chip__label", text: label }),
      h("span", { class: "context-chip__value", text: value }),
    ]);
  }
  function renderContextBar() {
    var bar = document.getElementById("context-bar");
    clear(bar);
    bar.appendChild(envChip());
    bar.appendChild(chip("Banco ativo", State.ctx.db || "Nenhum selecionado"));
    bar.appendChild(chip("Amostra", State.ctx.sample || "Nenhuma"));
    var jobBox = h("div", { class: "context-chip" }, [
      h("span", { class: "context-chip__label", text: "Execução" }),
      h("span", { class: "context-chip__value" }, [badge(State.ctx.job || "idle")]),
    ]);
    bar.appendChild(jobBox);
    if (State.ctx.evidence) bar.appendChild(chip("Evidence V2", "Shadow mode", true));
  }

  /* ---------------- assistente de próxima ação ---------------- */
  function renderNextAction(container) {
    var na = M.SCENARIOS[State.scenarioKey].nextAction;
    if (!na) return;
    var box = h("div", { class: "next-action" + (na.tone === "warn" ? " next-action--warn" : ""), role: "status" }, [
      h("div", { class: "next-action__icon", text: na.tone === "warn" ? "⚠️" : "➡️" }),
      h("div", { class: "next-action__body" }, [
        h("div", { class: "next-action__label", text: "Próxima ação recomendada" }),
        h("div", { class: "next-action__text", text: na.text }),
      ]),
      h("button", { class: "btn btn--primary", onclick: function () { routeTo(na.go); } }, ["Ir"]),
    ]);
    container.appendChild(box);
  }
  function routeTo(go) {
    if (go.indexOf("wizard:") === 0) { State.screen = "wizard"; State.wizardStep = parseInt(go.split(":")[1], 10); }
    else State.screen = go;
    render();
  }

  /* ---------------- cabeçalho / navegação ---------------- */
  function renderNav() {
    var nav = document.getElementById("main-nav");
    clear(nav);
    var items = [
      { key: "home", label: "Início" },
      { key: "wizard", label: "Nova análise" },
      { key: "results", label: "Resultados" },
      { key: "history", label: "Histórico" },
      { key: "evidence", label: "Evidence V2" },
    ];
    items.forEach(function (it) {
      var current = State.screen === it.key || (it.key === "wizard" && (State.screen === "wizard" || State.screen === "review" || State.screen === "execution"));
      nav.appendChild(h("button", {
        "aria-current": current ? "page" : false,
        onclick: function () { State.screen = it.key; if (it.key === "wizard") { /* keep step */ } render(); },
      }, [it.label]));
    });
  }

  /* ==========================================================
     TELA: Home (entrada principal — 4 ações)
     ========================================================== */
  function screenHome() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "home-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "home-title", class: "section-title", text: "Início" }));
    wrap.appendChild(h("p", { class: "section-lead", text: "Escolha como deseja começar. A recuperação de fragmentos virais candidatos segue uma jornada guiada, passo a passo." }));
    var grid = h("div", { class: "home-grid" });
    grid.appendChild(actionCard("🧪", "Nova análise", "Fluxo guiado do início ao resultado.", true, function () { State.screen = "wizard"; State.wizardStep = 0; render(); }));
    grid.appendChild(actionCard("⏱️", "Continuar execução", "Voltar ao acompanhamento de uma execução em andamento.", false, function () { State.screen = "execution"; render(); }));
    grid.appendChild(actionCard("▶️", "Executar demonstração", "Rodar um exemplo reprodutível com dados fictícios.", false, function () { State.screen = "wizard"; State.wizardStep = 4; render(); }));
    grid.appendChild(actionCard("🗂️", "Consultar histórico", "Revisar execuções anteriores e seus artefatos.", false, function () { State.screen = "history"; render(); }));
    wrap.appendChild(grid);
    return wrap;
  }
  function actionCard(icon, title, desc, primary, onclick) {
    return h("button", { class: "action-card" + (primary ? " action-card--primary" : ""), onclick: onclick }, [
      h("span", { class: "action-card__icon", text: icon }),
      h("span", { class: "action-card__title", text: title }),
      h("span", { class: "action-card__desc", text: desc }),
    ]);
  }

  /* ==========================================================
     Stepper
     ========================================================== */
  function stepper() {
    var ol = h("ol", { class: "stepper", role: "list", "aria-label": "Etapas da análise" });
    M.WIZARD_STEPS.forEach(function (st, i) {
      var stateAttr = i === State.wizardStep ? "current" : (State.wizardDone.indexOf(i) >= 0 ? "done" : "todo");
      var reachable = i <= State.wizardStep || State.wizardDone.indexOf(i) >= 0;
      var li = h("li", { "data-state": stateAttr });
      li.appendChild(h("button", {
        "aria-current": stateAttr === "current" ? "step" : false,
        disabled: !reachable,
        title: reachable ? "" : "Conclua as etapas anteriores para acessar",
        onclick: function () { if (reachable) { State.wizardStep = i; render(); } },
      }, [
        h("span", { class: "step-index", text: stateAttr === "done" ? "✓" : String(i + 1) }),
        h("span", { class: "step-label", text: st.label }),
      ]));
      ol.appendChild(li);
    });
    return ol;
  }

  /* ==========================================================
     Verifica pré-requisitos (gate visual)
     ========================================================== */
  function missingPrereqs() {
    var miss = [];
    if (State.ctx.env !== "ok") miss.push("verificar o ambiente");
    if (!State.form.db) miss.push("preparar/selecionar um banco viral");
    if (!State.form.sample) miss.push("importar uma amostra");
    if (State.form.hostFilter === "custom" && !State.form.hostValidated) miss.push("validar o índice customizado do hospedeiro");
    return miss;
  }

  /* ==========================================================
     TELA: Wizard (6 etapas)
     ========================================================== */
  function screenWizard() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "wiz-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "wiz-title", class: "section-title", text: "Nova análise — jornada guiada" }));
    wrap.appendChild(stepper());
    var step = M.WIZARD_STEPS[State.wizardStep];
    var card = h("div", { class: "card" });
    (stepRenderers[step.key] || function () {})(card);
    wrap.appendChild(card);
    wrap.appendChild(wizardButtons());
    return wrap;
  }

  function wizardButtons() {
    var row = h("div", { class: "btn-row" });
    if (State.wizardStep > 0) {
      row.appendChild(h("button", { class: "btn btn--ghost", onclick: function () { State.wizardStep--; render(); } }, ["← Anterior"]));
    }
    var isLast = State.wizardStep === M.WIZARD_STEPS.length - 1;
    var spacer = h("span", { class: "spacer" });
    row.appendChild(spacer);
    if (State.wizardStep === 4) {
      // etapa Revisar → mostra revisão inline; botão executa
      return row; // botões vêm do próprio stepReview
    }
    if (!isLast) {
      row.appendChild(h("button", { class: "btn btn--primary", onclick: function () {
        if (State.wizardDone.indexOf(State.wizardStep) < 0) State.wizardDone.push(State.wizardStep);
        State.wizardStep++; render();
      } }, ["Próximo →"]));
    }
    return row;
  }

  var stepRenderers = {
    env: function (card) {
      card.appendChild(h("h3", { text: "Verificar ambiente" }));
      card.appendChild(h("p", { class: "desc", text: "Confere se as ferramentas do pipeline estão disponíveis (verificação de pré-execução). O estado abaixo reflete o preflight, não apenas a existência de arquivos de configuração." }));
      var ok = State.ctx.env === "ok";
      card.appendChild(h("div", { class: "notice " + (ok ? "notice--ok" : "notice--info") }, [
        ok ? "Ambiente verificado: ferramentas essenciais detectadas (resultado fictício)." : "Ambiente ainda não verificado. Execute a verificação para liberar as próximas etapas.",
      ]));
      card.appendChild(h("button", { class: "btn btn--primary", onclick: function () {
        State.ctx.env = "ok"; if (State.wizardDone.indexOf(0) < 0) State.wizardDone.push(0); render();
      } }, ["Verificar ambiente"]));
    },
    db: function (card) {
      card.appendChild(h("h3", { text: "Preparar ou selecionar o banco viral" }));
      card.appendChild(h("p", { class: "desc", text: "O banco de referência define contra o que os fragmentos serão comparados. A sensibilidade depende da diversidade do banco escolhido." }));
      var grid = h("div", { class: "form-grid" });
      var sel = h("select", { id: "f-db", onchange: function (e) { State.form.db = e.target.selectedOptions[0].text === "Selecione um alvo" ? "" : e.target.selectedOptions[0].text; State.ctx.db = State.form.db || null; renderContextBar(); refreshGate(); } });
      sel.appendChild(h("option", { value: "" }, ["Selecione um alvo"]));
      M.TARGETS.forEach(function (t) {
        var o = h("option", { value: t.key }, [t.display_name]);
        if (t.display_name === State.form.db) o.selected = true;
        sel.appendChild(o);
      });
      grid.appendChild(field("Alvo pré-configurado", sel, "No modo simplificado, basta escolher um alvo desta lista."));
      card.appendChild(grid);

      var adv = advancedPanel([
        field("Query NCBI customizada", h("input", { type: "text", placeholder: '"Orbivirus"[Organism]' }), "Para vírus fora da lista. Aceita qualquer query NCBI válida."),
        field("TaxID", h("input", { type: "text", placeholder: "ex.: 12087" }), "Alternativa à query por identificador taxonômico."),
      ]);
      card.appendChild(adv.toggle); card.appendChild(adv.panel);
    },
    sample: function (card) {
      card.appendChild(h("h3", { text: "Importar amostra" }));
      card.appendChild(h("p", { class: "desc", text: "Envie os arquivos de leituras pareadas (R1/R2). Os nomes abaixo são exemplos fictícios." }));
      var grid = h("div", { class: "form-grid" });
      var sel = h("select", { onchange: function (e) { State.form.sample = e.target.value; State.ctx.sample = e.target.value || null; renderContextBar(); refreshGate(); } });
      sel.appendChild(h("option", { value: "" }, ["Selecione uma amostra importada"]));
      M.SAMPLES.forEach(function (s) { var o = h("option", { value: s }, [s]); if (s === State.form.sample) o.selected = true; sel.appendChild(o); });
      grid.appendChild(field("Amostra", sel, "Escolha uma amostra já importada ou envie novos arquivos abaixo."));
      grid.appendChild(field("Arquivo R1 (.fastq.gz)", h("input", { type: "file", disabled: true }), "Desativado no preview (sem backend)."));
      grid.appendChild(field("Arquivo R2 (.fastq.gz)", h("input", { type: "file", disabled: true }), "Desativado no preview (sem backend)."));
      card.appendChild(grid);
    },
    config: function (card) {
      card.appendChild(h("h3", { text: "Configurar análise" }));
      card.appendChild(h("p", { class: "desc", text: "No modo simplificado, apenas o essencial. Parâmetros técnicos ficam em Configuração avançada — mesma configuração, sem fluxos separados." }));
      var grid = h("div", { class: "form-grid" });
      // montador (essencial)
      var asm = h("select", { onchange: function (e) { State.form.assembler = e.target.value; } });
      M.ASSEMBLERS.forEach(function (a) { var o = h("option", { value: a.key }, [a.name + " — " + a.simpleHint]); if (a.key === State.form.assembler) o.selected = true; asm.appendChild(o); });
      grid.appendChild(field("Montador", asm, "Como os fragmentos são reconstruídos a partir das leituras."));
      // filtro hospedeiro (essencial, decisão simples)
      var host = h("select", { id: "f-host", onchange: function (e) { State.form.hostFilter = e.target.value; State.form.hostValidated = e.target.value !== "custom"; render(); } });
      [["sus_scrofa", "Sus scrofa (padrão)"], ["none", "Sem filtro de hospedeiro"], ["custom", "Índice customizado (avançado)"]].forEach(function (p) {
        var o = h("option", { value: p[0] }, [p[1]]); if (p[0] === State.form.hostFilter) o.selected = true; host.appendChild(o);
      });
      grid.appendChild(field("Filtro do hospedeiro", host, "Remove leituras do hospedeiro antes da montagem."));
      card.appendChild(grid);

      if (State.form.hostFilter === "custom") {
        var prefixInput = h("input", { type: "text", placeholder: "ref/host/bos_taurus_bt2", value: State.form.hostPrefix,
          oninput: function (e) { State.form.hostPrefix = e.target.value; State.form.hostValidated = false; } });
        var validateBtn = h("button", { class: "btn", onclick: function () {
          if (!State.form.hostPrefix) { toast("Informe o prefixo do índice antes de validar.", "warn"); return; }
          State.form.hostValidated = true; refreshGate(); toast("Índice customizado validado (resultado fictício).", "ok");
        } }, ["Validar índice"]);
        var cf = field("Prefixo do índice Bowtie2", prefixInput, State.form.hostValidated ? "Índice validado." : "O índice customizado ainda não foi validado.");
        cf.appendChild(validateBtn);
        card.appendChild(cf);
      }

      var adv = advancedPanel([
        field("k-mer", (function () { var i = h("input", { type: "number", min: 15, max: 99, step: 2, value: State.form.kmer, oninput: function (e) { State.form.kmer = e.target.value; } }); return i; })(), "Valor ímpar entre 15 e 99 (padrão 31)."),
        field("Controle de qualidade (QC)", (function () {
          var lbl = h("label", { class: "field__label", style: "display:flex;gap:8px;align-items:center;font-weight:400" }, []);
          var cb = h("input", { type: "checkbox", onchange: function (e) { State.form.skipQC = e.target.checked; } });
          if (State.form.skipQC) cb.checked = true;
          lbl.appendChild(cb); lbl.appendChild(document.createTextNode(" Pular QC (fastp)"));
          return lbl;
        })(), "Só marque se os dados já estiverem limpos."),
      ]);
      card.appendChild(adv.toggle); card.appendChild(adv.panel);
    },
    review: function (card) { stepReview(card); },
    run: function (card) {
      card.appendChild(h("h3", { text: "Executar e acompanhar" }));
      card.appendChild(h("p", { class: "desc", text: "A execução ocorre no backend real. Neste preview, use o seletor de estados (no topo) para ver o acompanhamento em cada situação." }));
      gateOrRun(card);
    },
  };

  function stepReview(card) {
    card.appendChild(h("h3", { text: "Revisar configuração antes de executar" }));
    card.appendChild(h("p", { class: "desc", text: "Confira o resumo. Você pode voltar a qualquer etapa para corrigir." }));
    var rows = [
      ["Amostra e arquivos", (State.form.sample || "—") + " · R1/R2 (fictícios)", 2],
      ["Banco selecionado", State.form.db || "—", 1],
      ["Montador", asmName(State.form.assembler), 3],
      ["k-mer", String(State.form.kmer), 3],
      ["Filtro do hospedeiro", hostName(State.form.hostFilter) + (State.form.hostFilter === "custom" ? (State.form.hostValidated ? " (validado)" : " (não validado)") : ""), 3],
      ["Controle de qualidade", State.form.skipQC ? "Ignorado" : "Ativado (fastp)", 3],
      ["Modo do pipeline", "Recuperação e priorização (não diagnóstico)", 3],
      ["Saídas esperadas", "Fragmentos candidatos, tabela de similaridade, relatório e artefatos", null],
    ];
    var dl = h("dl", { class: "kv" });
    rows.forEach(function (r) {
      dl.appendChild(h("dt", { text: r[0] }));
      var dd = h("dd", {}, [r[1]]);
      if (r[2] != null) {
        dd.appendChild(document.createTextNode("  "));
        dd.appendChild(h("button", { class: "help-inline", onclick: function () { State.wizardStep = r[2]; State.screen = "wizard"; render(); } }, ["corrigir"]));
      }
      dl.appendChild(dd);
    });
    card.appendChild(dl);
    gateOrRun(card);
  }

  function gateOrRun(card) {
    var miss = missingPrereqs();
    var row = h("div", { class: "btn-row" });
    if (miss.length) {
      card.appendChild(h("div", { class: "notice notice--warn", id: "gate-note", role: "alert" }, [
        "A execução está bloqueada. Para liberar, é preciso: " + miss.join("; ") + ".",
      ]));
      row.appendChild(h("button", { class: "btn btn--primary", disabled: true, "aria-describedby": "gate-note" }, ["Executar análise"]));
    } else {
      row.appendChild(h("button", { class: "btn btn--primary", onclick: function () { toast("No backend real, a execução começaria aqui. Use o seletor de estados para ver o acompanhamento.", "info"); State.screen = "execution"; State.ctx.job = "running"; State.exec = { stages: { qc: "running", host: "pending", assembly: "pending", blast: "pending", report: "pending" }, elapsed: "00:00:03" }; render(); } }, ["Executar análise"]));
    }
    card.appendChild(row);
  }

  /* ==========================================================
     TELA: Execução (acompanhamento)
     ========================================================== */
  function screenExecution() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "exec-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "exec-title", class: "section-title", text: "Acompanhamento da execução" }));
    var ex = State.exec || { stages: {}, elapsed: "00:00:00" };
    var card = h("div", { class: "card" });
    var head = h("div", { style: "display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px" }, [
      badge(State.ctx.job || "running"),
      h("span", { class: "context-chip__label", text: "Tempo decorrido" }),
      h("span", { class: "elapsed", id: "elapsed", text: ex.elapsed }),
    ]);
    card.appendChild(head);

    var list = h("ul", { class: "exec-stages" });
    M.PIPELINE_STAGES.forEach(function (s) {
      var st = (ex.stages && ex.stages[s.key]) || "pending";
      var icon = { pending: "⏳", running: "🔄", done: "✅", error: "❌", skipped: "⏭️" }[st] || "⏳";
      list.appendChild(h("li", { class: "exec-stage", "data-state": st }, [
        h("span", { class: "exec-stage__icon", text: icon }),
        h("span", { class: "exec-stage__label", text: s.label }),
        h("span", { class: "exec-stage__meta", text: st === "running" ? "em execução" : st === "done" ? "concluída" : st === "error" ? "falhou" : st === "skipped" ? "ignorada" : "pendente" }),
      ]));
    });
    card.appendChild(list);

    if (ex.error) {
      card.appendChild(h("div", { class: "notice notice--danger", role: "alert" }, [
        h("strong", { text: "Falha operacional na etapa Montagem. " }),
        "A execução foi interrompida por um erro técnico antes de gerar um resultado avaliável. Nenhuma conclusão científica pode ser derivada. Sugestão: revisar memória/parâmetros do montador e reexecutar.",
      ]));
    }

    card.appendChild(h("p", { class: "context-chip__label", style: "margin:12px 0 4px", text: "Log resumido" }));
    card.appendChild(h("pre", { class: "log-panel", text: M.LOG_SAMPLE }));
    var det = h("details", { class: "tech" }, [
      h("summary", { text: "Detalhes técnicos (log completo)" }),
      h("pre", { class: "log-panel", style: "margin-top:8px", text: M.LOG_SAMPLE + "\n[DEBUG] parâmetros efetivos: assembler=" + State.form.assembler + " k=" + State.form.kmer }),
    ]);
    card.appendChild(det);

    var row = h("div", { class: "btn-row" });
    if ((State.ctx.job || "") === "running") {
      row.appendChild(h("button", { class: "btn btn--danger", onclick: function () { if (confirm("Deseja cancelar a execução em andamento?")) { State.ctx.job = "cancelled"; render(); } } }, ["⏹️ Cancelar execução"]));
    } else if ((State.ctx.job || "") === "done") {
      row.appendChild(h("button", { class: "btn btn--primary", onclick: function () { State.screen = "results"; render(); } }, ["Ver resultado →"]));
    }
    card.appendChild(row);
    wrap.appendChild(card);
    return wrap;
  }

  /* ==========================================================
     TELA: Resultados em camadas
     ========================================================== */
  function screenResults() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "res-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "res-title", class: "section-title", text: "Resultado da análise" }));
    var outcome = (State.result && State.result.outcome) || "done";

    // Camada 1 — estado operacional
    wrap.appendChild(layer(1, "Estado operacional da execução", [
      h("div", { style: "display:flex;gap:10px;align-items:center;flex-wrap:wrap" }, [
        badge(outcome), h("span", { class: "context-chip__label", text: "Amostra: " + (State.ctx.sample || "—") + " · Banco: " + (State.ctx.db || "—") }),
      ]),
    ]));

    // Camada 2 — resultado da análise
    var l2 = [];
    if (outcome === "done") l2.push(h("p", { text: "Foram recuperados 3 fragmentos virais candidatos priorizados (ver camada 5)." }));
    else if (outcome === "none") l2.push(h("p", { text: "Nenhum fragmento candidato atendeu aos critérios adotados." }));
    else if (outcome === "na") l2.push(h("p", { text: "Não foi possível produzir uma classificação operacional confiável." }));
    else if (outcome === "fail") l2.push(h("p", { text: "A execução falhou antes de gerar um resultado avaliável." }));
    wrap.appendChild(layer(2, "Resultado da análise", l2));

    // Camada 3 — nível de evidência e limitações
    var interpClass = { done: "", none: "interpretation--none", na: "interpretation--na", fail: "interpretation--fail" }[outcome] || "";
    wrap.appendChild(layer(3, "Nível de evidência e limitações", [
      h("div", { class: "interpretation " + interpClass }, [L.interpretation[outcome] || L.interpretation.done]),
    ]));

    // Camada 4 — controles, cobertura e especificidade
    if (outcome === "done" || outcome === "none") {
      var dl = h("dl", { class: "kv" }, [
        h("dt", { text: "Controle negativo" }), h("dd", { text: outcome === "done" ? "Sem sinal (fictício)" : "Sem sinal" }),
        h("dt", { text: "Cobertura (breadth 1×)" }), h("dd", { text: outcome === "done" ? "62% (fictício)" : "8% (fictício)" }),
        h("dt", { text: "Especificidade" }), h("dd", { text: outcome === "done" ? "Compatível com o alvo" : "Insuficiente" }),
      ]);
      wrap.appendChild(layer(4, "Controles, cobertura e especificidade", [dl]));
    } else {
      wrap.appendChild(layer(4, "Controles, cobertura e especificidade", [h("p", { class: "context-chip__label", text: "Não aplicável para este desfecho." })]));
    }

    // Camada 5 — fragmentos candidatos priorizados
    if (outcome === "done") {
      wrap.appendChild(layer(5, "Fragmentos candidatos priorizados", [candidateTable()]));
    } else {
      wrap.appendChild(layer(5, "Fragmentos candidatos priorizados", [h("p", { class: "context-chip__label", text: "Nenhum fragmento candidato a apresentar." })]));
    }

    // Camada 6 — artefatos
    wrap.appendChild(layer(6, "Artefatos, tabelas e logs", [
      h("div", { class: "history-item__meta", style: "margin:0" }, [
        artifactBtn("📋 Relatório"), artifactBtn("🔬 Tabela de similaridade"), artifactBtn("⬇ FASTA de candidatos"), artifactBtn("⚙️ Log completo"),
      ]),
      h("p", { class: "context-chip__label", style: "margin-top:8px", text: "Artefatos intermediários ficam recolhidos, mas seguem acessíveis." }),
    ]));
    return wrap;
  }
  function layer(n, title, body, experimental) {
    var sec = h("section", { class: "result-layer" + (experimental ? " result-layer--experimental" : "") }, [
      h("header", {}, [h("span", { class: "result-layer__num", text: String(n) }), h("h4", { text: title })]),
      h("div", { class: "result-layer__body" }, body),
    ]);
    return sec;
  }
  function candidateTable() {
    var wrap = h("div", { class: "table-wrap" });
    var t = h("table", { class: "data" });
    t.appendChild(h("thead", {}, [h("tr", {}, ["Fragmento", "Referência", "Comprimento", "Cobertura", "Identidade", "Ident. ajustada", "Evidência"].map(function (x) { return h("th", { text: x }); }))]));
    var tb = h("tbody");
    M.CANDIDATE_FRAGMENTS.forEach(function (f) {
      tb.appendChild(h("tr", {}, [f.id, f.ref, f.len + " pb", f.cov, f.pident + "%", String(f.adj), f.evidence].map(function (x) { return h("td", { text: String(x) }); })));
    });
    t.appendChild(tb); wrap.appendChild(t);
    return wrap;
  }
  function artifactBtn(label) { return h("button", { class: "btn", onclick: function () { toast("No backend real, isto abriria/baixaria: " + label, "info"); } }, [label]); }

  /* ==========================================================
     TELA: Histórico
     ========================================================== */
  function screenHistory() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "hist-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "hist-title", class: "section-title", text: "Histórico de execuções" }));
    wrap.appendChild(h("p", { class: "section-lead", text: "Cada execução é uma unidade rastreável com amostra, banco, estado e artefatos." }));

    var filters = h("div", { class: "history-filters" });
    var fSample = h("input", { type: "search", placeholder: "Buscar por amostra", "aria-label": "Buscar por amostra", oninput: function (e) { redrawHistory(e.target.value, fState.value); } });
    var fState = h("select", { "aria-label": "Filtrar por estado", onchange: function () { redrawHistory(fSample.value, fState.value); } });
    fState.appendChild(h("option", { value: "" }, ["Todos os estados"]));
    ["done", "none", "na", "partial", "fail"].forEach(function (k) { fState.appendChild(h("option", { value: k }, [L.execState[k].text])); });
    filters.appendChild(fSample); filters.appendChild(fState);
    wrap.appendChild(filters);

    var listWrap = h("div", { id: "history-list" });
    wrap.appendChild(listWrap);
    setTimeout(function () { redrawHistory("", ""); }, 0);
    return wrap;
  }
  function redrawHistory(q, st) {
    var listWrap = document.getElementById("history-list"); if (!listWrap) return; clear(listWrap);
    var rows = M.HISTORY.filter(function (r) {
      return (!q || r.sample.toLowerCase().indexOf(q.toLowerCase()) >= 0) && (!st || r.state === st);
    });
    if (!rows.length) { listWrap.appendChild(h("p", { class: "context-chip__label", text: "Nenhuma execução corresponde aos filtros." })); return; }
    rows.forEach(function (r) {
      var item = h("article", { class: "history-item" });
      item.appendChild(h("header", {}, [h("h4", { text: r.sample }), badge(r.state), h("span", { class: "context-chip__label", text: r.mode })]));
      item.appendChild(h("div", { class: "history-item__meta" }, [
        h("span", { text: "📅 " + r.date }), h("span", { text: "🧬 " + r.db }), h("span", { text: "ID " + r.id }),
      ]));
      item.appendChild(h("p", { class: "history-item__summary", text: r.summary }));
      var actions = h("div", { class: "actions" });
      ["📋 Report", "🔬 Tabela", "⬇ Artefatos", "🔧 Parâmetros", "⚙️ Logs", "🔄 Reexecutar"].forEach(function (a) {
        actions.appendChild(h("button", { class: "btn", onclick: function () {
          if (a.indexOf("Parâmetros") >= 0) openModal("Parâmetros de " + r.id, paramsModalBody(r));
          else toast("No backend real: " + a + " · " + r.id, "info");
        } }, [a]));
      });
      item.appendChild(actions);
      listWrap.appendChild(item);
    });
  }
  function paramsModalBody(r) {
    return h("dl", { class: "kv" }, [
      h("dt", { text: "Amostra" }), h("dd", { text: r.sample }),
      h("dt", { text: "Banco" }), h("dd", { text: r.db }),
      h("dt", { text: "Modo" }), h("dd", { text: r.mode }),
      h("dt", { text: "Estado" }), h("dd", { text: L.execState[r.state].text }),
      h("dt", { text: "Montador" }), h("dd", { text: "Velvet (k=31) — fictício" }),
      h("dt", { text: "Filtro hospedeiro" }), h("dd", { text: "Sus scrofa — fictício" }),
    ]);
  }

  /* ==========================================================
     TELA: Evidence V2 (experimental / shadow mode)
     ========================================================== */
  function screenEvidence() {
    var wrap = h("section", { class: "screen active", "aria-labelledby": "ev-title" });
    renderNextAction(wrap);
    wrap.appendChild(h("h2", { id: "ev-title", class: "section-title", text: "Evidence V2" }));
    var box = h("div", { class: "evidence-wrap" });
    box.appendChild(h("div", { class: "evidence-banner" }, [
      h("span", { text: "🧪 Evidence V2" }), h("span", { class: "badge", text: "Experimental — shadow mode" }),
    ]));
    box.appendChild(h("p", { class: "notice notice--warn", text: "Modo experimental (shadow mode). As dimensões experimentais NÃO substituem a classificação operacional 1.1 e exigem revisão e validação complementar. Nada aqui constitui diagnóstico." }));

    box.appendChild(layer(1, "Classificação operacional 1.1 (oficial)", [
      h("div", { style: "display:flex;gap:10px;align-items:center;flex-wrap:wrap" }, [badge("done"), h("span", { text: "3 fragmentos candidatos · interpretação conservadora." })]),
    ]));
    var dims = h("div", { class: "history-item__meta", style: "margin:0;gap:10px" }, [
      dimCard("Nível de evidência", "E1 (teto)"),
      dimCard("Especificidade", "Compatível"),
      dimCard("Cobertura", "Parcial"),
      dimCard("Controle", "Sem sinal"),
    ]);
    box.appendChild(layer(2, "Dimensões experimentais Evidence V2", [dims, h("p", { class: "context-chip__label", style: "margin-top:8px", text: "Parâmetros em calibração." })], true));

    box.appendChild(layer(3, "Fragmentos exploratórios (20–49 pb)", [
      h("p", { text: "Apresentados apenas como evidência exploratória. Nunca aparecem isolados como identificação ou detecção." }),
      (function () { var ul = h("ul"); M.EXPLORATORY_FRAGMENTS.forEach(function (f) { ul.appendChild(h("li", { text: f.id + " · " + f.len + " pb — " + f.note })); }); return ul; })(),
    ], true));
    wrap.appendChild(box);
    return wrap;
  }
  function dimCard(label, value) {
    return h("div", { class: "context-chip", style: "min-width:150px" }, [
      h("span", { class: "context-chip__label", text: label }), h("span", { class: "context-chip__value", text: value }),
    ]);
  }

  /* ==========================================================
     Componentes utilitários compartilhados
     ========================================================== */
  function field(label, control, hint) {
    var id = "fld-" + Math.random().toString(36).slice(2, 8);
    if (control.tagName === "INPUT" || control.tagName === "SELECT" || control.tagName === "TEXTAREA") control.id = id;
    var f = h("div", { class: "field" }, [
      h("label", { for: id, class: "field__label", text: label }), control,
    ]);
    if (hint) f.appendChild(h("span", { class: "hint", text: hint }));
    return f;
  }
  function advancedPanel(children) {
    var open = State.form.mode === "advanced";
    var panel = h("div", { class: "advanced-panel", hidden: !open }, [h("div", { class: "form-grid" }, children)]);
    var toggle = h("button", { class: "advanced-toggle", "aria-expanded": open ? "true" : "false", onclick: function () {
      var isHidden = panel.hasAttribute("hidden");
      if (isHidden) { panel.removeAttribute("hidden"); toggle.setAttribute("aria-expanded", "true"); State.form.mode = "advanced"; }
      else { panel.setAttribute("hidden", ""); toggle.setAttribute("aria-expanded", "false"); State.form.mode = "simple"; }
      toggle.firstChild.textContent = panel.hasAttribute("hidden") ? "▸ Configuração avançada" : "▾ Configuração avançada";
    } }, [(open ? "▾ " : "▸ ") + "Configuração avançada"]);
    return { toggle: toggle, panel: panel };
  }
  function asmName(k) { var a = M.ASSEMBLERS.filter(function (x) { return x.key === k; })[0]; return a ? a.name : k; }
  function hostName(k) { return { sus_scrofa: "Sus scrofa (padrão)", none: "Sem filtro", custom: "Índice customizado" }[k] || k; }

  function refreshGate() {
    // Reexibe apenas o gate se estivermos numa tela que o contém
    if (State.screen === "wizard" && (State.wizardStep === 4 || State.wizardStep === 5)) render();
  }

  /* ---------------- toast simples ---------------- */
  var toastTimer = null;
  function toast(msg, tone) {
    var t = document.getElementById("toast");
    if (!t) { t = h("div", { id: "toast", role: "status", "aria-live": "polite", style: "position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:80;max-width:520px" }); document.body.appendChild(t); }
    clear(t);
    t.appendChild(h("div", { class: "notice notice--" + (tone || "info"), style: "box-shadow:var(--shadow);margin:0" }, [msg]));
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { clear(t); }, 3600);
  }

  /* ---------------- modal acessível ---------------- */
  var lastFocused = null;
  function openModal(title, bodyNode) {
    var overlay = document.getElementById("modal-overlay");
    var titleEl = document.getElementById("modal-title");
    var bodyEl = document.getElementById("modal-body");
    lastFocused = document.activeElement;
    titleEl.textContent = title; clear(bodyEl); bodyEl.appendChild(bodyNode);
    overlay.hidden = false;
    document.getElementById("modal-close").focus();
    document.addEventListener("keydown", modalKeydown);
  }
  function closeModal() {
    var overlay = document.getElementById("modal-overlay");
    overlay.hidden = true;
    document.removeEventListener("keydown", modalKeydown);
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }
  function modalKeydown(e) {
    if (e.key === "Escape") return closeModal();
    if (e.key === "Tab") {
      var modal = document.getElementById("modal");
      var focusables = modal.querySelectorAll("button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
      if (!focusables.length) return;
      var first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  /* ---------------- elapsed ticker (tempo real, não estimativa) ---------------- */
  function startElapsed() {
    stopElapsed();
    if (State.screen !== "execution" || (State.ctx.job || "") !== "running") return;
    var el = document.getElementById("elapsed"); if (!el) return;
    var parts = (State.exec.elapsed || "00:00:00").split(":").map(Number);
    var secs = parts[0] * 3600 + parts[1] * 60 + parts[2];
    elapsedTimer = setInterval(function () {
      secs++;
      var hh = String(Math.floor(secs / 3600)).padStart(2, "0");
      var mm = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
      var ss = String(secs % 60).padStart(2, "0");
      var e = document.getElementById("elapsed"); if (e) e.textContent = hh + ":" + mm + ":" + ss; else stopElapsed();
    }, 1000);
  }
  function stopElapsed() { if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; } }

  /* ---------------- render principal ---------------- */
  var screens = {
    home: screenHome, wizard: screenWizard, review: screenWizard,
    execution: screenExecution, results: screenResults, history: screenHistory, evidence: screenEvidence,
  };
  function render() {
    stopElapsed();
    renderNav();
    renderContextBar();
    clear(root);
    var fn = screens[State.screen] || screenHome;
    root.appendChild(fn());
    startElapsed();
  }

  /* ---------------- seletor de estados (preview) ---------------- */
  function buildStateSelector() {
    var sel = document.getElementById("scenario-select");
    M.SCENARIO_ORDER.forEach(function (key) { sel.appendChild(h("option", { value: key }, [M.SCENARIOS[key].title])); });
    sel.value = State.scenarioKey;
    sel.addEventListener("change", function () { loadScenario(sel.value); });
  }

  /* ---------------- init ---------------- */
  window.addEventListener("DOMContentLoaded", function () {
    root = document.getElementById("screen-root");
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal-overlay").addEventListener("click", function (e) { if (e.target.id === "modal-overlay") closeModal(); });
    buildStateSelector();
    loadScenario(State.scenarioKey);
  });
})();
