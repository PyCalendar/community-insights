const { test } = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const fitSelect = require("../../static/js/fit-select.js");

function page(chosen) {
  return new JSDOM(`
    <select data-fit-select="#fits-pr">
      <option value="">all</option>
      <option value="measured">measured</option>
      <option value="normal" ${chosen === "normal" ? "selected" : ""}>normal</option>
    </select>
    <table id="fits-pr">
      <tr data-fit="measured"></tr><tr data-fit="normal"></tr>
      <tr data-fit="measured"></tr><tr data-fit="Kaplan-Meier"></tr>
    </table>`).window.document;
}

function hidden(doc) {
  return Array.from(doc.querySelectorAll("tr[data-fit]"), (row) => row.hidden);
}

test("show keeps the rows of one fit, or all", () => {
  const doc = page();
  const rows = doc.querySelectorAll("tr[data-fit]");
  assert.equal(fitSelect.show(rows, "measured"), 2);
  assert.deepEqual(hidden(doc), [false, true, false, true]);
  assert.equal(fitSelect.show(rows, ""), 4);
  assert.deepEqual(hidden(doc), [false, false, false, false]);
  assert.equal(fitSelect.show(rows, "nothing"), 0);
});

test("setup shows the chosen fit and follows a change", () => {
  const doc = page("normal");
  const select = doc.querySelector("select");
  fitSelect.setup(select, doc);
  assert.deepEqual(hidden(doc), [true, false, true, true]);
  select.value = "";
  select.dispatchEvent(new doc.defaultView.Event("change"));
  assert.deepEqual(hidden(doc), [false, false, false, false]);
});

test("setup needs its table", () => {
  const doc = page();
  const select = doc.querySelector("select");
  select.setAttribute("data-fit-select", "#none");
  assert.equal(fitSelect.setup(select, doc), null);
});
