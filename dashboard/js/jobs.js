export const ACTIVE_JOB_STATES = Object.freeze(["queued", "starting", "running", "cancelling"]);
export const TERMINAL_JOB_STATES = Object.freeze(["done", "done_with_warning", "blocked", "failed", "cancelled"]);

export function canonicalExecutionStatus(job = {}) {
  if (job.execution_status) return job.execution_status;
  if (job.status === "error") return "failed";
  if (job.status === "success") return "done";
  return job.status || "queued";
}

export function isActiveJobStatus(status) {
  return ACTIVE_JOB_STATES.includes(status);
}

export function isTerminalJobStatus(status) {
  return TERMINAL_JOB_STATES.includes(status);
}

export function describeJob(job = {}) {
  const status = canonicalExecutionStatus(job);
  return Object.freeze({
    status,
    active: isActiveJobStatus(status),
    terminal: isTerminalJobStatus(status),
    warning: status === "done_with_warning",
    blocked: status === "blocked",
    cancelled: status === "cancelled",
    failed: status === "failed",
  });
}

export function extractJobId(payload) {
  if (payload && typeof payload.job_id === "string" && payload.job_id.trim()) {
    return payload.job_id.trim();
  }
  return null;
}
