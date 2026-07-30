import { initializeGuidedDashboard } from "./js/guided.js";
import { isActiveJobStatus } from "./js/jobs.js";

// Defensive element guards - get elements safely
const getEl = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`Missing element: ${id}`);
  return el;
};


const statusEl = getEl("job-status");
const actionEl = getEl("job-action");
const outputEl = getEl("job-output");
const samplesDatalist = getEl("samples");
const sampleSelectEl = getEl("sample-select");
const finalStatusEl = getEl("final-status");
const historyListEl = getEl("history-list");
const pipelineProgressEl = getEl("pipeline-progress");
const reportViewerEl = getEl("report-viewer");
const reportContentEl = getEl("report-content");
const dbTargetEl = getEl("db-target");
const dbStatusEl = getEl("db-status");
const configFormEl = getEl("config-form");
const configStatusEl = getEl("config-status");
const rebuildEnvBtnEl = getEl("rebuild-env-btn");
const rebuildStatusEl = getEl("rebuild-status");
const envFileStatusEl = getEl("env-file-status");
const envMtimeEl = getEl("env-mtime");
const envPathEl = getEl("env-path");
const tsvModalOverlayEl = getEl("tsv-modal-overlay");
const tsvModalContentEl = getEl("tsv-modal-content");
const tsvModalCloseEl = getEl("tsv-modal-close");
const cleanupBtnEl = getEl("cleanup-btn");
const cleanupStatusEl = getEl("cleanup-status");
const cancelJobBtnEl = getEl("cancel-job-btn");
const cancelAdvBtnEl = getEl("cancel-adv-btn");
const assemblyOnlySampleSelectEl = getEl("assembly-only-sample-select");
const assemblyOnlyStatusEl = getEl("assembly-only-status");
const hostFilterModeEl = getEl("host-filter-mode");
const hostIndexPrefixEl = getEl("host-index-prefix");
const hostIndexStatusEl = getEl("host-index-status");
const evidenceHostFilterModeEl = getEl("evidence-host-filter-mode");
const evidenceBatchHostFilterModeEl = getEl("evidence-batch-host-filter-mode");

// Elements for tab-analise-avancada
const advancedSampleSelectEl = getEl("advanced-sample-select");
const advStatusEl = getEl("adv-status");
const advOutputEl = getEl("adv-output");
const advReportViewerEl = getEl("adv-report-viewer");
const advReportContentEl = getEl("adv-report-content");

// Constants
const JOB_POLL_INTERVAL_MS = 1200;
const MAX_POLL_RETRIES = 7;

// State to remember last selected DB
let currentDB = {
  target: null,
  query: null,
  taxid: null,
  ncbi_db: null
};

// Track active job IDs to allow cancellation
let activeJobId = null;
let activeAdvJobId = null;

// Early abort if essential elements are missing
if (!statusEl || !outputEl || !finalStatusEl) {
  console.error("Critical UI elements missing. Dashboard cannot initialize.");
}

const stageConfig = {
  qc: { marker: "[2.5/6]", label: "Controle de qualidade" },
  host: { marker: "[3/6]", label: "Remoção de hospedeiro" },
  assembly: { marker: "[4/6]", label: "Montagem" },
  blast: { marker: "[5/6]", label: "BLAST" },
};

const stageIcon = { pending: "⏳", running: "🔄", done: "✅", error: "❌", skipped: "⏭️" };

const setStatus = (status, action) => {
  if (statusEl) statusEl.textContent = status;
  if (action && actionEl) actionEl.textContent = action;
};

const updateDBStatus = () => {
  if (!dbStatusEl) return;
  if (currentDB.target || currentDB.query) {
    // Support both old short keys (ptv, evg, psv) and new targets.json keys (teschovirus_a, etc.)
    const displayMap = {
      ptv: "Teschovirus A (PTV)",
      evg: "Enterovirus G",
      psv: "Sapelovirus A",
      svv: "Senecavirus A",
      fmdv: "FMDV (aftosa)",
      teschovirus_a: "Teschovirus A (PTV)",
      sapelovirus_a: "Sapelovirus A",
      enterovirus_g: "Enterovirus G",
      astrovirus_suino: "Astrovirus Suíno",
      picornaviridae_refseq: "Picornaviridae (RefSeq)",
      picornaviridae_complete: "Picornaviridae (complete genome)",
      picornaviridae_all: "Picornaviridae (ALL)",
      custom: "Query Customizada",
    };
    let displayText;
    if (currentDB.target) {
      displayText = displayMap[currentDB.target] || currentDB.target;
    } else {
      // Apenas query customizada — mostra trecho da query como rótulo
      const q = currentDB.query || "";
      displayText = `Banco customizado: ${q.length > 60 ? q.slice(0, 57) + "…" : q}`;
    }
    dbStatusEl.textContent = `DB ativo: ${displayText}`;
    dbStatusEl.className = "db-status active";
  } else {
    dbStatusEl.textContent = "DB: nenhum selecionado";
    dbStatusEl.className = "db-status";
  }
};


const setOutput = (text) => {
  if (!outputEl) return;
  outputEl.textContent = text || "";
  outputEl.scrollTop = outputEl.scrollHeight;
};

const setFinalStatus = (html, tone = "") => {
  if (!finalStatusEl) return;
  finalStatusEl.className = `final-status ${tone}`.trim();
  finalStatusEl.innerHTML = html || "";
};

const showFriendlyError = (tail, logLink) => {
  if (!tail) {
    setFinalStatus(`<strong>FALHA</strong> ❌ Sem log disponível.${logLink}`, "error");
    return;
  }

  // Regex para capturar log padronizado: [NÍVEL] [ETAPA] [AMOSTRA] — descrição — ação
  const regex = /\[(FATAL|AVISO|RECUPERADO|ERROR|WARN|INFO)\]\s*\[(.*?)\]\s*\[(.*?)\]\s*—\s*([^-]+?)(?:\s*—\s*(.*))?$/mi;
  const match = tail.match(regex);

  if (match) {
    const level = match[1].toUpperCase();
    const stage = match[2];
    const sample = match[3];
    const description = match[4].trim();
    const action = match[5] ? match[5].trim() : "";

    let alertClass = "error";
    let icon = "❌";
    let borderClr = "#e74c3c";
    let bgClr = "#fdf2f2";
    if (level === "AVISO" || level === "WARN") {
      alertClass = "warning";
      icon = "⚠️";
      borderClr = "#f39c12";
      bgClr = "#fef9e7";
    } else if (level === "RECUPERADO") {
      alertClass = "recovered";
      icon = "🔄";
      borderClr = "#3498db";
      bgClr = "#ebf5fb";
    }

    // Stage, sample, description and suggested action originate in the job log.
    // Keep the rich status card, but never treat log content as markup.
    const safeStage = escapeHTML(stage);
    const safeSample = escapeHTML(sample);
    const safeDescription = escapeHTML(description);
    const safeAction = escapeHTML(action);
    let actionHtml = action
      ? `<br><strong style="color: #444; display: inline-block; margin-top: 0.3rem;">Sugestão:</strong> <span style="font-style: italic;">${safeAction}</span>`
      : "";

    const bannerHtml = `
      <div class="error-banner ${alertClass}" style="margin: 0.5rem 0; padding: 1rem; border-left: 5px solid ${borderClr}; background: ${bgClr}; border-radius: 4px; text-align: left;">
        <div style="font-weight: bold; margin-bottom: 0.3rem; font-size: 1.05rem;">
          ${icon} Falha na etapa: <code style="background: rgba(0,0,0,0.05); padding: 2px 4px; border-radius: 3px;">${safeStage}</code> (Amostra: ${safeSample})
        </div>
        <div style="margin-bottom: 0.5rem; line-height: 1.4;">${safeDescription}${actionHtml}</div>
        <details style="margin-top: 0.8rem; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 0.5rem;">
          <summary style="cursor: pointer; font-size: 0.85rem; font-weight: bold; color: #666; outline: none;">Visualizar Detalhes Técnicos de Depuração (Tail do Log)</summary>
          <pre style="margin-top: 0.5rem; font-size: 0.82rem; background: #fafafa; padding: 0.5rem; border: 1px solid #eee; overflow-x: auto; max-height: 250px; text-align: left;">${escapeHTML(tail)}</pre>
        </details>
      </div>
      ${logLink}
    `;
    setFinalStatus(bannerHtml, alertClass);
  } else {
    // Tratamento genérico para erros que não seguem o formato padronizado (tracebacks Python, etc.)
    const lines = tail.split('\n');
    let lastLineWithText = "Erro indefinido na execução do pipeline.";
    for (let i = lines.length - 1; i >= 0; i--) {
      const trimmed = lines[i].trim();
      if (trimmed && !trimmed.startsWith("at ") && !trimmed.startsWith("Traceback") && !trimmed.startsWith("File ")) {
        lastLineWithText = trimmed;
        break;
      }
    }

    const bannerHtml = `
      <div class="error-banner error" style="margin: 0.5rem 0; padding: 1rem; border-left: 5px solid #e74c3c; background: #fdf2f2; border-radius: 4px; text-align: left;">
        <div style="font-weight: bold; margin-bottom: 0.3rem; font-size: 1.05rem;">
          ❌ Falha de Execução
        </div>
        <div style="margin-bottom: 0.5rem; line-height: 1.4; color: #c0392b; font-weight: 500;">${escapeHTML(lastLineWithText)}</div>
        <details style="margin-top: 0.8rem; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 0.5rem;">
          <summary style="cursor: pointer; font-size: 0.85rem; font-weight: bold; color: #666; outline: none;">Visualizar Detalhes Técnicos de Depuração (Tail do Log)</summary>
          <pre style="margin-top: 0.5rem; font-size: 0.82rem; background: #fafafa; padding: 0.5rem; border: 1px solid #eee; overflow-x: auto; max-height: 250px; text-align: left;">${escapeHTML(tail)}</pre>
        </details>
      </div>
      ${logLink}
    `;
    setFinalStatus(bannerHtml, "error");
  }
};

const setReportContent = (content) => {
  if (!reportContentEl || !reportViewerEl) return;
  reportContentEl.textContent = content || "";
  reportViewerEl.hidden = !content;
};

const initPipelineProgress = () => {
  if (!pipelineProgressEl) return;
  pipelineProgressEl.querySelectorAll("li[data-stage]").forEach((item) => {
    item.dataset.state = "pending";
    item.querySelector(".stage-icon").textContent = stageIcon.pending;
  });
};

const showPipelineProgress = (show) => {
  if (!pipelineProgressEl) return;
  pipelineProgressEl.hidden = !show;
  if (show) initPipelineProgress();
};

const applyStageState = (stage, state) => {
  if (!pipelineProgressEl) return;
  const item = pipelineProgressEl.querySelector(`li[data-stage="${stage}"]`);
  if (!item) return;
  item.dataset.state = state;
  item.querySelector(".stage-icon").textContent = stageIcon[state] || stageIcon.pending;
};

const updatePipelineProgressFromOutput = (output, jobStatus) => {
  const hasQC = output.includes(stageConfig.qc.marker);
  const skippedQC = output.includes("Controle de qualidade (fastp) ignorado") || output.includes("fastp não encontrado");
  const hasHost = output.includes(stageConfig.host.marker);
  const hasAssembly = output.includes(stageConfig.assembly.marker);
  const hasBlast = output.includes(stageConfig.blast.marker);
  const skippedHost = output.includes("Indice do hospedeiro") ||
    output.includes("Índice do hospedeiro") ||
    output.includes("Filtro do hospedeiro ignorado") ||
    output.includes("HOST_FILTER_ENABLED=false");

  applyStageState("qc", skippedQC ? "skipped" : (hasQC ? "done" : "pending"));
  applyStageState("host", skippedHost ? "skipped" : (hasHost ? "done" : (hasQC || skippedQC ? "running" : "pending")));
  applyStageState("assembly", hasAssembly ? "done" : (hasHost || skippedHost ? "running" : "pending"));
  applyStageState("blast", hasBlast ? "running" : "pending");

  if (jobStatus === "done") applyStageState("blast", "done");
  if (jobStatus === "error") {
    if (hasBlast) applyStageState("blast", "error");
    else if (hasAssembly) applyStageState("assembly", "error");
    else if (hasHost || skippedHost) applyStageState("host", "error");
    else if (hasQC || skippedQC) applyStageState("qc", "error");
  }
};

const fetchTargets = async () => {
  if (!dbTargetEl) return;
  try {
    const response = await fetch("/api/targets");
    if (!response.ok) return;
    const data = await response.json();
    const targets = data.targets || [];
    if (!targets.length) return;
    // Clear and rebuild options, always keeping a blank/neutral first option
    dbTargetEl.innerHTML = "";
    const customOpt = document.createElement("option");
    customOpt.value = "";
    customOpt.textContent = "Outro vírus / banco customizado";
    dbTargetEl.appendChild(customOpt);
    targets.forEach((target) => {
      const option = document.createElement("option");
      option.value = target.key;
      option.textContent = `${target.display_name} (${target.key})`;
      dbTargetEl.appendChild(option);
    });
  } catch (err) {
    console.error("Falha ao listar targets", err);
    // Keep hardcoded fallback options already in the HTML
  }
};

const fetchSamples = async () => {
  try {
    const response = await fetch("/api/samples");
    if (!response.ok) return;
    const data = await response.json();
    if (samplesDatalist) samplesDatalist.innerHTML = "";
    if (sampleSelectEl) sampleSelectEl.innerHTML = '<option value="">Selecione uma amostra</option>';
    if (advancedSampleSelectEl) advancedSampleSelectEl.innerHTML = '<option value="">Selecione uma amostra</option>';
    if (assemblyOnlySampleSelectEl) assemblyOnlySampleSelectEl.innerHTML = '<option value="">Selecione uma amostra</option>';
    (data.samples || []).forEach((sample) => {
      if (samplesDatalist) {
        const option = document.createElement("option");
        option.value = sample;
        samplesDatalist.appendChild(option);
      }

      if (sampleSelectEl) {
        const selectOption = document.createElement("option");
        selectOption.value = sample;
        selectOption.textContent = sample;
        sampleSelectEl.appendChild(selectOption);
      }

      if (advancedSampleSelectEl) {
        const selectOption = document.createElement("option");
        selectOption.value = sample;
        selectOption.textContent = sample;
        advancedSampleSelectEl.appendChild(selectOption);
      }

      if (assemblyOnlySampleSelectEl) {
        const selectOption = document.createElement("option");
        selectOption.value = sample;
        selectOption.textContent = sample;
        assemblyOnlySampleSelectEl.appendChild(selectOption);
      }
    });
  } catch (err) {
    console.error("Falha ao listar amostras", err);
  }
};

const openRunArtifact = (runDir, fileType) => {
  window.open(`/api/history/file?run=${encodeURIComponent(runDir)}&type=${encodeURIComponent(fileType)}`, "_blank");
};

const EVIDENCE_CLASS_ROW = {
  STRONG: "tsv-row-strong",
  STRONG_DIVERGENT: "tsv-row-strong-divergent",
  MODERATE: "tsv-row-moderate",
  WEAK_RECOVERABLE: "tsv-row-weak-recoverable",
  REVIEW: "tsv-row-review",
};

const parseTSV = (text) => {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return { headers: [], rows: [] };
  const headers = lines[0].split("\t");
  const rows = lines.slice(1).map((l) => l.split("\t"));
  return { headers, rows };
};

const escapeHTML = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));

const renderTSVTable = ({ headers, rows }) => {
  if (!headers.length) return '<p class="tsv-empty">Arquivo vazio ou sem dados.</p>';

  const classIdx = headers.findIndex((h) => h === "evidence_class");

  const ths = headers.map((h) => `<th>${escapeHTML(h)}</th>`).join("");
  const trs = rows.map((cells) => {
    const cls = classIdx >= 0 ? (cells[classIdx] || "").trim() : "";
    const rowClass = EVIDENCE_CLASS_ROW[cls] || "";
    const tds = headers.map((_, i) => `<td>${escapeHTML(cells[i] !== undefined ? cells[i] : "")}</td>`).join("");
    return `<tr class="${rowClass}">${tds}</tr>`;
  }).join("");

  return `<table class="tsv-table"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
};

const openLabeledTSV = async (runDir) => {
  if (!tsvModalOverlayEl || !tsvModalContentEl) {
    openRunArtifact(runDir, "labeled");
    return;
  }
  tsvModalContentEl.innerHTML = '<p class="tsv-empty">Carregando...</p>';
  tsvModalOverlayEl.hidden = false;
  document.body.style.overflow = "hidden";
  try {
    const response = await fetch(`/api/history/file?run=${encodeURIComponent(runDir)}&type=labeled`);
    if (!response.ok) {
      tsvModalContentEl.innerHTML = `<p class="tsv-empty">Arquivo não encontrado (HTTP ${escapeHTML(String(response.status))}).</p>`;
      return;
    }
    const text = await response.text();
    tsvModalContentEl.innerHTML = renderTSVTable(parseTSV(text));
  } catch (err) {
    console.error("[openLabeledTSV] Erro ao carregar TSV:", err);
    tsvModalContentEl.innerHTML = `<p class="tsv-empty">Erro ao carregar: ${escapeHTML(err.message)}</p>`;
  }
};

const closeTSVModal = () => {
  if (!tsvModalOverlayEl) return;
  tsvModalOverlayEl.hidden = true;
  document.body.style.overflow = "";
};

const cleanupTempFiles = async () => {
  if (!confirm("Deseja remover os arquivos temporários pesados dos montadores?\n\nSerão apagados diretórios intermediários do SPAdes/Velvet em data/assemblies/.\nOs arquivos contigs.fa/contigs.fasta, resultados BLAST, relatórios e histórico serão preservados.\n\nEssa ação não pode ser desfeita.")) {
    return;
  }
  if (cleanupStatusEl) {
    cleanupStatusEl.className = "final-status ok";
    cleanupStatusEl.innerHTML = "⏳ Limpando...";
  }
  try {
    const response = await fetch("/api/cleanup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const data = await response.json();
    if (response.ok && data.success) {
      const count = (data.removed || []).length;
      cleanupStatusEl.className = "final-status ok";
      cleanupStatusEl.innerHTML = `<strong>SUCESSO</strong> ✅ ${escapeHTML(String(count))} diretório(s) removido(s). ${data.freed_bytes ? `Liberado: ~${escapeHTML((data.freed_bytes / 1048576).toFixed(1))} MB` : ""}`;
    } else {
      cleanupStatusEl.className = "final-status error";
      cleanupStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(data.error || "Falha na limpeza")}`;
    }
  } catch (err) {
    if (cleanupStatusEl) {
      cleanupStatusEl.className = "final-status error";
      cleanupStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(err.message)}`;
    }
  }
};

const loadReportInline = async (runDir) => {
  if (!runDir) return setReportContent("Sem informações de diretório para carregar o resumo.");
  try {
    const response = await fetch(`/api/history/file?run=${encodeURIComponent(runDir)}&type=report`);
    if (!response.ok) return setReportContent("O pipeline terminou, mas nenhum relatório final validado foi disponibilizado. Consulte o log e os artefatos da execução.");
    const text = await response.text();
    if (!text.trim()) return setReportContent("Relatório vazio; isso não demonstra ausência de material viral.");
    setReportContent(text);
  } catch (err) {
    console.error("Falha ao carregar resumo", err);
    setReportContent("Erro de rede ao tentar carregar o resumo.");
  }
};

const rerunHistory = async (runDir) => {
  try {
    const response = await fetch("/api/history/rerun", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_dir: runDir }),
    });
    if (!response.ok) {
      const msg = await response.text();
      console.error(`[rerunHistory] Erro HTTP ${response.status} ao reexecutar run_dir='${runDir}':`, msg);
      return alert(`Falha ao reexecutar: ${msg}`);
    }
    const data = await response.json();
    const jobId = extractJobId(data, "[rerunHistory]");
    if (!jobId) return alert("Resposta inválida do servidor (sem job_id)");
    setStatus("Executando...", `rerun:${runDir}`);
    setOutput("");
    setFinalStatus("");
    showPipelineProgress(true);
    pollJob(jobId, `rerun:${runDir}`);
  } catch (err) {
    console.error(`[rerunHistory] Exceção ao reexecutar run_dir='${runDir}':`, err);
    alert(`Erro de rede ao reexecutar: ${err.message}`);
  }
};

const activateDashboardTab = (panelId, { focus = false } = {}) => {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  tabs.forEach((item) => {
    const active = item.dataset.tab === panelId;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    if (active && focus) item.focus();
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelId);
  });
  if (panelId === "tab-historico") fetchHistory();
  if (panelId === "tab-analise-avancada") fetchSamples();
  if (panelId === "tab-configuracao") {
    loadEnvironmentStatus();
    loadConfigEnv();
  }
};

const renderHistory = (runs) => {
  if (!historyListEl) return;
  if (!runs.length) {
    historyListEl.innerHTML = "<p>Nenhuma execução registrada ainda.</p>";
    return;
  }
  historyListEl.innerHTML = "";
  runs.forEach((run) => {
    const card = document.createElement("article");
    card.className = "history-item";
    if (run.evidence_v2) {
      const alpha2Valid = run.valid_alpha2 === true;
      const successful = alpha2Valid && (run.status === "done" || run.status === "done_with_warning");
      const evidenceLabel = alpha2Valid ? "Evidence V2 Alpha.2 experimental" : (run.compatibility_status || "NOT_EVALUABLE");
      const openLabel = alpha2Valid
        ? "Abrir resultado experimental"
        : (run.complete ? "Abrir estado incompatível" : "Abrir estado operacional");
      card.innerHTML = `
        <header><h3>${escapeHTML(run.sample) || "(lote V2)"}</h3><span class="badge ${successful ? "ok" : "error"}">${escapeHTML(run.status || "unknown")}</span></header>
        <p><strong>Evidence V2 experimental</strong> · teto E1 · run_id ${escapeHTML(run.run_id)}</p>
        <p><strong>Início:</strong> ${escapeHTML((run.start || "-").replace("T", " "))} • <strong>Fim:</strong> ${escapeHTML((run.end || "-").replace("T", " "))}</p>
        <div class="actions"><button data-evidence-open="1">Abrir resultado experimental</button></div>`;
      const evidenceHeading = card.querySelector("p strong");
      if (evidenceHeading) evidenceHeading.textContent = evidenceLabel;
      const openButton = card.querySelector("button[data-evidence-open]");
      if (openButton) openButton.textContent = openLabel;
      const statusDetail = document.createElement("p");
      statusDetail.textContent = `1.1: ${run.official_v1_status || "not_started"} · Evidence V2: ${run.evidence_v2_status || run.status}${run.failure_type ? ` · falha: ${run.failure_type}` : ""}`;
      const actions = card.querySelector(".actions");
      if (actions) card.insertBefore(statusDetail, actions);
      if (run.experimental_warning) {
        const warning = document.createElement("p");
        warning.className = "evidence-shadow-warning";
        warning.textContent = run.experimental_warning;
        if (actions) card.insertBefore(warning, actions);
      }
      if (run.failure_message || run.compatibility_message) {
        const detail = document.createElement("p");
        detail.className = "status-line error";
        detail.textContent = run.failure_message || run.compatibility_message;
        if (actions) card.insertBefore(detail, actions);
      }
      card.querySelector("button[data-evidence-open]")?.addEventListener("click", async () => {
        activeEvidenceRunId = run.run_id;
        activateDashboardTab("tab-evidence-v2");
        try { renderEvidenceStages(await evidenceApi(`/api/evidence/run?id=${encodeURIComponent(run.run_id)}`)); renderEvidenceResult(await evidenceApi(`/api/evidence/result?run=${encodeURIComponent(run.run_id)}`)); }
        catch (error) { setEvidenceText("evidence-run-status", error.message, "error"); }
      });
      historyListEl.appendChild(card);
      return;
    }
    const statusClass = run.exit_code === 0 ? "ok" : "error";
    card.innerHTML = `
      <header><h3>${escapeHTML(run.sample) || "(sem sample)"}</h3><span class="badge ${statusClass}">${run.exit_code === 0 ? "SUCESSO" : "FALHA"}</span></header>
      <p><strong>Início:</strong> ${escapeHTML((run.start || "-").replace("T", " "))} • <strong>Fim:</strong> ${escapeHTML((run.end || "-").replace("T", " "))}</p>
      <div class="actions">
        <button data-open="report">📋 Abrir Report</button>
        <button data-open="log">⚙️ Abrir Log</button>
        <button data-open="blast">🔍 BLAST Bruto</button>
        <button data-open="labeled" class="primary">🔬 Revisar hits classificados</button>
        <button data-open="adj_identity">📊 Identidade Adj.</button>
        ${run.paths && run.paths.run_hit_contigs_fasta ? `<button data-open="hit_contigs_fasta">⬇ FASTA Hits</button>` : ''}
        <button data-rerun="1">🔄 Reexecutar</button>
      </div>`;

    card.querySelectorAll("button[data-open]").forEach((button) => {
      if (button.dataset.open === "labeled") {
        button.addEventListener("click", () => openLabeledTSV(run.run_dir));
      } else {
        button.addEventListener("click", () => openRunArtifact(run.run_dir, button.dataset.open));
      }
    });
    card.querySelector("button[data-rerun]").addEventListener("click", () => rerunHistory(run.run_dir));
    historyListEl.appendChild(card);
  });
};

const fetchHistory = async () => {
  try {
    const response = await fetch("/api/history");
    if (!response.ok) return;
    renderHistory((await response.json()).runs || []);
  } catch (err) {
    console.error("Falha ao carregar histórico", err);
  }
};

const loadEnvironmentStatus = async () => {
  try {
    const response = await fetch("/api/config/environment");
    if (!response.ok) {
      if (envFileStatusEl) envFileStatusEl.textContent = "Erro ao carregar";
      return;
    }
    const data = await response.json();

    const mountWarningEl = getEl("mount-warning");
    if (mountWarningEl && data.running_on_windows_mount) {
      mountWarningEl.hidden = false;
    } else if (mountWarningEl) {
      mountWarningEl.hidden = true;
    }

    if (envFileStatusEl) {
      envFileStatusEl.textContent = data.has_environment_yml ? "Encontrado ✅" : "Não encontrado ❌";
    }
    if (envMtimeEl) {
      envMtimeEl.textContent = data.environment_yml_mtime ? data.environment_yml_mtime.replace("T", " ") : "N/A";
    }
    if (envPathEl) {
      envPathEl.textContent = data.environment_yml_path || "N/A";
    }
  } catch (err) {
    console.error("Falha ao carregar status do ambiente", err);
    if (envFileStatusEl) envFileStatusEl.textContent = "Erro ao carregar";
  }
};

const loadConfigEnv = async () => {
  if (!configFormEl) return;

  try {
    const response = await fetch("/api/config/env");
    if (!response.ok) {
      console.error("Falha ao carregar configuração");
      return;
    }
    const data = await response.json();
    const config = data.config || {};

    // Populate form fields
    Object.keys(config).forEach((key) => {
      const input = configFormEl.querySelector(`[name="${key}"]`);
      if (input) {
        input.value = config[key] || "";
      }
    });
  } catch (err) {
    console.error("Falha ao carregar configuração", err);
  }
};

const updateHostFilterFields = () => {
  const mode = hostFilterModeEl ? hostFilterModeEl.value : "none";
  document.querySelectorAll("[data-host-custom]").forEach((el) => {
    el.hidden = mode !== "custom";
  });
  if (hostIndexStatusEl && mode !== "custom") {
    hostIndexStatusEl.textContent = "";
    hostIndexStatusEl.className = "field-hint";
  }
};

const setHostIndexStatus = (message, ok = null) => {
  if (!hostIndexStatusEl) return;
  hostIndexStatusEl.textContent = message || "";
  hostIndexStatusEl.className = ok === null ? "field-hint" : `field-hint ${ok ? "ok" : "error"}`;
};

const validateCustomHostIndex = async () => {
  const mode = hostFilterModeEl ? hostFilterModeEl.value : "none";
  if (mode !== "custom") return true;
  const prefix = (hostIndexPrefixEl?.value || "").trim();
  if (!prefix) {
    setHostIndexStatus("Informe o prefixo do indice Bowtie2.", false);
    return false;
  }
  setHostIndexStatus("Validando indice...", null);
  try {
    const response = await fetch("/api/host-index/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prefix }),
    });
    const result = await response.json();
    setHostIndexStatus(result.message || (response.ok ? "Indice valido." : "Indice invalido."), response.ok);
    return response.ok;
  } catch (err) {
    setHostIndexStatus(`Erro ao validar indice: ${err.message}`, false);
    return false;
  }
};

const saveConfigEnv = async (event) => {
  event.preventDefault();
  if (!configFormEl || !configStatusEl) return;

  const formData = new FormData(configFormEl);
  const config = {};

  // Collect non-empty values
  for (const [key, value] of formData.entries()) {
    if (value.trim()) {
      config[key] = value.trim();
    }
  }

  try {
    const response = await fetch("/api/config/env", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      configStatusEl.className = "final-status ok";
      configStatusEl.innerHTML = `<strong>SUCESSO</strong> ✅ ${escapeHTML(result.message)}`;
    } else {
      configStatusEl.className = "final-status error";
      configStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(result.error || "Falha ao salvar configuração")}`;
    }
  } catch (err) {
    configStatusEl.className = "final-status error";
    configStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(err.message)}`;
  }
};

const rebuildEnvironment = async () => {
  if (!rebuildEnvBtnEl || !rebuildStatusEl) return;

  rebuildStatusEl.className = "final-status";
  rebuildStatusEl.innerHTML = "";

  try {
    const response = await fetch("/api/config/environment/rebuild", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const result = await response.json();
      rebuildStatusEl.className = "final-status error";
      rebuildStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(result.error || "Falha ao iniciar recriação")}`;
      return;
    }

    const { job_id: jobId } = await response.json();
    rebuildStatusEl.className = "final-status ok";
    rebuildStatusEl.innerHTML = "<strong>Recriando ambiente...</strong> ⏳ Aguarde a conclusão.";

    // Poll the job
    const interval = setInterval(async () => {
      const jobResponse = await fetch(`/api/job/${jobId}`);
      if (!jobResponse.ok) {
        clearInterval(interval);
        rebuildStatusEl.className = "final-status error";
        rebuildStatusEl.innerHTML = "<strong>ERRO</strong> ❌ Falha ao consultar status do job";
        return;
      }

      const jobData = await jobResponse.json();

      if (isActiveJobStatus(jobData.status)) {
        return;
      }

      clearInterval(interval);

      if (jobData.status === "done") {
        rebuildStatusEl.className = "final-status ok";
        rebuildStatusEl.innerHTML = "<strong>SUCESSO</strong> ✅ Ambiente recriado com sucesso";
        loadEnvironmentStatus();
      } else {
        rebuildStatusEl.className = "final-status error";
        rebuildStatusEl.innerHTML = `<strong>ERRO</strong> ❌<pre>${escapeHTML(jobData.tail || "Falha ao recriar ambiente")}</pre>`;
      }
    }, JOB_POLL_INTERVAL_MS);
  } catch (err) {
    rebuildStatusEl.className = "final-status error";
    rebuildStatusEl.innerHTML = `<strong>ERRO</strong> ❌ ${escapeHTML(err.message)}`;
  }
};

/** Validate and extract job_id from an API response object, logging a warning if missing. */
const extractJobId = (data, context = "") => {
  if (!data || typeof data.job_id !== "string" || !data.job_id.trim()) {
    console.error(`${context} Resposta sem job_id:`, data);
    return null;
  }
  return data.job_id.trim();
};

const runAction = async (action, params = {}) => {
  if (action === "advanced_analysis") {
    if (advStatusEl) advStatusEl.textContent = "Iniciando...";
    if (advOutputEl) {
      advOutputEl.style.display = "block";
      advOutputEl.textContent = "";
    }
    if (advReportViewerEl) advReportViewerEl.hidden = true;
    if (advReportContentEl) advReportContentEl.textContent = "";
  } else {
    setStatus("Executando...", action);
    setOutput("");
    setFinalStatus("");
    setReportContent("");
  }
  showPipelineProgress(action === "pipeline");

  // Show cancel button for pipeline and build_db; hide it first for a clean state
  if (action === "pipeline" || action === "build_db") {
    if (cancelJobBtnEl) cancelJobBtnEl.hidden = false;
  }
  if (action === "advanced_analysis") {
    if (cancelAdvBtnEl) cancelAdvBtnEl.hidden = false;
  }
  if (action === "assembly_only") {
    if (assemblyOnlyStatusEl) {
      assemblyOnlyStatusEl.className = "final-status";
      assemblyOnlyStatusEl.innerHTML = "⏳ Montando...";
    }
  }

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, params }),
    });

    if (!response.ok) {
      const msg = (await response.text()) || "Falha ao iniciar";
      console.error(`[runAction] Erro HTTP ${response.status} ao iniciar ação '${action}':`, msg);
      if (action === "advanced_analysis") {
        if (advStatusEl) advStatusEl.textContent = "Erro ao iniciar";
        if (advOutputEl) advOutputEl.textContent = msg;
      } else {
        setStatus("Erro ao iniciar", action);
        setOutput(msg);
        setFinalStatus(`<strong>ERRO</strong> ❌ Falha ao iniciar ação: ${msg}`, "error");
      }
      return;
    }

    const data = await response.json();
    const jobId = extractJobId(data, `[runAction '${action}']`);
    if (!jobId) {
      if (action === "advanced_analysis") {
        if (advStatusEl) advStatusEl.textContent = "Erro ao iniciar";
        if (cancelAdvBtnEl) cancelAdvBtnEl.hidden = true;
      } else {
        setStatus("Erro ao iniciar", action);
        setFinalStatus("<strong>ERRO</strong> ❌ Resposta inválida do servidor (sem job_id)", "error");
        if (cancelJobBtnEl) cancelJobBtnEl.hidden = true;
      }
      return;
    }
    // Store active job id for cancellation
    if (action === "advanced_analysis") {
      activeAdvJobId = jobId;
    } else {
      activeJobId = jobId;
    }
    pollJob(jobId, action);
  } catch (err) {
    console.error(`[runAction] Exceção ao iniciar ação '${action}':`, err);
    if (action === "advanced_analysis") {
      if (advStatusEl) advStatusEl.textContent = "Erro ao iniciar";
      if (advOutputEl) advOutputEl.textContent = err.message;
      if (cancelAdvBtnEl) cancelAdvBtnEl.hidden = true;
    } else {
      setStatus("Erro ao iniciar", action);
      setFinalStatus(`<strong>ERRO</strong> ❌ Erro de rede ou servidor: ${err.message}`, "error");
      if (cancelJobBtnEl) cancelJobBtnEl.hidden = true;
    }
  }
};

const pollJob = (jobId, action) => {
  let consecutiveErrors = 0;
  // Use a wrapper object to avoid the race condition where the first tick
  // fires before 'interval' is assigned (async callbacks + setInterval).
  const handle = { id: null };
  handle.id = setInterval(async () => {
    try {
      const response = await fetch(`/api/job/${jobId}`);
      if (!response.ok) {
        consecutiveErrors++;
        console.error(`[pollJob] Erro HTTP ${response.status} ao consultar job ${jobId} (tentativa ${consecutiveErrors})`);
        if (consecutiveErrors >= MAX_POLL_RETRIES) {
          if (action === "advanced_analysis") {
            if (advStatusEl) advStatusEl.textContent = "Erro ao consultar";
            if (cancelAdvBtnEl) cancelAdvBtnEl.hidden = true;
          } else {
            setStatus("Erro ao consultar", action);
            setFinalStatus(`<strong>ERRO</strong> ❌ Falha ao consultar job após ${consecutiveErrors} tentativas (HTTP ${response.status})`, "error");
            if (cancelJobBtnEl) cancelJobBtnEl.hidden = true;
          }
          return clearInterval(handle.id);
        }
        return;
      }

      consecutiveErrors = 0;
      const data = await response.json();

      if (action === "advanced_analysis") {
        if (advOutputEl) {
          advOutputEl.style.display = "block";
          advOutputEl.textContent = data.output || "";
          advOutputEl.scrollTop = advOutputEl.scrollHeight;
        }
      } else {
        setOutput(data.output || "");
      }

      if ((action === "pipeline" || action.startsWith("rerun:")) && data.status !== "queued") {
        showPipelineProgress(true);
        updatePipelineProgressFromOutput(data.output || "", data.status);
      } else showPipelineProgress(false);

      // Hide cancel button if job is no longer running
      const isFinished = !isActiveJobStatus(data.status);
      if (isFinished) {
        if (action === "advanced_analysis") {
          if (cancelAdvBtnEl) {
            cancelAdvBtnEl.hidden = true;
            cancelAdvBtnEl.disabled = false;
            cancelAdvBtnEl.textContent = "⏹️ Parar Análise";
          }
          activeAdvJobId = null;
        } else {
          if (cancelJobBtnEl) {
            cancelJobBtnEl.hidden = true;
            cancelJobBtnEl.disabled = false;
            cancelJobBtnEl.textContent = "⏹️ Parar Execução";
          }
          activeJobId = null;
        }
      }

      if (isActiveJobStatus(data.status)) {
        if (action === "advanced_analysis") {
          if (advStatusEl) {
            advStatusEl.textContent = data.status === "cancelling"
              ? "Cancelando..."
              : (data.status === "starting" ? "Iniciando..." : "Executando...");
          }
          return;
        } else {
          const label = data.status === "cancelling"
            ? "Cancelando..."
            : (data.status === "starting" ? "Iniciando..." : "Executando...");
          return setStatus(label, action);
        }
      }

      // Handle cancelled status
      if (data.status === "cancelled") {
        if (action === "advanced_analysis") {
          if (advStatusEl) advStatusEl.textContent = "Cancelado";
        } else {
          setStatus("Cancelado", action);
          setFinalStatus("<strong>CANCELADO</strong> ⏹️ A execução foi interrompida.", "error");
        }
        clearInterval(handle.id);
        fetchSamples();
        fetchHistory();
        return;
      }

      if (data.status === "done") {
        if (action === "advanced_analysis") {
          if (advStatusEl) advStatusEl.textContent = "Concluído";
          const runDir = data.run?.run_dir || "";
          if (advReportContentEl && advReportViewerEl && runDir) {
            try {
              const res = await fetch(`/api/history/file?run=${encodeURIComponent(runDir)}&type=report`);
              if (res.ok) {
                advReportContentEl.textContent = await res.text();
                advReportViewerEl.hidden = false;
              }
            } catch (err) {
              console.error("Falha ao carregar resumo avançado", err);
            }
          }
        } else if (action === "assembly_only") {
          const runDir = data.run?.run_dir || "";
          let summaryText = "";
          if (runDir) {
            try {
              const res = await fetch(`/api/history/file?run=${encodeURIComponent(runDir)}&type=report`);
              if (res.ok) summaryText = await res.text();
            } catch (_) {}
          }
          if (assemblyOnlyStatusEl) {
            const contigsPath = `data/assemblies/${escapeHTML(data.run?.sample || "?")}_assembly/contigs.fa`;
            assemblyOnlyStatusEl.className = "final-status ok";
            assemblyOnlyStatusEl.innerHTML = `<strong>SUCESSO</strong> ✅ Montagem concluída.<br><code>${contigsPath}</code>${summaryText ? `<br><details><summary style="cursor:pointer;margin-top:0.5rem;">Ver resumo</summary><pre style="margin-top:0.5rem;font-size:0.82rem;">${escapeHTML(summaryText)}</pre></details>` : ""}`;
          }
          setStatus("Concluído", action);
        } else {
          setStatus("Concluído", action);
          const runDir = data.run?.run_dir || "";
          const reportLink = runDir ? `<a href="/api/history/file?run=${encodeURIComponent(runDir)}&type=report" target="_blank">Abrir report</a>` : "";
          const fastaLink = (runDir && data.run?.paths?.run_hit_contigs_fasta) ? ` | <a href="/api/history/file?run=${encodeURIComponent(runDir)}&type=hit_contigs_fasta" target="_blank">Baixar FASTA de Hits</a>` : "";
          setFinalStatus(`<strong>SUCESSO</strong> ✅ ${reportLink}${fastaLink}`, "ok");
          await loadReportInline(runDir);
        }
      } else {
        console.error(`[pollJob] Job ${jobId} (ação '${action}') terminou com erro. Tail:`, data.tail);
        if (action === "advanced_analysis") {
          if (advStatusEl) advStatusEl.textContent = "Falhou";
        } else {
          setStatus("Falhou", action);
          const runDir = data.run?.run_dir || "";
          const logLink = runDir
            ? `<br><a href="/api/history/file?run=${encodeURIComponent(runDir)}&type=log" target="_blank">Inspecionar Log Completo</a>`
            : "";
          showFriendlyError(data.tail, logLink);
        }
      }

      clearInterval(handle.id);
      fetchSamples();
      fetchHistory();
    } catch (err) {
      consecutiveErrors++;
      console.error(`[pollJob] Exceção ao consultar job ${jobId} (tentativa ${consecutiveErrors}):`, err);
      if (consecutiveErrors >= MAX_POLL_RETRIES) {
        if (action === "advanced_analysis") {
          if (advStatusEl) advStatusEl.textContent = "Erro ao consultar";
          if (cancelAdvBtnEl) cancelAdvBtnEl.hidden = true;
        } else {
          setStatus("Erro ao consultar", action);
          setFinalStatus(`<strong>ERRO</strong> ❌ Erro de rede ao acompanhar execução: ${err.message}`, "error");
          if (cancelJobBtnEl) cancelJobBtnEl.hidden = true;
        }
        clearInterval(handle.id);
      }
    }
  }, JOB_POLL_INTERVAL_MS);
};

const uploadImport = async (formData) => {
  setStatus("Executando...", "upload_import");
  setOutput("");
  setFinalStatus("");

  const response = await fetch("/api/import-upload", { method: "POST", body: formData });
  if (!response.ok) {
    const msg = await response.text();
    setFinalStatus(`<strong>FALHA</strong> ❌<pre>${msg}</pre>`, "error");
    setStatus("Falhou", "upload_import");
    return;
  }
  const data = await response.json();
  setStatus("Concluído", "upload_import");
  setFinalStatus(`<strong>SUCESSO</strong> ✅ ${data.message}`, "ok");
  fetchSamples();
};

const bindButtons = () => {
  document.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });

  document.getElementById("db-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const target = formData.get("target")  || "";
    const query  = (formData.get("query")  || "").trim();
    const taxid  = formData.get("taxid")   || "";

    // Validação: pelo menos um dos campos deve estar preenchido
    if (!target && !query) {
      if (dbStatusEl) {
        dbStatusEl.textContent = "Erro: escolha um alvo da lista ou preencha a query customizada.";
        dbStatusEl.className = "db-status error";
      }
      return;
    }

    // Lembra a configuração do DB selecionado
    currentDB = {
      target: target || null,
      query:  query  || null,
      taxid:  taxid  || null,
      ncbi_db: null,
    };

    runAction("build_db", { target, query, taxid });
    updateDBStatus();
  });

  document.getElementById("import-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    runAction("import_sample", {
      sample: formData.get("sample"),
      r1: formData.get("r1"),
      r2: formData.get("r2"),
      copy: formData.get("copy") === "on",
    });
  });

  document.getElementById("upload-form").addEventListener("submit", (event) => {
    event.preventDefault();
    uploadImport(new FormData(event.target));
  });

  document.getElementById("pipeline-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    if (!(await validateCustomHostIndex())) return;
    const params = {
      sample: formData.get("sample_select") || formData.get("sample"),
      analysis_profile: formData.get("analysis_profile") || "canonical-e1",
      assembler: formData.get("assembler") || "velvet",
      kmer: formData.get("kmer"),
      skip_qc: formData.get("skip_qc") === "on",
      host_filter_mode: formData.get("host_filter_mode") || "none",
    };

    if (params.host_filter_mode === "custom") {
      params.host_name = formData.get("host_name") || "hospedeiro customizado";
      params.host_index_prefix = formData.get("host_index_prefix") || "";
    }

    // Inclui configuração do DB se alvo OU query estiver definido
    if (currentDB.target || currentDB.query) {
      params.db = currentDB.target || "custom";
      if (currentDB.query) {
        params.db_query = currentDB.query;
      }
      if (currentDB.ncbi_db) {
        params.ncbi_db = currentDB.ncbi_db;
      }
    }

    runAction("pipeline", params);
  });

  const advForm = document.getElementById("advanced-form");
  if (advForm) {
    advForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(event.target);
      runAction("advanced_analysis", {
        sample: formData.get("sample"),
        min_pident: formData.get("min_pident"),
        min_aln_len: formData.get("min_aln_len"),
        method: formData.get("method"),
        kmer: formData.get("kmer"),
      });
    });
  }

  const assemblyOnlyForm = document.getElementById("assembly-only-form");
  if (assemblyOnlyForm) {
    assemblyOnlyForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(event.target);
      const sample = formData.get("sample") || "";
      if (!sample) {
        if (assemblyOnlyStatusEl) {
          assemblyOnlyStatusEl.className = "final-status error";
          assemblyOnlyStatusEl.innerHTML = "<strong>ERRO</strong> ❌ Selecione uma amostra.";
        }
        return;
      }
      if (assemblyOnlyStatusEl) {
        assemblyOnlyStatusEl.className = "final-status";
        assemblyOnlyStatusEl.innerHTML = "";
      }
      runAction("assembly_only", {
        sample,
        assembler: formData.get("assembler") || "velvet",
        kmer: formData.get("kmer") || "31",
        spades_params: formData.get("spades_params") || "",
      });
    });
  }

  const dashboardTabs = Array.from(document.querySelectorAll(".tab"));
  dashboardTabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateDashboardTab(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      let nextIndex = null;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % dashboardTabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + dashboardTabs.length) % dashboardTabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = dashboardTabs.length - 1;
      if (nextIndex === null) return;
      event.preventDefault();
      activateDashboardTab(dashboardTabs[nextIndex].dataset.tab, { focus: true });
    });
  });

  // Bind config form
  if (configFormEl) {
    configFormEl.addEventListener("submit", saveConfigEnv);
  }

  if (hostFilterModeEl) {
    hostFilterModeEl.addEventListener("change", updateHostFilterFields);
    updateHostFilterFields();
  }
  if (hostIndexPrefixEl) {
    hostIndexPrefixEl.addEventListener("blur", validateCustomHostIndex);
  }

  // Bind rebuild environment button
  if (rebuildEnvBtnEl) {
    rebuildEnvBtnEl.addEventListener("click", rebuildEnvironment);
  }

  // Bind TSV modal close button
  if (tsvModalCloseEl) {
    tsvModalCloseEl.addEventListener("click", closeTSVModal);
  }
  if (tsvModalOverlayEl) {
    tsvModalOverlayEl.addEventListener("click", (e) => {
      if (e.target === tsvModalOverlayEl) closeTSVModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && tsvModalOverlayEl && !tsvModalOverlayEl.hidden) closeTSVModal();
  });

  // Bind cleanup button
  if (cleanupBtnEl) {
    cleanupBtnEl.addEventListener("click", cleanupTempFiles);
  }

  // Bind cancel (stop) buttons
  const cancelJob = async (jobIdRef, isAdv) => {
    const jid = isAdv ? activeAdvJobId : activeJobId;
    if (!jid) return;
    const confirmed = confirm(isAdv
      ? "Deseja interromper a análise avançada em andamento?"
      : "Deseja parar a execução do pipeline/banco em andamento?");
    if (!confirmed) return;
    try {
      const res = await fetch(`/api/job/${jid}/cancel`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: "{}" });
      const data = await res.json();
      if (data.ok) {
        if (isAdv) {
          if (advStatusEl) advStatusEl.textContent = "Cancelando...";
          if (cancelAdvBtnEl) { cancelAdvBtnEl.disabled = true; cancelAdvBtnEl.textContent = "⏳ Cancelando..."; }
        } else {
          setStatus("Cancelando...", "");
          if (cancelJobBtnEl) { cancelJobBtnEl.disabled = true; cancelJobBtnEl.textContent = "⏳ Cancelando..."; }
        }
      } else {
        alert(data.message || "Não foi possível cancelar o job.");
      }
    } catch (err) {
      alert(`Erro ao cancelar: ${err.message}`);
    }
  };

  if (cancelJobBtnEl) {
    cancelJobBtnEl.addEventListener("click", () => cancelJob(activeJobId, false));
  }
  if (cancelAdvBtnEl) {
    cancelAdvBtnEl.addEventListener("click", () => cancelJob(activeAdvJobId, true));
  }
};

let activeEvidenceRunId = null;
let activeEvidenceJobId = null;
let evidenceBatchRows = [];
let evidencePollTimer = null;

const evidenceApi = async (url, options = {}) => {
  const response = await fetch(url, { ...options, cache: "no-store" });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("json") ? await response.json() : { error: await response.text() };
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
};

const setEvidenceText = (id, text, tone = "") => {
  const node = getEl(id);
  if (!node) return;
  node.textContent = text || "";
  node.className = `status-line ${tone}`.trim();
};

const renderEvidenceStages = (state) => {
  const list = getEl("evidence-stage-list");
  if (!list) return;
  list.replaceChildren();
  const labels = { pending: "Não iniciada", starting: "Iniciando", running: "Em execução", cancelling: "Cancelando", done: "Concluída", warning: "Concluída com aviso", blocked: "Bloqueada", failed: "Falhou", cancelled: "Cancelada" };
  (state.stages || []).forEach((stage) => {
    const item = document.createElement("li");
    item.className = `evidence-stage evidence-stage--${stage.status}`;
    const title = document.createElement("strong");
    title.textContent = stage.label;
    const status = document.createElement("span");
    status.textContent = labels[stage.status] || stage.status;
    item.append(title, status);
    if (stage.message) {
      const message = document.createElement("small");
      message.textContent = stage.message;
      item.append(message);
    }
    list.append(item);
  });
};

const renderEvidenceResult = (result) => {
  const container = getEl("evidence-results");
  const empty = getEl("evidence-result-empty");
  if (result.valid_alpha2 === false) {
    if (container) container.hidden = true;
    if (empty) {
      empty.hidden = false;
      const compatibility = result.compatibility || {};
      const state = result.state || {};
      empty.textContent = [
        result.official_v1,
        result.experimental_warning,
        !result.complete ? `Estado operacional: ${state.status || "incompleto"}.` : "",
        !result.complete ? `Outcome cient\u00edfico: ${state.analysis_outcome || "NOT_EVALUABLE"}.` : "",
        !result.complete && state.failure_type ? `Tipo de falha: ${state.failure_type}.` : "",
        !result.complete && state.failed_stage ? `Etapa: ${state.failed_stage}.` : "",
        !result.complete ? state.failure_message || "" : "",
        `${compatibility.status || "NOT_EVALUABLE"}: ${compatibility.message || "Reexecute a an\u00e1lise para gerar artefatos Alpha.2 completos."}`,
      ].filter(Boolean).join("\n");
    }
    return;
  }
  if (!result.complete || !result.evidence_v2) {
    if (container) container.hidden = true;
    if (empty) {
      const state = result.state || {};
      empty.hidden = false;
      empty.textContent = [
        `Estado operacional: ${state.status || "incompleto"}.`,
        `Outcome científico: ${state.analysis_outcome || "NOT_EVALUABLE"}.`,
        state.failure_type ? `Tipo de falha: ${state.failure_type}.` : "",
        state.failed_stage ? `Etapa: ${state.failed_stage}.` : "",
        state.failure_message || "",
        "A execução não possui SUCCESS.json e nenhum artefato é apresentado como resultado concluído.",
        result.experimental_warning || "",
      ].filter(Boolean).join("\n");
    }
    return;
  }
  if (empty) empty.hidden = true;
  if (container) container.hidden = false;
  getEl("evidence-v1-result").textContent = result.official_v1 || "Relatório oficial 1.1 não disponível para este run; nenhum resultado foi substituído.";
  const dimensions = getEl("evidence-dimensions");
  dimensions.replaceChildren();
  const value = result.evidence_v2;
  if (Array.isArray(value.samples)) {
    value.samples.forEach((sample) => {
      const card = document.createElement("article");
      card.className = "evidence-dimension-card";
      const title = document.createElement("strong"); title.textContent = sample.sample_id;
      const body = document.createElement("p");
      body.textContent = [
        `execução=${sample.execution_status}`,
        `outcome=${sample.analysis_outcome || "NOT_EVALUABLE"}`,
        `evidência=${sample.evidence_level}`,
        `conclusão=${sample.reported_conclusion}`,
        `especificidade=${sample.specificity_status || "NOT_EVALUATED"}`,
        `cobertura=${sample.coverage_status || "NOT_EVALUATED"}`,
        `controle=${sample.control_status || "NOT_EVALUATED"}`,
      ].join("\n");
      card.append(title, body); dimensions.append(card);
    });
  } else {
    [
      "execution_status", "analysis_outcome", "evidence_level",
      "reported_conclusion", "shadow_mode", "specificity_status",
      "coverage_status", "control_status",
    ].forEach((key) => {
      const card = document.createElement("article"); card.className = "evidence-dimension-card";
      const title = document.createElement("strong"); title.textContent = key;
      const state = document.createElement("p");
      const canonicalValue = key === "shadow_mode" ? String(value[key]) : value[key];
      state.textContent = canonicalValue || "NOT_EVALUATED";
      const explanation = document.createElement("small"); explanation.textContent = (result.explanations || {})[value[key]] || "Estado experimental rastreável no JSON.";
      card.append(title, state, explanation); dimensions.append(card);
    });
  }
  const summary = getEl("evidence-summary");
  if (summary) {
    const metrics = value.metrics || {};
    const lines = [
      `Conclusão reportada pelo artefato canônico: ${value.reported_conclusion}.`,
      "O dashboard apenas apresenta os campos canônicos e não recalcula o nível de evidência.",
    ];
    if (Array.isArray(value.samples)) {
      value.samples.forEach((sample) => {
        const control = sample.control_metrics || {};
        lines.push(`${sample.sample_id}: evidência=${sample.evidence_level}; controle=${sample.control_status}; RPM pós-QC=${control.sample_rpm || "NA"}; RPM não hospedeiro=${control.rpm_nonhost || "NA"}`);
      });
    } else {
      lines.push(`Loci qualificadores: ${metrics.qualifying_loci ?? "NA"}`);
      lines.push(`Bases não redundantes: ${metrics.total_nonredundant_reference_bp ?? "NA"}`);
      lines.push(`Templates únicos: ${metrics.unique_templates ?? "NA"}`);
      lines.push(`Breadth 1×/3×: ${metrics.breadth_1x ?? "NA"} / ${metrics.breadth_3x ?? "NA"}`);
      lines.push(`Profundidade mediana nas posições cobertas: ${metrics.median_depth_covered ?? "NA"}`);
      lines.push(`Controle: ${value.control_status || "UNCONTROLLED"}`);
      lines.push(`Outcome: ${value.analysis_outcome || "NOT_EVALUABLE"}`);
      const blocked = (value.promotion_gates || []).filter((gate) => gate.status === "BLOCKED");
      if (blocked.length) lines.push(`Gates bloqueados: ${blocked.map((gate) => gate.gate_id).join(", ")}`);
      (value.caveats || []).forEach((caveat) => lines.push(`Ressalva: ${caveat}`));
    }
    summary.textContent = lines.join("\n");
  }
  const candidates = getEl("evidence-candidates");
  if (candidates) {
    candidates.replaceChildren();
    const canonicalCandidates = Array.isArray(value.candidates) ? value.candidates : [];
    if (!canonicalCandidates.length) {
      const message = document.createElement("p");
      message.textContent = Array.isArray(value.samples)
        ? "O resumo do lote não agrega candidatos entre amostras; consulte os artefatos canônicos de cada amostra."
        : "Nenhum candidato computacional foi retido; isso não demonstra ausência viral.";
      candidates.append(message);
    } else {
      canonicalCandidates.forEach((candidate) => {
        const card = document.createElement("article");
        card.className = `evidence-candidate-card${candidate.promotion_status === "BLOCKED" ? " evidence-candidate-card--blocked" : ""}`;
        const title = document.createElement("strong");
        title.textContent = `${candidate.reference_id} · ${candidate.candidate_class}`;
        const body = document.createElement("p");
        body.textContent = [
          `locus=${candidate.locus_id}; orientação=${candidate.orientation}`,
          `promoção=${candidate.promotion_status}`,
          `bloqueios=${(candidate.blocking_reasons || []).join(", ") || "nenhum"}`,
          `queries=${(candidate.query_ids || []).join(", ") || "nenhuma"}`,
        ].join("\n");
        card.append(title, body);
        candidates.append(card);
      });
    }
  }
  const artifacts = getEl("evidence-artifacts"); artifacts.replaceChildren();
  const artifactLabels = {
    sample_evidence: "Baixar evidência canônica da amostra (JSON)",
    batch_evidence: "Baixar evidência canônica do lote (JSON)",
    report: "Baixar relatório experimental",
    batch_report: "Baixar relatório experimental do lote",
    success: "Baixar marcador de commit",
    state: "Baixar estado final",
    provenance: "Baixar proveniência",
  };
  (result.artifacts || []).forEach((type) => {
    const link = document.createElement("a"); link.className = "btn btn--secondary"; link.textContent = artifactLabels[type] || `Baixar ${type}`;
    link.href = `/api/evidence/artifact?run=${encodeURIComponent(activeEvidenceRunId)}&type=${encodeURIComponent(type)}`;
    link.download = "";
    artifacts.append(link);
  });
};

const pollEvidenceRun = async () => {
  if (!activeEvidenceRunId) return;
  try {
    const state = await evidenceApi(`/api/evidence/run?id=${encodeURIComponent(activeEvidenceRunId)}`);
    renderEvidenceStages(state);
    const failureState = ["blocked", "failed", "cancelled", "alpha2_invalid", "legacy_incompatible"].includes(state.status);
    setEvidenceText("evidence-run-status", `${state.status} · run_id ${state.run_id}`, failureState ? "error" : "");
    const terminal = ["done", "done_with_warning", "blocked", "failed", "cancelled"].includes(state.status);
    if (terminal) {
      clearTimeout(evidencePollTimer);
      getEl("evidence-cancel").disabled = true;
      try {
        const result = await evidenceApi(`/api/evidence/result?run=${encodeURIComponent(activeEvidenceRunId)}`);
        renderEvidenceResult(result);
      } catch (error) {
        setEvidenceText("evidence-run-status", `Execução terminal, mas o resultado não pôde ser carregado: ${error.message}`, "error");
      }
      return;
    }
  } catch (error) {
    setEvidenceText("evidence-run-status", error.message, "error");
  }
  evidencePollTimer = setTimeout(pollEvidenceRun, 1200);
};

const startEvidenceRun = async (mode, params) => {
  const result = await evidenceApi("/api/evidence/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode, params }) });
  activeEvidenceRunId = result.job_id;
  activeEvidenceJobId = result.job_id;
  getEl("evidence-cancel").disabled = false;
  setEvidenceText("evidence-run-status", `Execução enfileirada · ${result.job_id}`);
  clearTimeout(evidencePollTimer);
  pollEvidenceRun();
};

const uploadEvidenceFiles = async (sample, r1, r2) => {
  if (!r1 || !r2 || !r1.name || !r2.name) return { sample_id: sample };
  if (!sample) throw new Error("Informe o identificador da amostra antes do upload.");
  const form = new FormData();
  form.append("sample", sample);
  form.append("r1file", r1, r1.name);
  form.append("r2file", r2, r2.name);
  return evidenceApi("/api/import-upload", { method: "POST", body: form });
};

const renderEvidenceBatchRows = () => {
  const body = getEl("evidence-batch-rows"); if (!body) return;
  body.replaceChildren();
  evidenceBatchRows.forEach((row, index) => {
    const tr = document.createElement("tr");
    [row.sample_id, row.role, row.library_mode, `${row.r1} / ${row.r2}`].forEach((value) => { const td = document.createElement("td"); td.textContent = value; tr.append(td); });
    const actions = document.createElement("td"); const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn--secondary"; remove.textContent = "Remover";
    remove.addEventListener("click", () => { evidenceBatchRows.splice(index, 1); renderEvidenceBatchRows(); }); actions.append(remove); tr.append(actions); body.append(tr);
  });
};

const loadEvidenceManifests = async () => {
  const data = await evidenceApi("/api/evidence/manifests"); const select = getEl("evidence-manifest-list"); if (!select) return;
  select.replaceChildren(new Option("Manifestos salvos", ""));
  (data.manifests || []).forEach((item) => select.add(new Option(`${item.manifest_id} · ${item.batch_id}`, item.manifest_id)));
};

const loadEvidenceInterface = async () => {
  try {
    const [samplesData, targetsData] = await Promise.all([evidenceApi("/api/samples"), evidenceApi("/api/targets")]);
    const sample = getEl("evidence-sample"); sample.replaceChildren(new Option("Selecione", "")); (samplesData.samples || []).forEach((item) => sample.add(new Option(item, item)));
    const targetOptions = (targetsData.targets || []).map((item) => ({
      label: item.display_name || item.label || item.name || item.key,
      value: item.key || item.id || item.name,
    }));
    ["evidence-target", "evidence-batch-target"].forEach((id) => {
      const target = getEl(id);
      target.replaceChildren(new Option("Selecione explicitamente um banco viral", ""));
      targetOptions.forEach((item) => target.add(new Option(item.label, item.value)));
    });
    await loadEvidenceManifests();
    try {
      const dependencies = await evidenceApi("/api/evidence/dependencies");
      setEvidenceText("evidence-dependencies-status", "Ambiente V2 disponível · Python efetivo e ferramentas registrados.");
    } catch (error) { setEvidenceText("evidence-dependencies-status", `Evidence V2 bloqueada: ${error.message}`, "error"); }
    try {
      const config = await evidenceApi("/api/evidence/config"); getEl("evidence-config-editor").value = JSON.stringify(config.config, null, 2);
      setEvidenceText("evidence-config-status", "Configuração 2.0-alpha carregada · em calibração");
    } catch (error) { setEvidenceText("evidence-config-status", error.message, "error"); }
  } catch (error) { setEvidenceText("evidence-form-status", error.message, "error"); }
};

const updateEvidenceHostFilterFields = () => {
  const custom = evidenceHostFilterModeEl?.value === "custom";
  document.querySelectorAll("[data-evidence-host-custom]").forEach((item) => {
    item.hidden = !custom;
  });
  const batchCustom = evidenceBatchHostFilterModeEl?.value === "custom";
  document.querySelectorAll("[data-evidence-batch-host-custom]").forEach((item) => {
    item.hidden = !batchCustom;
  });
};

const bindEvidenceInterface = () => {
  document.querySelectorAll(".evidence-mode").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".evidence-mode").forEach((item) => item.classList.remove("active")); button.classList.add("active");
    const advanced = button.dataset.mode === "advanced"; document.querySelectorAll(".evidence-advanced-only").forEach((item) => { item.hidden = !advanced; });
  }));
  evidenceHostFilterModeEl?.addEventListener("change", updateEvidenceHostFilterFields);
  evidenceBatchHostFilterModeEl?.addEventListener("change", updateEvidenceHostFilterFields);
  updateEvidenceHostFilterFields();
  getEl("evidence-role")?.addEventListener("change", (event) => { const input = getEl("evidence-expected-target"); input.disabled = event.target.value !== "positive"; if (input.disabled) input.value = ""; });
  getEl("evidence-individual-form")?.addEventListener("submit", async (event) => {
    event.preventDefault(); if (event.target.querySelector('input[type="file"]')?.files.length) return;
    const data = Object.fromEntries(new FormData(event.target).entries());
    try { await startEvidenceRun("individual", data); setEvidenceText("evidence-form-status", "Execução experimental iniciada."); } catch (error) { setEvidenceText("evidence-form-status", error.message, "error"); }
  });
  getEl("evidence-batch-row-form")?.addEventListener("submit", (event) => { event.preventDefault(); if (event.target.querySelector('input[type="file"]')?.files.length) return; evidenceBatchRows.push(Object.fromEntries(new FormData(event.target).entries())); renderEvidenceBatchRows(); event.target.reset(); });
  getEl("evidence-individual-form")?.addEventListener("submit", async (event) => {
    if (!event.target.querySelector('input[type="file"]')?.files.length) return;
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    try {
      const uploaded = await uploadEvidenceFiles(String(data.upload_sample || data.sample || "").trim(), data.r1file, data.r2file);
      data.sample = uploaded.sample_id || data.sample;
      delete data.upload_sample; delete data.r1file; delete data.r2file;
      await startEvidenceRun("individual", data);
      setEvidenceText("evidence-form-status", "Execução experimental iniciada.");
    } catch (error) { setEvidenceText("evidence-form-status", error.message, "error"); }
  });
  getEl("evidence-batch-row-form")?.addEventListener("submit", async (event) => {
    if (!event.target.querySelector('input[type="file"]')?.files.length) return;
    event.preventDefault();
    const formData = new FormData(event.target);
    const row = Object.fromEntries(formData.entries());
    try {
      const uploaded = await uploadEvidenceFiles(String(row.sample_id || "").trim(), row.r1file, row.r2file);
      row.r1 = uploaded.r1; row.r2 = uploaded.r2;
      delete row.r1file; delete row.r2file;
      evidenceBatchRows.push(row);
      renderEvidenceBatchRows();
      event.target.reset();
      setEvidenceText("evidence-manifest-status", "Amostra importada e adicionada ao lote.");
    } catch (error) { setEvidenceText("evidence-manifest-status", error.message, "error"); }
  });
  getEl("evidence-manifest-validate")?.addEventListener("click", async () => { try { const result = await evidenceApi("/api/evidence/manifests/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows: evidenceBatchRows }) }); setEvidenceText("evidence-manifest-status", result.warnings.join(" ") || "Manifesto válido."); } catch (error) { setEvidenceText("evidence-manifest-status", error.message, "error"); } });
  getEl("evidence-manifest-save")?.addEventListener("click", async () => { try { const result = await evidenceApi("/api/evidence/manifests/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows: evidenceBatchRows, manifest_id: getEl("evidence-manifest-id").value || null }) }); setEvidenceText("evidence-manifest-status", `Manifesto salvo: ${result.manifest_id}`); await loadEvidenceManifests(); } catch (error) { setEvidenceText("evidence-manifest-status", error.message, "error"); } });
  getEl("evidence-manifest-open")?.addEventListener("click", async () => { try { const id = getEl("evidence-manifest-list").value; const result = await evidenceApi(`/api/evidence/manifest?id=${encodeURIComponent(id)}`); evidenceBatchRows = result.rows; renderEvidenceBatchRows(); getEl("evidence-manifest-id").value = result.manifest_id; } catch (error) { setEvidenceText("evidence-manifest-status", error.message, "error"); } });
  getEl("evidence-batch-run")?.addEventListener("click", async () => {
    try {
      const manifestId = getEl("evidence-manifest-list").value || getEl("evidence-manifest-id").value;
      const target = getEl("evidence-batch-target").value;
      if (!manifestId) throw new Error("Salve ou selecione um manifesto válido.");
      if (!target) throw new Error("Selecione explicitamente um banco viral para o lote.");
      await startEvidenceRun("batch", {
        manifest_id: manifestId,
        target,
        host_filter_mode: evidenceBatchHostFilterModeEl?.value || "none",
        host_name: getEl("evidence-batch-host-name").value,
        host_index_prefix: getEl("evidence-batch-host-index-prefix").value,
      });
    } catch (error) { setEvidenceText("evidence-manifest-status", error.message, "error"); }
  });
  getEl("evidence-config-validate")?.addEventListener("click", async () => { try { await evidenceApi("/api/evidence/config/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: getEl("evidence-config-editor").value }) }); setEvidenceText("evidence-config-status", "Configuração válida · parâmetros em calibração"); } catch (error) { setEvidenceText("evidence-config-status", error.message, "error"); } });
  getEl("evidence-cancel")?.addEventListener("click", async () => {
    if (!activeEvidenceJobId) return;
    try {
      await evidenceApi(`/api/job/${activeEvidenceJobId}/cancel`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      setEvidenceText("evidence-run-status", "Cancelamento solicitado.");
    } catch (error) {
      setEvidenceText("evidence-run-status", `Falha ao solicitar cancelamento: ${error.message}`, "error");
    }
  });
};

window.addEventListener("load", () => {
  bindButtons();
  bindEvidenceInterface();
  fetchTargets();
  fetchSamples();
  fetchHistory();
  showPipelineProgress(false);
  setReportContent("");
  updateDBStatus();
  loadEvidenceInterface();
  initializeGuidedDashboard();
});
