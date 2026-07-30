import { getJSON } from "./api.js";
import { setDisabled } from "./a11y.js";
import { createElement } from "./dom.js";
import { createStore } from "./state.js";
import { EXEC_STEPS, sectionStep, stepState } from "./wizard.js";

const sessionValue = (key, fallback = "") => {
  try {
    return typeof sessionStorage === "undefined" ? fallback : (sessionStorage.getItem(key) ?? fallback);
  } catch (_) {
    return fallback;
  }
};

const saveSessionValue = (key, value) => {
  try {
    if (typeof sessionStorage !== "undefined") sessionStorage.setItem(key, String(value));
  } catch (_) {}
};

const uiStore = createStore({
  step: Number(sessionValue("genein.ux.step", "0") || 0),
  guided: sessionValue("genein.ux.mode", "guided") !== "all",
  environment: "checking",
  environmentSummary: "Verificando o ambiente efetivo…",
  database: "",
  sample: "",
  job: "idle",
});

let sectionMap = [];

function getValue(selector) {
  return String(document.querySelector(selector)?.value || "").trim();
}

function readDatabase() {
  const status = document.getElementById("db-status");
  if (!status?.classList.contains("active")) return "";
  return status.textContent.replace(/^DB ativo:\s*/i, "").trim();
}

function readSample() {
  return getValue("#sample-select") || getValue('#pipeline-form input[name="sample"]');
}

function readJobState() {
  const label = document.getElementById("job-status")?.textContent.trim().toLowerCase() || "";
  if (label.includes("execut") || label.includes("inici")) return "running";
  if (label.includes("conclu")) return "done";
  if (label.includes("falh") || label.includes("erro") || label.includes("bloque")) return "failed";
  if (label.includes("cancel")) return "cancelled";
  return "idle";
}

function synchronizeState() {
  uiStore.set({
    database: readDatabase(),
    sample: readSample(),
    job: readJobState(),
  });
}

function stateLabel(job) {
  return {
    idle: ["Aguardando", "ux-badge--idle"],
    running: ["Em execução", "ux-badge--running"],
    done: ["Concluída", "ux-badge--done"],
    failed: ["Falha", "ux-badge--fail"],
    cancelled: ["Cancelada", "ux-badge--cancel"],
  }[job] || ["Aguardando", "ux-badge--idle"];
}

function renderContext(state) {
  const env = document.getElementById("ctx-env");
  const database = document.getElementById("ctx-db");
  const sample = document.getElementById("ctx-sample");
  const job = document.getElementById("ctx-job");
  const envChip = env?.closest(".context-chip");
  if (env) {
    env.textContent = {
      checking: "Verificando…",
      ok: "Pronto",
      pending: "Com pendências",
      error: "Indisponível",
    }[state.environment] || "Indisponível";
    env.title = state.environmentSummary;
  }
  envChip?.classList.toggle("context-chip--experimental", ["pending", "error"].includes(state.environment));
  if (database) database.textContent = state.database || "Nenhum selecionado";
  if (sample) sample.textContent = state.sample || "Nenhuma";
  if (job) {
    const [label, className] = stateLabel(state.job);
    job.replaceChildren(createElement(document, "span", {
      class: `ux-badge ${className}`,
      text: label,
    }));
  }
}

function nextAction(state) {
  if (state.job === "running") return ["Execução em andamento. Acompanhe as etapas e os logs.", false];
  if (state.job === "failed") return ["A última execução falhou. Revise o estado operacional e o log técnico.", true];
  if (["pending", "error"].includes(state.environment)) {
    return [state.environmentSummary || "O ambiente possui dependências pendentes.", true];
  }
  if (!state.database) return ["Prepare um banco viral para continuar.", false];
  if (!state.sample) return ["Banco preparado. Importe ou selecione uma amostra.", false];
  if (state.job === "done") return ["Execução concluída. Revise o relatório e os artefatos.", false];
  return ["Pré-requisitos disponíveis. Revise os parâmetros e execute a análise principal.", false];
}

function renderNextAction(state) {
  const container = document.getElementById("next-action");
  const icon = document.getElementById("next-action-icon");
  const text = document.getElementById("next-action-text");
  if (!container || !text) return;
  const [message, warning] = nextAction(state);
  text.textContent = message;
  container.classList.toggle("next-action--warn", warning);
  if (icon) icon.textContent = warning ? "⚠️" : "➡️";
}

function renderPreflightDetail(result) {
  const node = document.getElementById("preflight-detail");
  if (!node) return;
  node.replaceChildren();
  const summary = result?.summary || "Não foi possível obter o preflight do ambiente.";
  const pathSource = result?.path_source ? `Origem do PATH: ${result.path_source}.` : "";
  node.append(
    createElement(document, "strong", { text: result?.ok ? "Ambiente pronto. " : "Ambiente com pendências. " }),
    createElement(document, "span", { text: summary }),
  );
  if (pathSource) node.append(document.createTextNode(` ${pathSource}`));
  const tools = Array.isArray(result?.tools) ? result.tools : [];
  if (!tools.length) return;
  const list = createElement(document, "ul", { class: "preflight-tool-list" });
  tools.forEach((tool) => {
    const state = tool.present ? "disponível" : (tool.required ? "ausente" : "opcional");
    const item = createElement(document, "li", { dataset: { state: tool.present ? "ok" : (tool.required ? "missing" : "optional") } });
    item.append(
      createElement(document, "strong", { text: tool.name || "ferramenta" }),
      document.createTextNode(` — ${state}${tool.path ? ` (${tool.path})` : ""}`),
    );
    list.append(item);
  });
  node.append(list);
}

function renderStepper(state) {
  const list = document.getElementById("ux-stepper");
  if (!list) return;
  list.replaceChildren();
  const stateLabels = {
    current: "etapa atual",
    done: "concluída",
    blocked: "bloqueada",
    ready: "pronta",
  };
  EXEC_STEPS.forEach((definition, index) => {
    const status = stepState(index, state.step, state);
    const item = createElement(document, "li", { dataset: { state: status } });
    const button = createElement(document, "button", {
      type: "button",
      "aria-label": `${definition.label} — ${stateLabels[status]}`,
      onclick: () => setStep(index),
    });
    if (status === "current") button.setAttribute("aria-current", "step");
    const marker = status === "done" ? "✓" : (status === "blocked" ? "🔒" : String(index + 1));
    button.append(
      createElement(document, "span", { class: "step-index", "aria-hidden": "true", text: marker }),
      createElement(document, "span", { class: "step-label", text: definition.label }),
    );
    item.append(button);
    list.append(item);
  });
}

function updateGate(state) {
  const submit = document.querySelector('#pipeline-form button[type="submit"]');
  const note = document.getElementById("ux-gate-note");
  if (!submit) return;
  const missing = [];
  if (!state.database) missing.push("preparar um banco viral");
  if (!state.sample) missing.push("selecionar uma amostra");
  const reason = missing.length ? `Faltando: ${missing.join("; ")}.` : "";
  setDisabled(submit, missing.length > 0, reason);
  if (note) note.textContent = missing.length ? `Para executar, falta: ${missing.join("; ")}.` : "";
}

function renderPhaseDescription(state) {
  const node = document.getElementById("ux-step-description");
  if (!node) return;
  const definition = EXEC_STEPS[state.step];
  node.replaceChildren(
    createElement(document, "strong", { text: `${state.step + 1}. ${definition.label}: ` }),
    document.createTextNode(definition.description),
  );
}

function renderSections(state) {
  sectionMap.forEach(({ element, step }) => {
    element.hidden = state.guided ? step !== state.step : false;
  });
  document.getElementById("tab-execucao")?.classList.toggle("ux-showall", !state.guided);
  const previous = document.getElementById("ux-prev");
  const next = document.getElementById("ux-next");
  if (previous) previous.disabled = state.step === 0;
  if (next) next.textContent = state.step === EXEC_STEPS.length - 1 ? "Concluir" : "Próximo →";
  document.getElementById("ux-mode-guided")?.setAttribute("aria-pressed", state.guided ? "true" : "false");
  document.getElementById("ux-mode-all")?.setAttribute("aria-pressed", state.guided ? "false" : "true");
}

function renderReview(state) {
  const body = document.getElementById("ux-review-body");
  const form = document.getElementById("pipeline-form");
  if (!body || !form) return;
  const profile = getValue('#pipeline-form select[name="analysis_profile"]') || "canonical-e1";
  const assembler = profile === "assembly-consensus"
    ? "Consenso: Velvet, SPAdes e metaSPAdes"
    : getValue('#pipeline-form select[name="assembler"]');
  const hostMode = getValue('#pipeline-form select[name="host_filter_mode"]') || "none";
  const hostLabels = {
    none: "Sem filtro de hospedeiro",
    sus_scrofa: "Sus scrofa (opt-in)",
    custom: getValue('#pipeline-form input[name="host_name"]') || "Índice customizado",
  };
  const rows = [
    ["Amostra", state.sample || "—"],
    ["Banco viral", state.database || "—"],
    ["Perfil", profile === "assembly-consensus" ? "Consenso entre montadores" : "Canônico E1"],
    ["Montagem", assembler || "—"],
    ["k-mer", getValue('#pipeline-form input[name="kmer"]') || "31"],
    ["Filtro do hospedeiro", hostLabels[hostMode] || hostMode],
    ["Controle de qualidade", document.querySelector('#pipeline-form input[name="skip_qc"]')?.checked ? "Ignorado" : "Ativado (fastp)"],
    ["Limite interpretativo", "Evidência computacional; fragmentos de 20–49 pb permanecem exploratórios."],
  ];
  const list = createElement(document, "dl", { class: "ux-review-list" });
  rows.forEach(([label, value]) => {
    list.append(
      createElement(document, "dt", { text: label }),
      createElement(document, "dd", { text: value }),
    );
  });
  body.replaceChildren(list);
}

function render(state) {
  renderContext(state);
  renderNextAction(state);
  renderStepper(state);
  renderPhaseDescription(state);
  renderSections(state);
  renderReview(state);
  updateGate(state);
}

function setStep(step) {
  const value = Math.max(0, Math.min(EXEC_STEPS.length - 1, Number(step) || 0));
  saveSessionValue("genein.ux.step", value);
  uiStore.set({ step: value });
}

function setMode(guided) {
  saveSessionValue("genein.ux.mode", guided ? "guided" : "all");
  uiStore.set({ guided });
}

function initializeWizard() {
  const panel = document.getElementById("tab-execucao");
  if (!panel || document.getElementById("ux-wizard-head")) return;
  sectionMap = Array.from(panel.querySelectorAll(":scope > section.section-card"))
    .map((element) => ({
      element,
      step: sectionStep(element.querySelector(".section-card__title")?.textContent),
    }))
    .filter(({ step }) => step >= 0);

  const header = createElement(document, "div", { id: "ux-wizard-head", class: "ux-wizard-head" });
  const quick = createElement(document, "div", { class: "ux-quickstart", "aria-label": "Início rápido" });
  [
    ["nova", "🧪 Nova análise", "Fluxo guiado do início ao resultado", true],
    ["continuar", "⏱️ Continuar execução", "Ir ao acompanhamento", false],
    ["demo", "▶️ Demonstração", "Exemplo reprodutível", false],
    ["historico", "🗂️ Histórico", "Execuções anteriores", false],
  ].forEach(([key, title, description, primary]) => {
    quick.append(createElement(document, "button", {
      type: "button",
      class: primary ? "primary" : "",
      dataset: { quickstart: key },
      onclick: () => {
        if (key === "nova") setStep(0);
        if (key === "continuar") setStep(4);
        if (key === "demo") {
          document.querySelector('[data-action="demo"]')?.click();
          setStep(0);
        }
        if (key === "historico") document.getElementById("tab-button-historico")?.click();
      },
    }, [
      createElement(document, "span", { class: "qs-title", text: title }),
      createElement(document, "span", { class: "qs-desc", text: description }),
    ]));
  });
  const mode = createElement(document, "div", { class: "ux-mode-toggle", role: "group", "aria-label": "Modo de exibição" }, [
    document.createTextNode("Exibição: "),
    createElement(document, "button", { id: "ux-mode-guided", type: "button", onclick: () => setMode(true), text: "Modo guiado" }),
    createElement(document, "button", { id: "ux-mode-all", type: "button", onclick: () => setMode(false), text: "Ver tudo" }),
  ]);
  header.append(
    quick,
    mode,
    createElement(document, "ol", { id: "ux-stepper", class: "ux-stepper", "aria-label": "Etapas da análise" }),
    createElement(document, "p", { id: "ux-step-description", class: "ux-step-description" }),
  );
  panel.insertBefore(header, panel.firstChild);

  panel.append(createElement(document, "div", { class: "ux-wizard-nav" }, [
    createElement(document, "button", { id: "ux-prev", class: "btn btn--secondary", type: "button", onclick: () => setStep(uiStore.get().step - 1), text: "← Anterior" }),
    createElement(document, "span", { id: "ux-gate-note", class: "ux-gate-note" }),
    createElement(document, "span", { class: "spacer" }),
    createElement(document, "button", { id: "ux-next", class: "btn btn--primary", type: "button", onclick: () => setStep(uiStore.get().step + 1), text: "Próximo →" }),
  ]));
}

function initializeReview() {
  const form = document.getElementById("pipeline-form");
  if (!form || document.getElementById("ux-review")) return;
  const review = createElement(document, "section", { id: "ux-review", class: "result-layer" });
  review.append(
    createElement(document, "header", {}, [
      createElement(document, "span", { class: "result-layer__num", text: "✓" }),
      createElement(document, "h4", { text: "Revisão antes de executar" }),
    ]),
    createElement(document, "div", { id: "ux-review-body", class: "result-layer__body" }),
  );
  form.parentNode.insertBefore(review, form);
}

function initializeResultLayers() {
  const output = document.getElementById("job-output");
  const section = output?.closest("section.section-card");
  if (!output || !section || section.dataset.uxLayered) return;
  section.dataset.uxLayered = "true";
  const makeLayer = (number, title) => {
    const layer = createElement(document, "section", { class: "result-layer" });
    const body = createElement(document, "div", { class: "result-layer__body" });
    layer.append(
      createElement(document, "header", {}, [
        createElement(document, "span", { class: "result-layer__num", text: number }),
        createElement(document, "h4", { text: title }),
      ]),
      body,
    );
    return [layer, body];
  };
  const definitions = [
    ["1", "Estado operacional da execução", [section.querySelector(".status-grid"), document.getElementById("final-status")]],
    ["2", "Progresso das etapas", [document.getElementById("pipeline-progress"), document.getElementById("cancel-job-btn")]],
    ["3", "Log de execução", [output]],
    ["4", "Relatório e interpretação", [document.getElementById("report-viewer")]],
  ];
  definitions.forEach(([number, title, nodes], index) => {
    const [layer, body] = makeLayer(number, title);
    nodes.filter(Boolean).forEach((node) => body.append(node));
    if (index === 3) {
      body.append(createElement(document, "div", { class: "notice notice--info" }, [
        createElement(document, "strong", { text: "Interpretação conservadora. " }),
        document.createTextNode("Fragmentos candidatos representam evidência computacional e requerem validação complementar; não constituem diagnóstico."),
      ]));
    }
    section.append(layer);
  });
}

function initializeHistoryFilter() {
  const search = document.getElementById("history-search");
  const list = document.getElementById("history-list");
  if (!search || !list) return;
  search.addEventListener("input", () => {
    const query = search.value.toLowerCase().trim();
    Array.from(list.children).forEach((item) => {
      item.hidden = Boolean(query) && !item.textContent.toLowerCase().includes(query);
    });
  });
}

function synchronizeProfileControls() {
  document.querySelectorAll("[data-profile-selector]").forEach((profile) => {
    const form = profile.closest("form");
    const assembler = form?.querySelector("[data-assembler-selector]");
    const help = form?.querySelector("[data-profile-help]");
    const apply = () => {
      const consensus = profile.value === "assembly-consensus";
      if (assembler) setDisabled(assembler, consensus, "O perfil de consenso seleciona os três montadores automaticamente.");
      if (help) help.textContent = consensus
        ? "Executa Velvet, SPAdes e metaSPAdes quando aplicável e exige concordância mínima de dois."
        : "Usa o montador selecionado e mantém o teto E1.";
      synchronizeState();
    };
    profile.addEventListener("change", apply);
    apply();
  });
  const warning = document.querySelector(".evidence-shadow-warning");
  if (warning) warning.textContent = "Evidence V2 ativo no teto E1. A saída é evidência computacional; E2/E3 permanecem bloqueados e o resultado oficial 1.1 continua separado.";
  const evidenceButton = document.querySelector("#evidence-individual-form button[type=submit]");
  if (evidenceButton) evidenceButton.textContent = "Executar Evidence V2 · teto E1";
}

function synchronizeTabs() {
  document.querySelectorAll("[role=tab][data-tab]").forEach((tab) => {
    const apply = () => {
      document.querySelectorAll("[role=tab][data-tab]").forEach((candidate) => {
        const selected = candidate.classList.contains("active");
        candidate.setAttribute("aria-selected", selected ? "true" : "false");
        candidate.setAttribute("aria-current", selected ? "page" : "false");
        candidate.tabIndex = selected ? 0 : -1;
      });
    };
    tab.addEventListener("click", () => setTimeout(apply, 0));
  });
}

async function loadPreflight() {
  try {
    const result = await getJSON("/api/preflight");
    renderPreflightDetail(result);
    uiStore.set({
      environment: result.ok ? "ok" : "pending",
      environmentSummary: result.summary || (result.ok ? "Ambiente pronto." : "Ambiente com pendências."),
    });
  } catch (_) {
    renderPreflightDetail({ summary: "Não foi possível verificar as ferramentas do ambiente efetivo." });
    uiStore.set({
      environment: "error",
      environmentSummary: "Não foi possível verificar as ferramentas do ambiente efetivo.",
    });
  }
}

export function initializeGuidedDashboard() {
  initializeResultLayers();
  initializeReview();
  initializeWizard();
  initializeHistoryFilter();
  synchronizeProfileControls();
  synchronizeTabs();
  synchronizeState();
  uiStore.subscribe(render);
  render(uiStore.get());

  const observer = new MutationObserver(synchronizeState);
  ["job-status", "job-action", "db-status", "sample-select", "host-index-status"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) observer.observe(element, { childList: true, subtree: true, attributes: true });
  });
  document.getElementById("tab-execucao")?.addEventListener("input", synchronizeState);
  document.getElementById("tab-execucao")?.addEventListener("change", synchronizeState);
  document.getElementById("pipeline-form")?.addEventListener("submit", () => setTimeout(() => setStep(4), 0));
  loadPreflight();
}
