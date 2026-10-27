const { test } = require("node:test");
const assert = require("node:assert/strict");
const copy = require("../../static/js/copy.js");

function button(attributes) {
  return {
    textContent: "Copy",
    attributes: { ...attributes },
    hasAttribute(name) { return name in this.attributes; },
    getAttribute(name) { return this.attributes[name] ?? null; },
    setAttribute(name, value) { this.attributes[name] = value; },
  };
}

test("textOf copies the address of the page or the value of a field", () => {
  const field = { value: "[![x](i)](p)" };
  const doc = { querySelector: (selector) => (selector === "#code" ? field : null) };
  const location = { href: "https://example.org/s/o~r/?since=2026-01-01" };
  assert.equal(copy.textOf(button({ "data-copy-url": "" }), doc, location), location.href);
  assert.equal(copy.textOf(button({ "data-copy": "#code" }), doc, location), field.value);
  assert.equal(copy.textOf(button({ "data-copy": "#missing" }), doc, location), "");
  const text = { textContent: "plain" };
  assert.equal(copy.textOf(button({ "data-copy": "#t" }), { querySelector: () => text }, location), "plain");
});

test("copy uses the clipboard and fails without one", async () => {
  const written = [];
  await copy.copy("abc", { writeText: async (t) => { written.push(t); } });
  assert.deepEqual(written, ["abc"]);
  await assert.rejects(copy.copy("abc", undefined));
});

test("confirmCopied says Copied and comes back", () => {
  const b = button({});
  let later;
  copy.confirmCopied(b, (f, ms) => { later = f; assert.equal(ms, 2000); });
  assert.equal(b.textContent, "Copied");
  later();
  assert.equal(b.textContent, "Copy");
  copy.confirmCopied(b, () => {});
  copy.confirmCopied(b, (f) => f());
  assert.equal(b.textContent, "Copy", "a second click keeps the first label");
});

test("setup copies on a click and selects the field when the clipboard fails", async () => {
  let listener;
  const field = { value: "code", selected: false, select() { this.selected = true; } };
  const doc = {
    addEventListener: (name, f) => { listener = f; },
    querySelector: () => field,
  };
  const written = [];
  const win = {
    location: { href: "u" },
    navigator: { clipboard: { writeText: async (t) => { written.push(t); } } },
    setTimeout: () => {},
  };
  copy.setup(doc, win);
  const b = button({ "data-copy": "#f" });
  let prevented = false;
  listener({ target: { closest: () => b }, preventDefault: () => { prevented = true; } });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(written, ["code"]);
  assert.equal(prevented, true);
  assert.equal(b.textContent, "Copied");

  win.navigator = {};
  listener({ target: { closest: () => b }, preventDefault: () => {} });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(field.selected, true);
  listener({ target: { closest: () => null }, preventDefault: () => { throw new Error("no"); } });
});
