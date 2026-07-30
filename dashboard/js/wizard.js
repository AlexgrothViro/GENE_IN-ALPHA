export const EXEC_STEPS = Object.freeze([
  {
    label: "Ambiente",
    titles: ["Preparação inicial"],
    description: "Verifica as ferramentas e o ambiente efetivo usados pelos jobs.",
  },
  {
    label: "Banco viral",
    titles: ["Banco viral"],
    description: "Prepara as referências que delimitam a busca por homologia.",
  },
  {
    label: "Amostra",
    titles: ["Amostra"],
    description: "Importa FASTQ R1/R2 e seleciona a amostra da execução.",
  },
  {
    label: "Executar",
    titles: ["Montar contigs", "Análise principal"],
    description: "Revisa perfil, QC, hospedeiro e montagem antes de iniciar.",
  },
  {
    label: "Acompanhar",
    titles: ["Resultados e logs"],
    description: "Distingue progresso, falha operacional e resultado científico.",
  },
]);

export function sectionStep(titleText, steps = EXEC_STEPS) {
  const title = String(titleText || "").toLowerCase();
  return steps.findIndex((step) => step.titles.some(
    (candidate) => title.includes(candidate.toLowerCase()),
  ));
}

export function stepDone(index, context = {}) {
  if (index === 0) return context.environment === "ok";
  if (index === 1) return Boolean(context.database);
  if (index === 2) return Boolean(context.sample);
  if (index === 3) return ["running", "done", "failed", "cancelled"].includes(context.job);
  if (index === 4) return ["done", "failed", "cancelled"].includes(context.job);
  return false;
}

export function stepBlocked(index, context = {}) {
  if (index === 3) return !(context.database && context.sample);
  if (index === 4) return context.job === "idle";
  return false;
}

export function stepState(index, current, context) {
  if (index === current) return "current";
  if (stepDone(index, context)) return "done";
  if (stepBlocked(index, context)) return "blocked";
  return "ready";
}
