export function collectNonEmptyConfig(entries) {
  const config = {};
  for (const [key, rawValue] of entries) {
    const value = String(rawValue ?? "").trim();
    if (value) config[key] = value;
  }
  return config;
}

export function buildConfigUpdate(entries, governance = {}) {
  return {
    config: collectNonEmptyConfig(entries),
    governance: {
      unlock: governance.unlock === true,
      justification: String(governance.justification || "").trim(),
      operator_declared: String(governance.operatorDeclared || "").trim(),
    },
  };
}
