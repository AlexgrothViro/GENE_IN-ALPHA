export function historySearchText(run = {}) {
  const label = Number(run.exit_code) === 0 ? "sucesso" : "falha";
  return [
    run.sample, run.db, run.status, run.execution_status,
    run.compatibility_status, label, run.run_id, run.run_dir,
  ].map((value) => String(value == null ? "" : value).toLowerCase()).join(" ");
}

export function filterHistoryRuns(runs, query) {
  const normalized = String(query || "").toLowerCase().trim();
  if (!normalized) return Array.isArray(runs) ? runs : [];
  return (Array.isArray(runs) ? runs : []).filter((run) => historySearchText(run).includes(normalized));
}
