export function setBusy(node, busy) {
  node.setAttribute("aria-busy", busy ? "true" : "false");
  return node;
}

export function setExpanded(node, expanded) {
  node.setAttribute("aria-expanded", expanded ? "true" : "false");
  return node;
}

export function setHidden(node, hidden) {
  const value = Boolean(hidden);
  node.hidden = value;
  node.setAttribute("aria-hidden", value ? "true" : "false");
  return node;
}

export function setDisabled(node, disabled, reason = "") {
  const value = Boolean(disabled);
  node.disabled = value;
  node.setAttribute("aria-disabled", value ? "true" : "false");
  node.title = value ? reason : "";
  return node;
}

export function announce(region, message) {
  if (!region.getAttribute("role")) region.setAttribute("role", "status");
  if (!region.getAttribute("aria-live")) region.setAttribute("aria-live", "polite");
  region.textContent = message == null ? "" : String(message);
  return region;
}
