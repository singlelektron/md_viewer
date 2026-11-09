"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const flush = () => new Promise((resolve) => setImmediate(resolve));
const preview = (values = {}) => ({
  revision: 1, title: "note.md", html: "<p>First</p>", modified: false,
  theme: "moonlit", connected: true, error: null, ...values,
});

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function harness() {
  const elements = new Map();
  for (const id of ["document", "viewport", "document-title", "status", "theme", "empty-state", "error"]) {
    elements.set(id, {
      dataset: {}, children: [], listeners: {}, textContent: "", innerHTML: "",
      hidden: false, scrollTop: 0, value: "moonlit", mathNodes: [],
      addEventListener(name, callback) { this.listeners[name] = callback; },
      getBoundingClientRect() { return { top: 0, bottom: 100 }; },
      querySelectorAll(selector) { return selector.startsWith(".math") ? this.mathNodes : []; },
    });
  }
  const initial = deferred();
  const themeResponses = [];
  const calls = [];
  let listener;
  const document = {
    documentElement: { dataset: { theme: "moonlit" } },
    getElementById: (id) => elements.get(id),
  };
  const window = {
    __TAURI__: {
      core: { invoke(command, args) {
        calls.push({ command, args });
        if (command === "get_preview") return initial.promise;
        if (command === "set_theme") {
          const response = deferred();
          themeResponses.push(response);
          return response.promise;
        }
        return Promise.resolve();
      } },
      event: { async listen(_event, callback) { listener = callback; } },
    },
    katex: { render(_source, node) { node.rendered = true; } },
  };
  vm.runInNewContext(source, { window, document });
  return {
    document, window, elements, calls, initial, themeResponses,
    emit: (payload) => listener({ payload }),
  };
}

test("an in-flight initial snapshot cannot overwrite a newer editor event", async () => {
  const h = harness();
  await flush();
  h.emit(preview({ revision: 2, html: "<p>Unsaved</p>", modified: true }));
  h.initial.resolve(preview());
  await flush();
  assert.equal(h.elements.get("document").innerHTML, "<p>Unsaved</p>");
  assert.equal(h.elements.get("status").textContent, "Live · unsaved");
  assert.equal(h.calls.at(-1).command, "frontend_ready");
});

test("theme and disconnect events apply even when content revision is unchanged", async () => {
  const h = harness();
  h.initial.resolve(preview());
  await flush();
  h.emit(preview({ theme: "paper", connected: false }));
  assert.equal(h.document.documentElement.dataset.theme, "paper");
  assert.equal(h.elements.get("theme").value, "paper");
  assert.equal(h.elements.get("status").textContent, "Disconnected");
  h.emit(preview({ revision: 0, html: "<p>Stale</p>", theme: "graphite" }));
  assert.equal(h.document.documentElement.dataset.theme, "paper");
  assert.equal(h.elements.get("document").innerHTML, "<p>First</p>");
});

test("a delayed theme response cannot replace a newer document", async () => {
  const h = harness();
  h.initial.resolve(preview());
  await flush();
  const control = h.elements.get("theme");
  control.value = "graphite";
  const changed = control.listeners.change();
  h.emit(preview({ revision: 3, html: "<p>Latest</p>", theme: "graphite" }));
  h.themeResponses[0].resolve(preview({ theme: "graphite" }));
  await changed;
  assert.equal(h.elements.get("document").dataset.revision, "3");
  assert.equal(h.elements.get("document").innerHTML, "<p>Latest</p>");
});

test("one failed formula falls back to text without stopping the next formula", async () => {
  const h = harness();
  const nodes = ["\\bad{", "x^2"].map((tex) => ({
    textContent: "", getAttribute: () => tex,
    classList: { contains: () => false, add() {} },
  }));
  h.elements.get("document").mathNodes = nodes;
  h.window.katex.render = (tex, node, options) => {
    assert.equal(options.trust, false);
    assert.equal(options.throwOnError, false);
    if (tex === "\\bad{") throw new Error("untrusted <source>");
    node.rendered = true;
  };
  h.initial.resolve(preview());
  await flush();
  assert.equal(nodes[0].textContent, "\\bad{");
  assert.equal(nodes[1].rendered, true);
});

test("external document links do not navigate the WebView", async () => {
  const h = harness();
  h.initial.resolve(preview());
  await flush();
  let prevented = false;
  h.elements.get("document").listeners.click({
    target: { closest: () => ({ getAttribute: () => "https://example.com" }) },
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
});
