export function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));
}

export function parseTSV(text) {
  const lines = String(text || "").split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return { headers: [], rows: [] };
  return {
    headers: lines[0].split("\t"),
    rows: lines.slice(1).map((line) => line.split("\t")),
  };
}

export function renderTSVTable({ headers = [], rows = [] } = {}) {
  if (!headers.length) return '<p class="tsv-empty">Arquivo vazio ou sem dados.</p>';
  const classIndex = headers.findIndex((header) => header === "evidence_class");
  const headingCells = headers
    .map((header) => `<th>${escapeHTML(header)}</th>`)
    .join("");
  const bodyRows = rows.map((cells) => {
    const evidenceClass = classIndex >= 0 ? (cells[classIndex] || "").trim() : "";
    const rowClass = EVIDENCE_CLASS_ROW[evidenceClass] || "";
    const values = headers.map((_, index) => (
      `<td>${escapeHTML(cells[index] === undefined ? "" : cells[index])}</td>`
    )).join("");
    return `<tr class="${rowClass}">${values}</tr>`;
  }).join("");
  return `<table class="tsv-table"><thead><tr>${headingCells}</tr></thead><tbody>${bodyRows}</tbody></table>`;
}
const EVIDENCE_CLASS_ROW = Object.freeze({
  STRONG: "tsv-row-strong",
  STRONG_DIVERGENT: "tsv-row-strong-divergent",
  MODERATE: "tsv-row-moderate",
  WEAK_RECOVERABLE: "tsv-row-weak-recoverable",
  REVIEW: "tsv-row-review",
});
