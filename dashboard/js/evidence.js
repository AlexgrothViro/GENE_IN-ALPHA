export const EVIDENCE_TERMINAL_STATES = Object.freeze([
  "done", "done_with_warning", "blocked", "failed", "cancelled",
]);

export function isEvidenceTerminal(status) {
  return EVIDENCE_TERMINAL_STATES.includes(status);
}

export function evidenceResultDisposition(result = {}) {
  if (result.valid_alpha2 === false) return "incompatible";
  if (!result.complete || !result.evidence_v2) return "incomplete";
  return "complete";
}
