import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { announce, setBusy, setDisabled, setExpanded } from "../js/a11y.js";
import { createElement, replaceContent, setText } from "../js/dom.js";
import { evidenceResultDisposition } from "../js/evidence.js";
import { filterHistoryRuns } from "../js/history.js";
import {
  ACTIVE_JOB_STATES,
  TERMINAL_JOB_STATES,
  canonicalExecutionStatus,
  describeJob,
  extractJobId,
} from "../js/jobs.js";
import { escapeHTML, parseTSV, renderTSVTable } from "../js/results.js";
import { createStore } from "../js/state.js";
import { EXEC_STEPS, sectionStep, stepBlocked } from "../js/wizard.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));

function fakeDocument() {
  return {
    createElement(tagName) {
      return {
        tagName: tagName.toUpperCase(),
        attributes: new Map(),
        children: [],
        dataset: {},
        className: "",
        textContent: "",
        setAttribute(name, value) { this.attributes.set(name, String(value)); },
        addEventListener() {},
        append(...children) { this.children.push(...children); },
      };
    },
    createTextNode(text) {
      return { nodeType: 3, textContent: String(text) };
    },
  };
}

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

test("HTML escaping keeps hostile log values literal", () => {
  const hostile = '<img src=x onerror="alert(1)">';
  const escaped = escapeHTML(hostile);
  assert.equal(escaped, "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
  assert.equal(escaped.includes("<img"), false);
});

test("dashboard modules never assign innerHTML", () => {
  const moduleDir = path.join(TEST_DIR, "..", "js");
  for (const name of fs.readdirSync(moduleDir).filter((item) => item.endsWith(".js"))) {
    const source = fs.readFileSync(path.join(moduleDir, name), "utf8");
    assert.equal(
      /\.innerHTML\s*=/.test(source),
      false,
      `${name} must keep DOM writes outside innerHTML`,
    );
  }
});

test("DOM helpers keep hostile text inert and replace prior content", () => {
  const doc = fakeDocument();
  const payload = "<script>alert(1)</script>";
  const node = createElement(doc, "div", { title: payload }, [payload]);
  assert.equal(node.attributes.get("title"), payload);
  assert.equal(node.children[0].nodeType, 3);
  assert.equal(node.children[0].textContent, payload);

  const container = {
    children: ["old"],
    replaceChildren() { this.children = []; },
    append(...children) { this.children.push(...children); },
  };
  replaceContent(container, node);
  assert.deepEqual(container.children, [node]);
  setText(node, payload);
  assert.equal(node.textContent, payload);
});

test("accessibility helpers expose busy, expanded and live-region state", () => {
  const attributes = new Map();
  const node = {
    textContent: "",
    setAttribute(name, value) { attributes.set(name, value); },
    getAttribute(name) { return attributes.get(name) || null; },
  };
  setBusy(node, true);
  setExpanded(node, false);
  announce(node, "<strong>mensagem literal</strong>");
  assert.equal(attributes.get("aria-busy"), "true");
  assert.equal(attributes.get("aria-expanded"), "false");
  assert.equal(attributes.get("role"), "status");
  assert.equal(node.textContent, "<strong>mensagem literal</strong>");
});

test("state store merges patches, supports replacement and notifies", () => {
  const store = createStore({ job: { status: "queued", output: [] } });
  const observed = [];
  const unsubscribe = store.subscribe((state) => observed.push(state));
  store.set({ job: { status: "running" } });
  assert.deepEqual(store.get(), { job: { status: "running", output: [] } });
  store.replace({ job: { status: "done" } });
  assert.deepEqual(store.get(), { job: { status: "done" } });
  assert.equal(observed.length, 2);
  unsubscribe();
});

test("job helpers classify every active and terminal state", () => {
  ACTIVE_JOB_STATES.forEach((status) => {
    const description = describeJob({ execution_status: status });
    assert.equal(description.active, true);
    assert.equal(description.terminal, false);
  });
  TERMINAL_JOB_STATES.forEach((status) => {
    const description = describeJob({ execution_status: status });
    assert.equal(description.active, false);
    assert.equal(description.terminal, true);
  });
  assert.equal(extractJobId({ job_id: "  run-1  " }), "run-1");
  assert.equal(extractJobId({}), null);
});

test("TSV rendering escapes cells and preserves evidence row classes", () => {
  const parsed = parseTSV(
    "sample\tevidence_class\n<img src=x>\tSTRONG\n",
  );
  const html = renderTSVTable(parsed);
  assert.match(html, /tsv-row-strong/);
  assert.match(html, /&lt;img src=x&gt;/);
  assert.equal(html.includes("<img src=x>"), false);
});

test("Evidence result disposition distinguishes incompatible and incomplete", () => {
  assert.equal(evidenceResultDisposition({ valid_alpha2: false }), "incompatible");
  assert.equal(evidenceResultDisposition({ complete: false }), "incomplete");
  assert.equal(
    evidenceResultDisposition({ complete: true, evidence_v2: {} }),
    "complete",
  );
});
