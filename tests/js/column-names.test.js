const { test } = require("node:test");
const assert = require("node:assert/strict");
const names = require("../../static/js/column-names.js");

function memory() {
  const data = {};
  return { getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = v; } };
}

test("namesFor and the kept choice", () => {
  assert.equal(names.namesFor(true), "words");
  assert.equal(names.namesFor(false), "variables");
  const storage = memory();
  assert.equal(names.kept(storage), "variables");
  names.keep(storage, "words");
  assert.equal(names.kept(storage), "words");
  assert.equal(names.kept(null), "variables");
  const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
  assert.equal(names.kept(broken), "variables");
  names.keep(broken, "words");
});

function page() {
  const { JSDOM } = require("jsdom");
  return new JSDOM(`
    <div id="query-result">
      <input type="checkbox" data-column-names="#t">
      <table id="t" data-names="variables"></table>
    </div>`).window.document;
}

test("setup switches the table and keeps the choice", () => {
  const doc = page();
  const input = doc.querySelector("input");
  const table = doc.querySelector("table");
  const storage = memory();
  names.keep(storage, "words");
  names.setup(input, doc, storage);
  assert.equal(input.checked, true);
  assert.equal(table.getAttribute("data-names"), "words");
  input.click();
  assert.equal(table.getAttribute("data-names"), "variables");
  assert.equal(names.kept(storage), "variables");
});

test("setup needs the table and sets a switch up once", () => {
  const doc = page();
  const input = doc.querySelector("input");
  assert.equal(names.setup(input, doc, memory()), doc.querySelector("table"));
  assert.equal(names.setup(input, doc, memory()), null, "already set up");
  const lonely = doc.createElement("input");
  lonely.setAttribute("data-column-names", "#missing");
  assert.equal(names.setup(lonely, doc, memory()), null);
});

test("setupAll sets up the switch of a result htmx put in", () => {
  const doc = page();
  const storage = memory();
  names.keep(storage, "words");
  names.setupAll(doc, storage);
  doc.getElementById("query-result").outerHTML =
    '<div id="query-result"><input type="checkbox" data-column-names="#t"><table id="t"></table></div>';
  names.setupAll(doc, storage);
  assert.equal(doc.querySelector("table").getAttribute("data-names"), "words");
  doc.querySelector("input").click();
  assert.equal(doc.querySelector("table").getAttribute("data-names"), "variables");
});
