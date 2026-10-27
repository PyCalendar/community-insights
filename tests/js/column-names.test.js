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

test("setup switches the table and keeps the choice", () => {
  const attributes = {};
  const table = { setAttribute: (k, v) => { attributes[k] = v; } };
  let listener;
  const input = {
    checked: false,
    getAttribute: () => "#t",
    addEventListener: (name, f) => { listener = f; },
  };
  const storage = memory();
  names.keep(storage, "words");
  names.setup(input, { querySelector: () => table }, storage);
  assert.equal(input.checked, true);
  assert.equal(attributes["data-names"], "words");
  input.checked = false;
  listener();
  assert.equal(attributes["data-names"], "variables");
  assert.equal(names.kept(storage), "variables");
  assert.equal(names.setup(input, { querySelector: () => null }, storage), null);
});
