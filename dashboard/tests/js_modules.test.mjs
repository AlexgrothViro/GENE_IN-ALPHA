import assert from "node:assert/strict";
import test from "node:test";

import { setDisabled } from "../js/a11y.js";
import { filterHistoryRuns } from "../js/history.js";
import { canonicalExecutionStatus } from "../js/jobs.js";
import { EXEC_STEPS, sectionStep, stepBlocked } from "../js/wizard.js";

test("wizard preserves the five-stage reference flow", () => {
  assert.deepEqual(EXEC_STEPS.map((step) => step.label), [
    "Ambiente", "Banco viral", "Amostra", "Executar", "Acompanhar",
  ]);
  assert.equal(sectionStep("Análise principal"), 3);
  assert.equal(sectionStep("Resultados e logs"), 4);
  assert.equal(stepBlocked(3, { database: "", sample: "" }), true);
});

test("job status prefers the canonical execution field", () => {
  assert.equal(canonicalExecutionStatus({ status: "done", execution_status: "blocked" }), "blocked");
});

test("history filtering is case insensitive", () => {
  const runs = [{ sample: "Suino_A", execution_status: "done" }, { sample: "Controle", execution_status: "failed" }];
  assert.deepEqual(filterHistoryRuns(runs, "suino"), [runs[0]]);
});

test("disabled controls expose the blocking reason", () => {
  const attributes = new Map();
  const node = {
    disabled: false,
    title: "",
    setAttribute(name, value) { attributes.set(name, value); },
  };
  setDisabled(node, true, "Prepare o banco");
  assert.equal(node.disabled, true);
  assert.equal(node.title, "Prepare o banco");
  assert.equal(attributes.get("aria-disabled"), "true");
});
