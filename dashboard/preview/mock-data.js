/* =====================================================================
   Gene-In · Preview de UX — DADOS FICTÍCIOS
   Este arquivo contém apenas dados de demonstração e catálogos de texto.
   Nenhum dado real. Não utiliza a amostra 2323.
   Separado da lógica visual (preview.js) de propósito.
   ===================================================================== */
(function (global) {
  "use strict";

  /* ---- Catálogo central de rótulos e estados (linguagem conservadora) ---- */
  const LABELS = {
    // Estados de execução (operacional) — distintos entre si, nunca sinônimos
    execState: {
      idle:      { text: "Aguardando",            badge: "badge--none" },
      running:   { text: "Em execução",           badge: "badge--running" },
      done:      { text: "Execução concluída",     badge: "badge--ok" },
      none:      { text: "Nenhuma evidência recuperada", badge: "badge--none" },
      na:        { text: "Não avaliável",          badge: "badge--na" },
      fail:      { text: "Falha operacional",      badge: "badge--fail" },
      cancelled: { text: "Execução cancelada",     badge: "badge--cancel" },
      partial:   { text: "Sucesso parcial (lote)", badge: "badge--partial" },
    },
    // Interpretação científica associada a cada desfecho
    interpretation: {
      done:  "Execução concluída. Foram recuperados fragmentos virais candidatos com evidência molecular compatível, sob os critérios adotados. Interpretação conservadora: requer análise complementar e controles independentes; não constitui diagnóstico nem confirmação de presença viral.",
      none:  "Execução concluída sem fragmentos candidatos que atendam aos critérios adotados. Nenhuma evidência recuperada não equivale a ausência viral: pode refletir baixa cobertura, banco de referência limitado ou linhagens divergentes.",
      na:    "Resultado não avaliável. Os pré-requisitos mínimos de qualidade/cobertura não foram atendidos para permitir uma classificação operacional confiável. Isto é diferente de falha e de ausência de evidência.",
      fail:  "Falha operacional durante a execução. O pipeline foi interrompido por um erro técnico antes de produzir um resultado avaliável. Nenhuma conclusão científica pode ser derivada desta execução.",
      cancelled: "Execução cancelada pelo operador. Não há resultado científico a interpretar.",
    },
    // Rótulos preferenciais de UI
    ui: {
      candidateFragment: "fragmento viral candidato",
      complementary: "Análise filogenética complementar",
      operationalClass: "classificação operacional",
    },
  };

  /* ---- Alvos / bancos virais pré-configurados (fictícios/ilustrativos) ---- */
  const TARGETS = [
    { key: "teschovirus_a",         display_name: "Teschovirus A (PTV)" },
    { key: "sapelovirus_a",         display_name: "Sapelovirus A" },
    { key: "enterovirus_g",         display_name: "Enterovirus G" },
    { key: "astrovirus_suino",      display_name: "Astrovirus suíno" },
    { key: "picornaviridae_refseq", display_name: "Picornaviridae (RefSeq)" },
  ];

  const ASSEMBLERS = [
    { key: "velvet",     name: "Velvet",     simpleHint: "Rápido, bom padrão inicial" },
    { key: "spades",     name: "SPAdes",     simpleHint: "Mais sensível, mais lento" },
    { key: "metaspades", name: "metaSPAdes", simpleHint: "Para amostras metagenômicas" },
  ];

  /* ---- Amostras fictícias já importadas ---- */
  const SAMPLES = ["suino_lab_A", "suino_lab_B", "swab_fazenda_07", "demo_sintetica"];

  /* ---- Fragmentos candidatos priorizados (fictícios) ---- */
  const CANDIDATE_FRAGMENTS = [
    { id: "contig_0007", ref: "Teschovirus A (ref. fictícia FIC-001)", len: 812, cov: "18.4x", pident: 96.2, adj: 0.91, evidence: "E1" },
    { id: "contig_0021", ref: "Teschovirus A (ref. fictícia FIC-002)", len: 544, cov: "9.7x",  pident: 92.8, adj: 0.84, evidence: "E1" },
    { id: "contig_0043", ref: "Sapelovirus A (ref. fictícia FIC-011)", len: 203, cov: "4.1x",  pident: 88.0, adj: 0.62, evidence: "revisão" },
  ];

  const EXPLORATORY_FRAGMENTS = [
    { id: "frag_x12", len: 34, note: "20–49 pb — evidência exploratória; nunca isolada como identificação" },
    { id: "frag_x27", len: 41, note: "20–49 pb — evidência exploratória; nunca isolada como identificação" },
  ];

  /* ---- Etapas do pipeline (acompanhamento) ---- */
  const PIPELINE_STAGES = [
    { key: "qc",       label: "Controle de qualidade (QC)" },
    { key: "host",     label: "Filtro do hospedeiro" },
    { key: "assembly", label: "Montagem de contigs" },
    { key: "blast",    label: "Busca por similaridade (BLAST)" },
    { key: "report",   label: "Consolidação do resultado" },
  ];

  const LOG_SAMPLE = [
    "[INFO] [QC] [demo] — leituras avaliadas: 1.204.882 — aprovado",
    "[INFO] [HOSPEDEIRO] [demo] — leituras do hospedeiro removidas: 71,3%",
    "[INFO] [MONTAGEM] [demo] — contigs gerados: 132 (N50 fictício 684 pb)",
    "[INFO] [BLAST] [demo] — hits candidatos após filtros: 3",
  ].join("\n");

  /* ---- Histórico fictício ---- */
  const HISTORY = [
    { id: "run-1041", sample: "suino_lab_A",   date: "2026-07-16 14:22", db: "Teschovirus A (PTV)", state: "done",      mode: "Simplificado", summary: "3 fragmentos candidatos recuperados; requer análise complementar." },
    { id: "run-1039", sample: "suino_lab_B",   date: "2026-07-16 10:05", db: "Enterovirus G",       state: "none",      mode: "Avançado",     summary: "Nenhuma evidência recuperada nos critérios adotados." },
    { id: "run-1036", sample: "swab_fazenda_07",date: "2026-07-15 18:40", db: "Sapelovirus A",       state: "na",        mode: "Simplificado", summary: "Cobertura insuficiente; resultado não avaliável." },
    { id: "run-1030", sample: "lote_julho",     date: "2026-07-15 09:12", db: "Picornaviridae (RefSeq)", state: "partial", mode: "Lote",     summary: "Lote com sucesso parcial: 4 de 6 amostras avaliáveis." },
    { id: "run-1024", sample: "suino_lab_A",   date: "2026-07-14 16:33", db: "Teschovirus A (PTV)", state: "fail",      mode: "Avançado",     summary: "Falha operacional na montagem; sem resultado avaliável." },
  ];

  /* =====================================================================
     11 CENÁRIOS OBRIGATÓRIOS
     Cada um define a barra de contexto, a tela sugerida e o conteúdo.
     ===================================================================== */
  const SCENARIOS = {
    "1_ambiente_nao_verificado": {
      title: "1 · Ambiente ainda não verificado",
      screen: "home",
      context: { env: "unknown", db: null, sample: null, job: "idle", evidence: false },
      wizard: { current: 0, done: [] },
      nextAction: { text: "Comece verificando o ambiente de execução.", tone: "info", go: "wizard:0" },
    },
    "2_banco_ausente": {
      title: "2 · Banco viral ausente",
      screen: "wizard",
      context: { env: "ok", db: null, sample: null, job: "idle", evidence: false },
      wizard: { current: 1, done: [0] },
      nextAction: { text: "Prepare ou selecione um banco viral para continuar.", tone: "info", go: "wizard:1" },
    },
    "3_amostra_importada": {
      title: "3 · Amostra importada",
      screen: "wizard",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "idle", evidence: false },
      wizard: { current: 3, done: [0, 1, 2] },
      nextAction: { text: "Amostra importada. Configure a análise ou vá direto à revisão.", tone: "info", go: "wizard:3" },
    },
    "4_pronto_para_revisao": {
      title: "4 · Configuração pronta para revisão",
      screen: "wizard",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "idle", evidence: false },
      wizard: { current: 4, done: [0, 1, 2, 3] },
      nextAction: { text: "Revise a configuração antes de executar.", tone: "info", go: "wizard:4" },
    },
    "5_execucao_em_andamento": {
      title: "5 · Execução em andamento",
      screen: "execution",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "running", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4] },
      exec: { stages: { qc: "done", host: "done", assembly: "running", blast: "pending", report: "pending" }, elapsed: "00:03:41" },
      nextAction: { text: "Existe uma execução em andamento. Acompanhe o progresso.", tone: "info", go: "execution" },
    },
    "6_concluida_com_candidatos": {
      title: "6 · Concluída com fragmentos candidatos",
      screen: "results",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "done", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4, 5] },
      result: { outcome: "done" },
      nextAction: { text: "Execução concluída. Revise o resultado e os artefatos.", tone: "info", go: "results" },
    },
    "7_nenhuma_evidencia": {
      title: "7 · Nenhuma evidência recuperada",
      screen: "results",
      context: { env: "ok", db: "Enterovirus G", sample: "suino_lab_B", job: "none", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4, 5] },
      result: { outcome: "none" },
      nextAction: { text: "Nenhuma evidência nos critérios adotados. Considere revisar banco/cobertura.", tone: "info", go: "results" },
    },
    "8_nao_avaliavel": {
      title: "8 · Resultado não avaliável",
      screen: "results",
      context: { env: "ok", db: "Sapelovirus A", sample: "swab_fazenda_07", job: "na", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4, 5] },
      result: { outcome: "na" },
      nextAction: { text: "Pré-requisitos mínimos não atendidos. Resultado não avaliável.", tone: "warn", go: "results" },
    },
    "9_falha_operacional": {
      title: "9 · Falha operacional",
      screen: "execution",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "fail", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4] },
      exec: { stages: { qc: "done", host: "done", assembly: "error", blast: "pending", report: "pending" }, elapsed: "00:02:12", error: true },
      nextAction: { text: "Falha operacional na montagem. Verifique os detalhes técnicos.", tone: "warn", go: "execution" },
    },
    "10_lote_sucesso_parcial": {
      title: "10 · Lote com sucesso parcial",
      screen: "history",
      context: { env: "ok", db: "Picornaviridae (RefSeq)", sample: "lote_julho", job: "partial", evidence: false },
      wizard: { current: 5, done: [0, 1, 2, 3, 4, 5] },
      nextAction: { text: "Lote concluído com sucesso parcial. Revise as amostras não avaliáveis.", tone: "warn", go: "history" },
    },
    "11_evidence_v2_shadow": {
      title: "11 · Evidence V2 em shadow mode",
      screen: "evidence",
      context: { env: "ok", db: "Teschovirus A (PTV)", sample: "suino_lab_A", job: "done", evidence: true },
      wizard: { current: 5, done: [0, 1, 2, 3, 4, 5] },
      nextAction: { text: "Evidence V2 é experimental (shadow mode). Não substitui a classificação operacional 1.1.", tone: "warn", go: "evidence" },
    },
  };

  const SCENARIO_ORDER = Object.keys(SCENARIOS);

  const WIZARD_STEPS = [
    { key: "env",     label: "Verificar ambiente" },
    { key: "db",      label: "Banco viral" },
    { key: "sample",  label: "Importar amostra" },
    { key: "config",  label: "Configurar análise" },
    { key: "review",  label: "Revisar" },
    { key: "run",     label: "Executar" },
  ];

  global.GENEIN_MOCK = {
    LABELS, TARGETS, ASSEMBLERS, SAMPLES, CANDIDATE_FRAGMENTS, EXPLORATORY_FRAGMENTS,
    PIPELINE_STAGES, LOG_SAMPLE, HISTORY, SCENARIOS, SCENARIO_ORDER, WIZARD_STEPS,
  };
})(window);
