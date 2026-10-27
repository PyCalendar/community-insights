const { test } = require("node:test");
const assert = require("node:assert/strict");
const fitSelect = require("../../static/js/fit-select.js");

function row(fit) {
  return { hidden: false, getAttribute: () => fit };
}

test("show keeps the rows of one fit, or all", () => {
  const rows = [row("measured"), row("normal"), row("measured"), row("Kaplan-Meier")];
  assert.equal(fitSelect.show(rows, "measured"), 2);
  assert.deepEqual(rows.map((r) => r.hidden), [false, true, false, true]);
  assert.equal(fitSelect.show(rows, ""), 4);
  assert.deepEqual(rows.map((r) => r.hidden), [false, false, false, false]);
  assert.equal(fitSelect.show(rows, "nothing"), 0);
});

test("setup follows the choice and needs its table", () => {
  const rows = [row("measured"), row("normal")];
  const table = { querySelectorAll: () => rows };
  const listeners = [];
  const select = {
    value: "normal",
    getAttribute: () => "#fits-pr",
    addEventListener: (name, f) => listeners.push(f),
  };
  const doc = { querySelector: (selector) => (selector === "#fits-pr" ? table : null) };
  fitSelect.setup(select, doc);
  assert.deepEqual(rows.map((r) => r.hidden), [true, false]);
  select.value = "";
  listeners[0]();
  assert.deepEqual(rows.map((r) => r.hidden), [false, false]);
  assert.equal(fitSelect.setup({ getAttribute: () => "#none" }, doc), null);
});
